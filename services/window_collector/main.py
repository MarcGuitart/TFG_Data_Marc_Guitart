# services/window_collector/main.py
import os, json, threading, socket, time
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from fastapi import FastAPI
import uvicorn
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone

# === ENV VARS ===
BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")
TPROC = os.getenv("TOPIC_PROCESSED", "telemetry.processed")
OUTPATH = os.getenv("OUTPUT_PATH", "/app/data/processed_window.parquet")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")
# Deduplicación configurable (en compose tienes DEDUP_KEY=timestamp,id)
DEDUP_KEY = os.getenv("DEDUP_KEY", "timestamp,id")
_key_fields = tuple(k.strip() for k in DEDUP_KEY.split(",") if k.strip())

os.makedirs(os.path.dirname(OUTPATH), exist_ok=True)

# ==== Influx client global y SINCRONO ====
_influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
_write_api = _influx_client.write_api(write_options=SYNCHRONOUS)

app = FastAPI()
_lock = threading.Lock()
_last_by_key = {}

def wait_for_kafka(broker="kafka:9092", timeout=120):
    host, port = broker.split(":")
    port = int(port)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                print(f"[collector] ✅ Kafka OK en {broker}")
                return
        except Exception as e:
            print(f"[collector] esperando Kafka {broker} ... {e}")
            time.sleep(2)
    raise RuntimeError(f"[collector] ❌ Kafka no disponible en {broker}")

def _parse_ts(ts_any):
    """Devuelve datetime UTC (seg.) desde string ISO/‘YYYY-mm-dd HH:MM:SS’ o datetime."""
    if ts_any is None:
        return None
    if isinstance(ts_any, datetime):
        return ts_any.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    s = str(ts_any).replace("T", " ").replace("Z", "")
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def _shift_ts_to_today(ts_str):
    """Mantiene H/M/S del mensaje y mueve la FECHA a hoy (UTC)."""
    if not ts_str:
        return datetime.utcnow().replace(tzinfo=timezone.utc)
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        t = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").time()
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)
    today = datetime.utcnow().date()
    return datetime.combine(today, t).replace(tzinfo=timezone.utc)

def _key_tuple(rec: dict):
    # Construye la clave de dedupe con los campos configurados; si faltan, usa None
    return tuple(rec.get(f) for f in _key_fields) if _key_fields else (rec.get("timestamp"), rec.get("id"))

def write_to_influx(rec):
    """
    Guarda:
      - telemetry.var       @ timestamp (observado)
      - telemetry.prediction@ ts_pred (predicción a horizonte)
      - weights.w (por modelo) @ ts_pred (estado del hypermodel en ese tick)
    """
    try:
        unit = rec.get("id") or rec.get("unit_id") or "unknown"

        # 1) Dato observado (var) con timestamp del CSV movido a HOY
        if "var" in rec and rec["var"] is not None:
            p = (
                Point("telemetry")
                .tag("id", unit)
                .field("var", float(rec["var"]))
                .time(_shift_ts_to_today(rec.get("timestamp")), WritePrecision.S)
            )
            _write_api.write(bucket=INFLUX_BUCKET, record=p)

        # 2) Predicción global del HyperModel (campo yhat), time = ts_pred si viene, si no timestamp
        if "yhat" in rec and rec["yhat"] is not None:
            t_pred = _shift_ts_to_today(rec.get("ts_pred") or rec.get("timestamp"))
            p = (
                Point("telemetry")
                .tag("id", unit)
                .field("prediction", float(rec["yhat"]))
                .time(t_pred, WritePrecision.S)
            )
            _write_api.write(bucket=INFLUX_BUCKET, record=p)

        # 3) Pesos del HyperModel (si el agent los envía)
        # Esperamos: rec["hyper_weights"] = {"linear_8": 0.42, "poly2_12": 0.31, "ab_fast": 0.27, ...}
        if isinstance(rec.get("hyper_weights"), dict):
            t_pred = _shift_ts_to_today(rec.get("ts_pred") or rec.get("timestamp"))
            for model_name, w in rec["hyper_weights"].items():
                if w is None:
                    continue
                pw = (
                    Point("weights")
                    .tag("id", unit)
                    .tag("model", str(model_name))
                    .field("w", float(w))
                    .time(t_pred, WritePrecision.S)
                )
                _write_api.write(bucket=INFLUX_BUCKET, record=pw)

    except Exception as e:
        print(f"[collector] ❌ Error escribiendo en Influx: {e}")

def run_consumer():
    wait_for_kafka(BROKER)

    while True:
        try:
            consumer = KafkaConsumer(
                TOUT,
                bootstrap_servers=BROKER,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                group_id="collector-v5"
            )
            print(f"[collector] ✅ Suscrito a {TOUT}, esperando mensajes...")

            producer = KafkaProducer(
                bootstrap_servers=BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )

            for msg in consumer:
                try:
                    # En tu agent ya usas value_serializer json; aquí por robustez re-decodiﬁcamos
                    rec = json.loads(msg.value.decode("utf-8")) if isinstance(msg.value, (bytes, bytearray)) else msg.value
                except Exception as e:
                    print("[collector] ❌ Error decoding message:", e)
                    continue

                # Publicar copia procesada
                try:
                    producer.send(TPROC, rec)
                except Exception:
                    pass

                # Deduplicación (opcional)
                k = _key_tuple(rec)
                with _lock:
                    _last_by_key[k] = rec

                # Escribir en Influx
                write_to_influx(rec)

                print(f"[collector] ⚙️ recibido key={k}")

        except Exception as e:
            print(f"[collector] ⚠️ Error en consumer loop: {e}")
            time.sleep(5)

@app.on_event("startup")
def start_bg():
    threading.Thread(target=run_consumer, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset")
def reset():
    global _last_by_key
    with _lock:
        _last_by_key = {}
    try:
        os.remove(OUTPATH)
    except FileNotFoundError:
        pass
    return {"status": "reset"}

@app.get("/flush")
def flush():
    with _lock:
        snapshot = list(_last_by_key.values())

    df = pd.DataFrame(snapshot)
    if df.empty:
        print("[collector] ⚠️ No hay datos para flush()")
        return {"rows": 0, "path": OUTPATH}

    ext = ".parquet"
    if "__src_format" in df.columns and (df["__src_format"] == "csv").any():
        ext = ".csv"

    out_path = OUTPATH.replace(".parquet", ext)
    if ext == ".csv":
        df.to_csv(out_path, index=False)
    else:
        df.to_parquet(out_path, index=False)

    print(f"[collector] 💾 Guardado {len(df)} filas en {out_path}")
    return {"rows": len(df), "path": out_path}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
