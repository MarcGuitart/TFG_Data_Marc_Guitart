import os, json, threading, socket, time
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from fastapi import FastAPI
import uvicorn
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone, timedelta

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
_key_fields = [s.strip() for s in DEDUP_KEY.split(",") if s.strip()]


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
                print(f"[collector] ✅ Kafka OK en {broker}", flush=True)
                return
        except Exception as e:
            print(f"[collector] esperando Kafka {broker} ... {e}", flush=True)
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
    """
    Mantiene la fecha y hora del CSV pero las traslada al pasado reciente.
    Calcula cuántos días atrás estaba el timestamp original y lo traslada
    manteniendo esa distancia relativa, pero dentro de la ventana de retention.
    """
    if not ts_str:
        return datetime.utcnow().replace(tzinfo=timezone.utc)
    
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        original_dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)
    
    # Referencia: usamos una fecha base del CSV (primera fecha que aparezca)
    # Para simplicidad, asumimos que queremos trasladar todo a los últimos 6 días
    # Calculamos la diferencia desde una fecha base arbitraria (ej: 2025-03-10)
    reference_date = datetime(2025, 3, 10)  # Primera fecha del CSV típico
    
    # Calculamos cuántos segundos han pasado desde la referencia
    delta_seconds = (original_dt - reference_date).total_seconds()
    
    # Creamos un timestamp 7 días atrás desde ahora y sumamos el delta
    # Esto asegura que incluso el último punto del CSV esté en el pasado
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    base_past = now - timedelta(days=7)  # 7 días atrás (dentro de retention)
    
    # Sumamos el delta desde la referencia
    result_dt = base_past + timedelta(seconds=delta_seconds)
    
    return result_dt

def _key_tuple(rec: dict):
    # Construye la clave de dedupe con los campos configurados; si faltan, usa None
    return tuple(rec.get(f) for f in _key_fields) if _key_fields else (rec.get("timestamp"), rec.get("id"))

