from kafka import KafkaProducer
import json
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
msg = {"id":"unit_test_01","unit_id":"unit_test_01","var": 1.23}
producer.send('telemetry.agent.in', value=msg)
producer.flush()
print("mensaje enviado")