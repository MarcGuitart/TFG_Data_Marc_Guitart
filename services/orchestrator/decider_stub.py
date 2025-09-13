import os, json, time, threading
USE_CONFLUENT = os.getenv("USE_CONFLUENT", "0") == "1"

TOPIC_CONTROL = os.getenv("TOPIC_AGENT_CONTROL", "agent.control")
BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
INTERVAL_S = int(os.getenv("DECIDER_INTERVAL_S", "10"))

if USE_CONFLUENT:
    from confluent_kafka import Producer
    producer = Producer({"bootstrap.servers": BROKER})
    def send(msg):
        producer.produce(TOPIC_CONTROL, value=json.dumps(msg).encode("utf-8"))
        producer.poll(0)
        producer.flush()
else:
    from kafka import KafkaProducer
    producer = KafkaProducer(bootstrap_servers=BROKER,
                             value_serializer=lambda v: json.dumps(v).encode("utf-8"))
    def send(msg):
        producer.send(TOPIC_CONTROL, msg)
        producer.flush()

def loop():
    while True:
        msg = {
            "action": "noop",
            "ts": time.time(),
            "reason": "stub",
        }
        send(msg)
        time.sleep(INTERVAL_S)

if __name__ == "__main__":
    loop()
