# services/agent/main.py
import os, json, time, socket, datetime, threading, logging, collections
from datetime import datetime, timedelta, timezone
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.delete_api import DeleteApi
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent")

# === MODELOS ===
try:
    # Modelo previo (lo conservamos para compatibilidad con learner/estado)
    from agent.model import NaiveDailyProfileModel
except ModuleNotFoundError:
    from model import NaiveDailyProfileModel

# --- HyperModel (nuevo) ---
# Permitimos dos rutas de import para no depender del layout exacto del paquete
try:
    from agent.hypermodel.hyper_model import HyperModel
except ModuleNotFoundError:
    try:
        from hypermodel.hyper_model import HyperModel
    except ModuleNotFoundError:
        # fallback muy directo si lo tienes plano
        from hyper_model import HyperModel

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

# --- HyperModel config ---
HYPER_CFG_PATH = os.getenv("HYPERMODEL_CONFIG", "/app/hypermodel/model_config.json")
HYPER_DECAY    = float(os.getenv("HYPERMODEL_DECAY", "0.95"))
HYPER_W_CAP    = float(os.getenv("HYPERMODEL_W_CAP", "10.0"))
BUFFER_LEN     = int(os.getenv("BUFFER_LEN", "32"))  # tamaño ventana por id

# === HTTP app (health) ===
app = FastAPI()
@app.get("/health")
def health(): return {"status": "ok"}

# === CLIENTES Influx ===
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
delete_api: DeleteApi = client.delete_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

# === UTILIDADES TIEMPO ===
def now_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc)

def shift_ts_to_today(ts_str: str | None) -> datetime:
    """
    Parsea 'YYYY-mm-dd HH:MM:SS' o ISO.
    Mantiene H/M/S del CSV pero pone la FECHA de HOY (UTC).
    """
    base = now_utc()
    if not ts_str:
        return base
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        t = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").time()
    except Exception:
        return base
    return datetime.combine(base.date(), t).replace(tzinfo=timezone.utc)

def parse_ts_keep_date(ts_str):
    """Parsea 'YYYY-mm-dd HH:MM:SS' o ISO y conserva fecha y hora; salida UTC."""
    if not ts_str:
        return now_utc()
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        dt = datetime.utcnow()
    return dt.replace(tzinfo=timezone.utc)

# === ESPERA KAFKA ===
def wait_for_kafka(broker: str, timeout=300):
    host, port = broker.split(":")
    port = int(port)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                log.info(f"Kafka OK en {broker}")
                return
        except Exception as e:
            log.info(f"Esperando Kafka {broker} ... {e}")
            time.sleep(2)
    raise RuntimeError(f"Kafka no disponible en {broker}")

# === MODELO DIARIO (legacy) ===
MODEL_PATH = os.getenv("MODEL_PATH", "/app/data/model_naive_daily.json")
SLOT_MINUTES = int(os.getenv("SLOT_MINUTES", "30"))
PRED_HORIZON_MIN = int(os.getenv("PRED_HORIZON_MIN", str(SLOT_MINUTES)))
model = NaiveDailyProfileModel(slot_minutes=SLOT_MINUTES, horizon_slots=max(1, PRED_HORIZON_MIN // SLOT_MINUTES))
try:
    if os.path.exists(MODEL_PATH):
        model.load(MODEL_PATH)
except Exception as e:
    log.warning("no se pudo cargar modelo diario: %s", e)

# === CAP POR UNIDAD ===
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
            log.info("purgados datos antiguos de id=%s", u)

def auto_purge():
    while True:
        try:
            enforce_cap_per_unit()
        except Exception as e:
            log.error("error en auto-purge: %s", e)
        time.sleep(300)

# === ESCRITURA TELEMETRÍA ===
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
                log.warning("field cast error: %s rec=%s", e, rec)
    if not fields_added:
        p = p.field("dummy", 1.0)
    ts = shift_ts_to_today(rec.get("timestamp"))
    p = p.time(ts, WritePrecision.S)
    if "var" in rec and rec["var"] is not None:
        try:
            model.update_buffer(float(rec["var"]))  # legacy buffer (no interfiere)
        except Exception:
            pass
    write_api.write(bucket=INFLUX_BUCKET, record=p)

def write_prediction(unit: str, when: datetime, yhat: float):
    p = Point("telemetry").tag("id", unit).field("prediction", float(yhat)).time(when, WritePrecision.S)
    write_api.write(bucket=INFLUX_BUCKET, record=p)

# === TRAINER (legacy, compatible con tag id) ===
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
    while True:
        try:
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
                        log.info("learner: updated model with %d rows for id=%s", len(rows), u)
                        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
                        model.save(MODEL_PATH)
                    except Exception as e:
                        log.error("learner: error updating/saving model: %s", e)
        except Exception as e:
            log.error("learner error: %s", e)
        time.sleep(LEARN_PERIOD_SEC)

# === HYPERMODEL STATE (por id) ===
buffers_by_id: dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=BUFFER_LEN))
hyper_by_id: dict[str, HyperModel] = {}
last_pred_by_id: dict[str, float] = {}