def write_to_influx(rec):
    # SIEMPRE define unit lo primero
    unit = rec.get("id") or rec.get("unit_id") or "unknown"

    # --- Predicciones por modelo (para evaluación individual)
    per_model = rec.get("hyper_models")
    if isinstance(per_model, dict):
        try:
            ts_pm = _parse_ts(rec.get("ts_pred")) or _shift_ts_to_today(rec.get("timestamp"))
            for model_name, yhat_m in per_model.items():
                _write_api.write(
                    bucket=INFLUX_BUCKET,
                    record=(
                        Point("telemetry_models")
                        .tag("id", unit)
                        .tag("model", str(model_name))
                        .field("yhat", float(yhat_m))
                        .time(ts_pm, WritePrecision.S)
                    ),
                )
        except Exception as e:
            print(f"[collector] ❌ Error guardando telemetry_models: {e}")

    # Observado… (DESACTIVADO - el agent ya lo escribe)
    # if "var" in rec:
    #     try:
    #         ts_var = _shift_ts_to_today(rec.get("timestamp"))
    #         p = (
    #             Point("telemetry")
    #             .tag("id", unit) 
    #             .field("var", float(rec["var"]))
    #             .time(ts_var, WritePrecision.S)
    #         )
    #         _write_api.write(bucket=INFLUX_BUCKET, record=p)
    #     except Exception as e:
    #         print(f"[collector] ❌ Error guardando observed: {e}")

    # ✅ Predicción en ts_pred (DESACTIVADO - el agent ya lo escribe)
    # if "yhat" in rec:
    #     ts_pred_str = rec.get("ts_pred")  # "YYYY-mm-dd HH:MM:SS"
    #     if ts_pred_str:
    #         when = _shift_ts_to_today(ts_pred_str)
    #         try:
    #             p = (
    #                 Point("telemetry")
    #                 .tag("id", unit)
    #                 .field("prediction", float(rec["yhat"]))
    #                 .time(when, WritePrecision.S)
    #             )
    #             _write_api.write(bucket=INFLUX_BUCKET, record=p)
    #         except Exception as e:
    #             print(f"[collector] ❌ Error guardando prediction: {e}")
        # si no hay ts_pred, no escribas prediction desde el collector

    # Pesos (opcional)
    weights = rec.get("hyper_weights")
    if isinstance(weights, dict):
        try:
            # USAR el timestamp exacto que el agent usó para escribir a InfluxDB
            tsw = _parse_ts(rec.get("ts_influx"))
            if not tsw:
                # Fallback a ts_pred o timestamp shifteado
                tsw = _parse_ts(rec.get("ts_pred")) or _shift_ts_to_today(rec.get("timestamp"))
            for model_name, w in weights.items():
                _write_api.write(
                    bucket=INFLUX_BUCKET,
                    record=(
                        Point("weights")
                        .tag("id", unit)
                        .tag("model", str(model_name))
                        .field("w", float(w))
                        .time(tsw, WritePrecision.S)
                    ),
                )
        except Exception as e:
            print(f"[collector] ❌ Error guardando weights: {e}")

    # Modelo elegido (AP2 - modo adaptativo)
    chosen_model = rec.get("hyper_chosen")
    if chosen_model:
        try:
            # USAR el timestamp exacto que el agent usó para escribir a InfluxDB
            tsc = _parse_ts(rec.get("ts_influx"))
            if not tsc:
                # Fallback: intentar parsear timestamp original y shiftearlo
                tsc = _parse_ts(rec.get("timestamp")) or _shift_ts_to_today(rec.get("timestamp"))
            _write_api.write(
                bucket=INFLUX_BUCKET,
                record=(
                    Point("chosen_model")
                    .tag("id", unit)
                    .field("model", str(chosen_model))
                    .time(tsc, WritePrecision.S)
                ),
            )
            print(f"[collector] ✅ Escrito chosen_model: {unit} @ {tsc.isoformat()} = {chosen_model}", flush=True)
        except Exception as e:
            print(f"[collector] ❌ Error guardando chosen_model: {e}", flush=True)

    # AP2: Error del modelo elegido (absoluto y relativo)
    chosen_error_abs = rec.get("chosen_error_abs")
    chosen_error_rel = rec.get("chosen_error_rel")
    if chosen_error_abs is not None or chosen_error_rel is not None:
        try:
            # USAR el timestamp exacto que el agent usó para escribir a InfluxDB
            tse = _parse_ts(rec.get("ts_influx"))
            if not tse:
                # Fallback: intentar parsear timestamp original y shiftearlo
                tse = _parse_ts(rec.get("timestamp")) or _shift_ts_to_today(rec.get("timestamp"))
            p = Point("chosen_error").tag("id", unit)
            if chosen_error_abs is not None:
                p = p.field("error_abs", float(chosen_error_abs))
            if chosen_error_rel is not None:
                p = p.field("error_rel", float(chosen_error_rel))
            p = p.time(tse, WritePrecision.S)
            _write_api.write(bucket=INFLUX_BUCKET, record=p)
            print(f"[collector] ✅ Escrito chosen_error: {unit} @ {tse.isoformat()}", flush=True)
        except Exception as e:
            print(f"[collector] ❌ Error guardando chosen_error: {e}", flush=True)

    # AP2: Errores por modelo (relativos) para análisis detallado
    errors_rel = rec.get("hyper_errors_rel")
    if isinstance(errors_rel, dict):
        try:
            tser = _parse_ts(rec.get("ts_pred")) or _shift_ts_to_today(rec.get("timestamp"))
            for model_name, err_rel in errors_rel.items():
                _write_api.write(
                    bucket=INFLUX_BUCKET,
                    record=(
                        Point("model_errors")
                        .tag("id", unit)
                        .tag("model", str(model_name))
                        .field("error_rel", float(err_rel))
                        .time(tser, WritePrecision.S)
                    ),
                )
        except Exception as e:
            print(f"[collector] ❌ Error guardando model_errors: {e}")

    # AP3: Rankings y rewards por modelo
    rankings = rec.get("rankings")
    rewards = rec.get("rewards")
    if isinstance(rankings, dict) or isinstance(rewards, dict):
        try:
            ts_ap3 = _parse_ts(rec.get("ts_pred")) or _shift_ts_to_today(rec.get("timestamp"))
            
            # Escribir rankings
            if isinstance(rankings, dict):
                for model_name, rank in rankings.items():
                    _write_api.write(
                        bucket=INFLUX_BUCKET,
                        record=(
                            Point("model_rankings")
                            .tag("id", unit)
                            .tag("model", str(model_name))
                            .field("rank", int(rank))
                            .time(ts_ap3, WritePrecision.S)
                        ),
                    )
            
            # Escribir rewards
            if isinstance(rewards, dict):
                for model_name, reward in rewards.items():
                    _write_api.write(
                        bucket=INFLUX_BUCKET,
                        record=(
                            Point("model_rewards")
                            .tag("id", unit)
                            .tag("model", str(model_name))
                            .field("reward", int(reward))
                            .time(ts_ap3, WritePrecision.S)
                        ),
                    )
        except Exception as e:
            print(f"[collector] ❌ Error guardando rankings/rewards: {e}")

    # AP3: chosen_by_error vs chosen_by_weight (para comparación)
    chosen_by_error = rec.get("chosen_by_error")
    chosen_by_weight = rec.get("chosen_by_weight")
    choices_differ = rec.get("choices_differ")
    if chosen_by_error or chosen_by_weight:
        try:
            ts_choice = _parse_ts(rec.get("ts_pred")) or _shift_ts_to_today(rec.get("timestamp"))
            p = Point("weight_decisions").tag("id", unit)
            if chosen_by_error:
                p = p.field("chosen_by_error", str(chosen_by_error))
            if chosen_by_weight:
                p = p.field("chosen_by_weight", str(chosen_by_weight))
            if choices_differ is not None:
                p = p.field("choices_differ", 1 if choices_differ else 0)
            p = p.time(ts_choice, WritePrecision.S)
            _write_api.write(bucket=INFLUX_BUCKET, record=p)
        except Exception as e:
            print(f"[collector] ❌ Error guardando weight_decisions: {e}")



