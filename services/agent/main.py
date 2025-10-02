import os, json, time, socket, datetime
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.delete_api import DeleteApi
from datetime import datetime, timedelta


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

# --- esperar a Kafka ---
def wait_for_kafka(broker: str, timeout=120):
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

from datetime import datetime

def write_timeseries(rec):
    unit = rec.get("unit_id") or rec.get("id") or "unknown"

    p = Point("telemetry").tag("unit", unit)

    # Añadimos las métricas numéricas
    for f in ["v1", "v2", "v3", "v4", "v5", "var"]:
        if f in rec:
            try:
                p = p.field(f, float(rec[f]))
            except:
                pass

    # Forzar timestamp actual (no parsear el campo timestamp del mensaje)
    ts_str = rec.get("timestamp")
    ts = parse_or_now(ts_str)
    p = p.time(ts, WritePrecision.S)


    write_api.write(bucket=INFLUX_BUCKET, record=p)

def main():
    wait_for_kafka(BROKER)

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

    print(f"[agent] escuchando {TIN} y publicando en {TOUT}")
    for msg in consumer:
        rec = msg.value
        print(f"[agent] recibido: {rec}")
        try:
            write_timeseries(rec)
        except Exception as e:
            print("[agent] influx write error:", e)

        if FLAVOR != "training":
            if "v1" in rec:
                try:
                    rec["v1"] = round(float(rec["v1"]) * 1.1, 6)
                except:
                    pass
            producer.send(TOUT, rec)

if __name__ == "__main__":
    main()
