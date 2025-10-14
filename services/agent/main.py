import os, json, time, socket, datetime
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.delete_api import DeleteApi
from datetime import datetime, timedelta
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
BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")  # p.ej. "kafka:9092"
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
        time.sleep(300)  # cada 5 min



def query_training_rows(unit: str, lookback_days: int = 30):
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{lookback_days}d)
      |> filter(fn: (r) => r["_measurement"] == "telemetry" and r["unit"] == "{unit}" and r["_field"] == "var")
      |> keep(columns: ["_time","_value"])
    '''
    tables = client.query_api().query(org=INFLUX_ORG, query=flux)
    rows = []
    for t in tables:
        for r in t.records:
            rows.append({"_time": r.get_time(), "var": float(r.get_value())})
    return rows

def learner_loop(unit_selector="*"):
    # versión simple: si hay diferentes units, itera por cada una
    # aquí, para MVP, intentamos entrenar con la primera unit vista en el último día
    while True:
        try:
            # descubre units
            flux_units = f'''
            import "influxdata/influxdb/schema"
            schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "unit")
            '''
            tabs = client.query_api().query(org=INFLUX_ORG, query=flux_units)
            units = list({ r.get_value() for t in tabs for r in t.records if r.get_value() })
            for u in units:
                rows = query_training_rows(u, lookback_days=LEARN_LOOKBACK_DAYS)
                if rows:
                    model.update(rows)
                    print(f"[agent] learner: updated model with {len(rows)} rows for unit={u}")
                    # opcionalmente persistimos el modelo
                    try:
                        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
                        model.save(MODEL_PATH)
                    except Exception as e:
                        print("[agent] no se pudo guardar modelo:", e)
            # entrena cada 24h (ajusta si quieres acelerar)
            time.sleep(LEARN_PERIOD_SEC)
        except Exception as e:
            print("[agent] learner error:", e)
            time.sleep(60)

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

# --- cliente Influx (sincrono para depurar) ---
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
delete_api = client.delete_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

MODEL_PATH = os.getenv("MODEL_PATH", "/app/data/model_naive_daily.json")
PRED_HORIZON_MIN = int(os.getenv("PRED_HORIZON_MIN", "30")) # horizonte predicción en minutos
model = NaiveDailyProfileModel(slot_minutes=30, horizon_slots=PRED_HORIZON_MIN // 30)
# Si existe un modelo guardado, cárgalo
try:
    if os.path.exists(MODEL_PATH):
        model.load(MODEL_PATH)
except Exception as e:
    print("[agent] no se pudo cargar modelo:", e)

def parse_or_now(ts_str):
    try:
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        # Corrige al día de hoy, misma hora/min/seg
        today = datetime.utcnow().date()
        ts = datetime.combine(today, ts.time())
        return ts
    except:
        return datetime.utcnow()

def enforce_cap_per_unit():
    q = client.query_api()
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "unit")
    '''
    units = [r.get_value() for t in q.query(org=INFLUX_ORG, query=flux) for r in t.records]

    for u in units:
        flux2 = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "telemetry" and r["unit"] == "{u}")
          |> count()
        '''
        tables = q.query(org=INFLUX_ORG, query=flux2)
        count = sum(r.get_value() for t in tables for r in t.records)

        if count > MAX_ROWS_PER_UNIT:
            # borrar datos más antiguos de 7 días para este unit
            start = "1970-01-01T00:00:00Z"
            stop = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            delete_api.delete(start, stop, f'_measurement="telemetry" AND unit="{u}"',
                              bucket=INFLUX_BUCKET, org=INFLUX_ORG)
            print(f"[agent] purgados datos antiguos de unit={u}")


def write_timeseries(rec):
    unit = rec.get("unit_id") or rec.get("id") or "unknown"
    print(f"[agent] escribiendo en Influx unit={unit}")

    p = Point("telemetry").tag("unit", unit)

    # Añadimos las métrricas numéricas (sin duplicar el for)
    fields_added = False
    for f in ["v1", "v2", "v3", "v4", "v5", "var"]:
        if f in rec:
            try:
                p = p.field(f, float(rec[f]))
                fields_added = True
            except Exception as e:
                print("[agent] field cast error:", e, "rec=", rec)

    if not fields_added:
        p = p.field("dummy", 1.0)

    ts_str = rec.get("timestamp")
    ts = parse_or_now(ts_str)
    p = p.time(ts, WritePrecision.S)

    if "var" in rec:
        try:
            model.update_buffer(float(rec["var"]))
        except Exception:
            pass

    write_api.write(bucket=INFLUX_BUCKET, record=p)



    # Si no había ninguno de esos campos, escribe aunque sea un flag
    if not fields_added:
        p = p.field("dummy", 1.0)

    # Forzar timestamp actual (no parsear el campo timestamp del mensaje)
    ts_str = rec.get("timestamp")
    ts = parse_or_now(ts_str)
    p = p.time(ts, WritePrecision.S)
    if "var" in rec:
        try:
            model.update_buffer(float(rec["var"]))
        except Exception:
            pass

    write_api.write(bucket=INFLUX_BUCKET, record=p)

def write_prediction(unit: str, when: datetime, yhat: float):
    p = Point("telemetry").tag("unit", unit).field("prediction", float(yhat)).time(when, WritePrecision.S)
    write_api.write(bucket=INFLUX_BUCKET, record=p)


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

    # === arranque de tareas en background (ahora SÍ dentro de main) ===
    threading.Thread(target=auto_purge, daemon=True).start()
    threading.Thread(target=learner_loop, daemon=True).start()

    print(f"[agent] escuchando {TIN} y publicando en {TOUT}")
    for msg in consumer:
        # 1) deserialización segura
        try:
            rec = msg.value
            print(f"[agent] recibido: {rec}")
        except Exception as e:
            print("[agent] error deserializando:", e, msg.value)
            continue

        # 2) escribir medida en Influx + actualizar buffer del modelo
        try:
            write_timeseries(rec)
        except Exception as e:
            print("[agent] influx write error:", e)

        # 3) predicción t+Δ (MVP: yhat = var@t; fallback: último del buffer; si no, 0.0)
        try:
            base_ts = parse_or_now(rec.get("timestamp"))
            ts_pred = base_ts + timedelta(minutes=PRED_HORIZON_MIN)

            if "var" in rec:
                try:
                    yhat = float(rec["var"])
                except Exception:
                    # fallback al último del buffer del modelo
                    yhat = float(model.buffer[-1]) if getattr(model, "buffer", None) else 0.0
            else:
                yhat = float(model.buffer[-1]) if getattr(model, "buffer", None) else 0.0

            unit = rec.get("unit_id") or rec.get("id") or "unknown"
            print(f"[agent] prediction: unit={unit} ts_pred={ts_pred} yhat={yhat}")
            write_prediction(unit, ts_pred, yhat)
            print(f"[agent] prediction: unit={unit} ts_pred={ts_pred} yhat={yhat}")

            # publicar enriquecido en agent.out
            enriched = dict(rec)
            enriched["yhat"] = yhat
            enriched["ts_pred"] = ts_pred.isoformat()
            enriched["mode"] = FLAVOR
            if "timestamp" in enriched and "ts" not in enriched:
                enriched["ts"] = enriched["timestamp"]  # normalizamos para collector
            producer.send(TOUT, enriched)

        except Exception as e:
            print("[agent] prediction error:", e)
            # al menos emite el registro original
            if "timestamp" in rec and "ts" not in rec:
                rec["ts"] = rec["timestamp"]
            producer.send(TOUT, rec)

        if FLAVOR != "training":
            if "v1" in rec:
                try:
                    rec["v1"] = round(float(rec["v1"]) * 1.1, 6)
                except:
                    pass


if __name__ == "__main__":
    print(f"[agent] conectado a Influx {INFLUX_URL}, bucket={INFLUX_BUCKET}, org={INFLUX_ORG}", flush=True)
    print(f"[agent] escuchando {TIN} y publicando en {TOUT}", flush=True)
    # levantar FastAPI en background y loop principal
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning"), daemon=True).start()
    main()