def run_consumer():
    print("[collector] 🚀 Iniciando run_consumer()...")
    while True:
        try:
            print("[collector] ⏳ Esperando Kafka...")
            wait_for_kafka(BROKER, timeout=300)
            consumer = KafkaConsumer(
                TOUT,
                bootstrap_servers=BROKER,
                auto_offset_reset="earliest",  # Leer todos los mensajes desde el principio
                enable_auto_commit=True,       # Habilitar auto-commit para guardar progreso
                group_id="collector-v7"        # Nuevo group_id para resetear offset
            )
            print(f"[collector] ✅ Suscrito a {TOUT}, esperando mensajes...", flush=True)

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
                except Exception as e:
                    print(f"[collector] ⚠️ Error en consumer loop: {e}")
                    time.sleep(5)

                # Deduplicación (opcional)
                k = tuple(rec.get(f) for f in _key_fields)
                with _lock:
                    _last_by_key[k] = rec

                # Writting in Influx
                write_to_influx(rec)

                print(f"[collector] ⚙️ recibido key={k}")

        except Exception as e:
            print(f"[collector] ⚠️ Error en consumer loop: {e}")
            time.sleep(5)

@app.on_event("startup")
def start_bg():
    pass  # Deshabilitado - el thread se inicia en __main__

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
    import sys
    sys.stdout.flush()
    print("[collector] 🚀 Iniciando aplicación...", flush=True)
    print("[collector] 🔧 Iniciando thread de run_consumer()...", flush=True)
    threading.Thread(target=run_consumer, daemon=True).start()
    print("[collector] ✅ Thread iniciado, arrancando servidor HTTP...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8082)

