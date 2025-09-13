import os, json
from kafka import KafkaConsumer, KafkaProducer

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TIN = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")
MODE = os.getenv("PROCESS_MODE", "identity")  # procedure to apply

def plus_one(record):
    out = {}
    for k, v in record.items():
        if isinstance(v, (int, float)):
            out[k] = v + 1
        else:
            out[k] = v
    return out

consumer = KafkaConsumer(TIN, bootstrap_servers=BROKER,
                         value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                         auto_offset_reset="earliest", enable_auto_commit=True,
                         group_id="agent-v1")
producer = KafkaProducer(bootstrap_servers=BROKER,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

for msg in consumer:
    rec = msg.value
    if MODE == "plus_one":
        rec = plus_one(rec)
    producer.send(TOUT, rec)
    producer.flush()
