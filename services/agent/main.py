import os, json
from kafka import KafkaConsumer, KafkaProducer

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TIN  = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")
MODE = os.getenv("PROCESS_MODE", "identity") 

consumer = KafkaConsumer(TIN, bootstrap_servers=BROKER,
                         value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                         auto_offset_reset="earliest", enable_auto_commit=True,
                         group_id="agent-v1")
producer = KafkaProducer(bootstrap_servers=BROKER,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                         key_serializer=lambda k: k.encode('utf-8'))

def process(msg: dict) -> dict:
    if MODE == "identity":
        return msg
    if MODE == "scale_v1":
        # asegura tipos
        msg["v1"] = float(msg["v1"]) * 1.1
        return msg
    # reserva para futuros modos
    return msg

for rec in consumer:
    out = process(rec.value)
    key = out.get("unit_id","")
    producer.send(TOUT, out, key=key)
    print(f"[agent] mode={MODE} in={TIN} out={TOUT} msg_keys={list(out.keys())}")
    producer.flush()
