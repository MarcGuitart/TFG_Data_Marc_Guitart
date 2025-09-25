import os, json
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point, WritePrecision

# === CONFIGURACIÓN ===
FLAVOR = os.getenv("FLAVOR", "inference")
BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TIN = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")
MAX_ROWS_PER_UNIT = int(os.getenv("MAX_ROWS_PER_UNIT", "1000"))

# === INFLUX CLIENT ===
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api()

def write_timeseries(rec):
    unit = rec.get("unit_id") or rec.get("id") or "unknown"
    ts = rec.get("ts") or rec.get("timestamp")
    p = Point("telemetry").tag("unit", unit)
    for f in ["v1", "v2", "v3", "v4", "v5", "var"]:
        if f in rec:
            try:
                p = p.field(f, float(rec[f]))
            except:
                pass
    if ts:
        p = p.time(ts, WritePrecision.S)
    write_api.write(bucket=INFLUX_BUCKET, record=p)

def enforce_cap_per_unit():
    from influxdb_client.client.query_api import QueryApi
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
          |> sort(columns: ["_time"], desc: true)
          |> drop(columns: ["_start","_stop"])
        '''
        tables = q.query(org=INFLUX_ORG, query=flux2)
        count = sum(len(t.records) for t in tables)
        if count > MAX_ROWS_PER_UNIT:
            # dejar anotado para future delete by threshold
            pass

def main():
    consumer = KafkaConsumer(TIN, bootstrap_servers=BROKER,
                             value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                             auto_offset_reset="earliest", enable_auto_commit=True,
                             group_id="agent-v1")
    producer = KafkaProducer(bootstrap_servers=BROKER,
                             value_serializer=lambda v: json.dumps(v).encode("utf-8"))

    for msg in consumer:
        rec = msg.value
        try:
            write_timeseries(rec)
        except Exception as e:
            print("[agent] influx write error:", e)

        if FLAVOR == "training":
            continue  # no publicar nada

        if "v1" in rec:
            rec["v1"] = round(float(rec["v1"]) * 1.1, 6)

        producer.send(TOUT, rec)

if __name__ == "__main__":
    main()
