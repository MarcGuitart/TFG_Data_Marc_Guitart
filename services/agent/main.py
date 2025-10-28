import os, json, time, socket, datetime
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.delete_api import DeleteApi
from datetime import datetime, timedelta, timezone
import threading
from fastapi import FastAPI
import uvicorn
import logging
logging.basicConfig(level=logging.INFO)

try:
    from agent.model import NaiveDailyProfileModel
except ModuleNotFoundError:
    from model import NaiveDailyProfileModel

# === CONFIG ===
FLAVOR = os.getenv("FLAVOR", "inference")
BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TIN = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")
MAX_ROWS_PER_UNIT = int(os.getenv("MAX_ROWS_PER_UNIT", "1000"))

LEARN_LOOKBACK_DAYS = int(os.getenv("LEARN_LOOKBACK_DAYS", "30"))
LEARN_PERIOD_SEC    = int(os.getenv("LEARN_PERIOD_SEC", "86400"))

def auto_purge():
    while True:
        try:
            enforce_cap_per_unit()
        except Exception as e:
            print("[agent] error en auto-purge:", e)
        time.sleep(300)

# --- esperar a Kafka ---
def wait_for_kafka(broker: str, timeout=300):
    host, port = broker.split(":")
    port = int(port)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                print(f"[agent] Kafka OK en {broker}")
                return
        except Exception as e:
            print(f"[agent] esperando Kafka {broker} ... {e}")
            time.sleep(2)
    raise RuntimeError(f"Kafka no disponible en {broker}")

def shift_ts_to_today(ts_str: str | None) -> datetime:
    """
    Parsea 'YYYY-mm-dd HH:MM:SS' o ISO.
    Mantiene la hora/min/seg del CSV pero pone la FECHA de HOY (UTC).
    """
    now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
    if not ts_str:
        return now_utc
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        t = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").time()
    except Exception:
        return now_utc
    return datetime.combine(now_utc.date(), t).replace(tzinfo=timezone.utc)

# --- cliente Influx (sincrono para depurar) ---
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
delete_api = client.delete_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