def get_hyper_for(unit_id: str) -> HyperModel:
    hm = hyper_by_id.get(unit_id)
    if hm is None:
        # instanciamos un HyperModel por id para que los pesos sean independientes por flujo
        hm = HyperModel(cfg_path=HYPER_CFG_PATH, decay=HYPER_DECAY, w_cap=HYPER_W_CAP)
        hyper_by_id[unit_id] = hm
        log.info("[hypermodel] creado para id=%s (cfg=%s, decay=%.3f, w_cap=%.1f)",
                 unit_id, HYPER_CFG_PATH, HYPER_DECAY, HYPER_W_CAP)
    return hm

# === MAIN LOOP ===
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

    log.info("escuchando %s y publicando en %s", TIN, TOUT)

    for msg in consumer:
        try:
            rec = msg.value
            log.info("[in] %s", rec)
        except Exception as e:
            log.error("error deserializando: %s %s", e, msg.value)
            continue

        # 1) Persistimos observación en Influx
        try:
            write_timeseries(rec)
        except Exception as e:
            log.error("influx write error: %s", e)

        # 2) Predicción con HyperModel (on-line, por id)
        try:
            unit = rec.get("unit_id") or rec.get("id") or "unknown"
            y_real = rec.get("var")
            base_ts = shift_ts_to_today(rec.get("timestamp"))

            # --- actualizar pesos con la VERDAD del tick anterior (si existía pred previa)
            if unit in last_pred_by_id and y_real is not None:
                hm = get_hyper_for(unit)
                try:
                    hm.update_weights(float(y_real))
                except Exception as e:
                    log.warning("[hypermodel] update_weights error: %s", e)

            # --- alimentar buffer y predecir siguiente paso
            buf = buffers_by_id[unit]
            if y_real is not None:
                try:
                    buf.append(float(y_real))
                except Exception:
                    pass

            hm = get_hyper_for(unit)
            y_hat, preds_by_model = hm.predict(list(buf))
            weights = hm.export_state()
            last_pred_by_id[unit] = y_hat

            # 3) Compatibilidad: conservamos tu horizonte y escritura de 'prediction'
            ts_pred = base_ts + timedelta(minutes=PRED_HORIZON_MIN)
            write_prediction(unit, ts_pred, y_hat)

            # 4) Publicamos mensaje enriquecido (compatible + telemetría HyperModel)
            enriched = dict(rec)
            enriched["yhat"] = float(y_hat)                  # COMPAT: collector la escribe en 'prediction'
            enriched["ts_pred"] = ts_pred.strftime("%Y-%m-%d %H:%M:%S")
            enriched["mode"] = FLAVOR
            if "timestamp" in enriched and "ts" not in enriched:
                enriched["ts"] = enriched["timestamp"]

            # Telemetría opcional (por si luego la colectas en otra measurement)
            enriched["hyper_y_hat"] = float(y_hat)
            enriched["hyper_models"] = preds_by_model
            enriched["hyper_weights"] = weights

            producer.send(TOUT, enriched)
            producer.flush()

            log.info("[pred] id=%s y=%s y_hat=%.6f buf=%d models=%s",
                     unit, str(y_real), y_hat, len(buf), ",".join(preds_by_model.keys()))

            # 5) Pequeño efecto demo (tu lógica original)
            if FLAVOR != "training" and "v1" in rec:
                try: enriched["v1"] = round(float(rec["v1"]) * 1.1, 6)
                except: pass

        except Exception as e:
            log.error("prediction error: %s", e)
            # En error, preserva flujo original
            if "timestamp" in rec and "ts" not in rec:
                rec["ts"] = rec["timestamp"]
            producer.send(TOUT, rec)

if __name__ == "__main__":
    log.info("conectado a Influx %s, bucket=%s, org=%s", INFLUX_URL, INFLUX_BUCKET, INFLUX_ORG)
    log.info("escuchando %s y publicando en %s", TIN, TOUT)
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning"), daemon=True).start()
    main()
