#!/usr/bin/env python3
from kafka import KafkaConsumer
import json
import time

print("[test] Creando consumer...")
consumer = KafkaConsumer(
    "telemetry.agent.in",
    bootstrap_servers="kafka:9092",
    group_id="test-debug-2",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    consumer_timeout_ms=5000
)

print("[test] Consumer creado. Leyendo mensajes...")
count = 0
for msg in consumer:
    print(f"[test] Mensaje {count}: {msg.value}")
    count += 1
    if count >= 3:
        break

print(f"[test] Leídos {count} mensajes")
consumer.close()