MODEL_PATH = os.getenv("MODEL_PATH", "/app/data/model_naive_daily.json")
SLOT_MINUTES = int(os.getenv("SLOT_MINUTES", "30"))
PRED_HORIZON_MIN = int(os.getenv("PRED_HORIZON_MIN", str(SLOT_MINUTES)))  # por defecto = 30
model = NaiveDailyProfileModel(slot_minutes=SLOT_MINUTES, horizon_slots=max(1, PRED_HORIZON_MIN // SLOT_MINUTES))

# Si existe un modelo guardado, cárgalo
try:
    if os.path.exists(MODEL_PATH):
        model.load(MODEL_PATH)
except Exception as e:
    print("[agent] no se pudo cargar modelo:", e)

def parse_ts_keep_date(ts_str):
    """Parsea 'YYYY-mm-dd HH:MM:SS' o ISO y conserva fecha y hora; salida UTC."""
    if not ts_str:
        return datetime.utcnow().replace(tzinfo=timezone.utc)
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        # último recurso: ahora
        dt = datetime.utcnow()
    return dt.replace(tzinfo=timezone.utc)

def enforce_cap_per_unit():
    q = client.query_api()
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "id")
    '''
    units = [r.get_value() for t in q.query(org=INFLUX_ORG, query=flux) for r in t.records]
    for u in units:
        flux2 = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "telemetry" and r["id"] == "{u}")
          |> count()
        '''
        tables = q.query(org=INFLUX_ORG, query=flux2)
        count = sum(r.get_value() for t in tables for r in t.records)
        if count > MAX_ROWS_PER_UNIT:
            start = "1970-01-01T00:00:00Z"
            stop = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            delete_api.delete(start, stop, f'_measurement="telemetry" AND id="{u}"',
                              bucket=INFLUX_BUCKET, org=INFLUX_ORG)
            print(f"[agent] purgados datos antiguos de id={u}")

def write_timeseries(rec):
    unit = rec.get("unit_id") or rec.get("id") or "unknown"
    p = Point("telemetry").tag("id", unit)

    fields_added = False
    for f in ["v1", "v2", "v3", "v4", "v5", "var"]:
        if f in rec and rec[f] is not None:
            try:
                p = p.field(f, float(rec[f]))
                fields_added = True
            except Exception as e:
                print("[agent] field cast error:", e, "rec=", rec)

    if not fields_added:
        p = p.field("dummy", 1.0)

    ts = shift_ts_to_today(rec.get("timestamp"))
    p = p.time(ts, WritePrecision.S)

    if "var" in rec and rec["var"] is not None:
        try:
            model.update_buffer(float(rec["var"]))
        except Exception:
            pass

    write_api.write(bucket=INFLUX_BUCKET, record=p)

def write_prediction(unit: str, when: datetime, yhat: float):
    p = Point("telemetry").tag("id", unit).field("prediction", float(yhat)).time(when, WritePrecision.S)
    write_api.write(bucket=INFLUX_BUCKET, record=p)

# === Entrenamiento opcional (robusto y compatible con tag "id") ===
def query_training_rows(unit: str, lookback_days: int = LEARN_LOOKBACK_DAYS):
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{lookback_days}d)
      |> filter(fn: (r) => r["_measurement"] == "telemetry" and r["id"] == "{unit}" and r["_field"] == "var")
      |> keep(columns: ["_time","_value"])
      |> sort(columns: ["_time"])
    '''
    tables = client.query_api().query(org=INFLUX_ORG, query=flux)
    rows = []
    for t in tables:
        for r in t.records:
            rows.append({"_time": r.get_time(), "var": float(r.get_value())})
    return rows

def learner_loop():
    """Bucle de entrenamiento no-bloqueante; si no hay datos, no hace nada."""
    while True:
        try:
            # Descubre unidades por el tag correcto "id"
            flux_units = f'''
            import "influxdata/influxdb/schema"
            schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "id")
            '''
            tabs = client.query_api().query(org=INFLUX_ORG, query=flux_units)
            units = list({ r.get_value() for t in tabs for r in t.records if r.get_value() })

            for u in units:
                rows = query_training_rows(u, lookback_days=LEARN_LOOKBACK_DAYS)
                if rows:
                    try:
                        model.update(rows)
                        print(f"[agent] learner: updated model with {len(rows)} rows for id={u}")
                        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
                        model.save(MODEL_PATH)
                    except Exception as e:
                        print("[agent] learner: error updating/saving model:", e)
        except Exception as e:
            print("[agent] learner error:", e)
            time.sleep(LEARN_PERIOD_SEC)
    
def main():
    wait_for_kafka(BROKER, timeout=300)
    consumer = KafkaConsumer(
        TIN,
        bootstrap_servers=BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="agent-v1"
    )
    producer = KafkaProducer(
        bootstrap_servers=BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    threading.Thread(target=auto_purge, daemon=True).start()
    threading.Thread(target=learner_loop, daemon=True).start()

    print(f"[agent] escuchando {TIN} y publicando en {TOUT}")
    for msg in consumer:
        try:
            rec = msg.value
            print(f"[agent] recibido: {rec}")
        except Exception as e:
            print("[agent] error deserializando:", e, msg.value)
            continue

        try:
            write_timeseries(rec)
        except Exception as e:
            print("[agent] influx write error:", e)

        # Predicción T + PRED_HORIZON_MIN
        try:
            base_ts = shift_ts_to_today(rec.get("timestamp"))
            ts_pred = base_ts + timedelta(minutes=PRED_HORIZON_MIN)

            if "var" in rec and rec["var"] is not None:
                yhat = float(rec["var"])
            else:
                yhat = float(model.buffer[-1]) if getattr(model, "buffer", None) else 0.0

            unit = rec.get("unit_id") or rec.get("id") or "unknown"
            print(f"[agent] prediction: unit={unit} ts_pred={ts_pred} yhat={yhat}")
            write_prediction(unit, ts_pred, yhat)

            enriched = dict(rec)
            enriched["yhat"] = yhat
            enriched["ts_pred"] = ts_pred.strftime("%Y-%m-%d %H:%M:%S")
            enriched["mode"] = FLAVOR
            if "timestamp" in enriched and "ts" not in enriched:
                enriched["ts"] = enriched["timestamp"]
            producer.send(TOUT, enriched)

        except Exception as e:
            print("[agent] prediction error:", e)
            if "timestamp" in rec and "ts" not in rec:
                rec["ts"] = rec["timestamp"]
            producer.send(TOUT, rec)

        if FLAVOR != "training" and "v1" in rec:
            try:
                rec["v1"] = round(float(rec["v1"]) * 1.1, 6)
            except:
                pass

if __name__ == "__main__":
    print(f"[agent] conectado a Influx {INFLUX_URL}, bucket={INFLUX_BUCKET}, org={INFLUX_ORG}", flush=True)
    print(f"[agent] escuchando {TIN} y publicando en {TOUT}", flush=True)
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning"), daemon=True).start()
    main()
    