from kafka import KafkaProducer
import json, time, sys

BROKER = "localhost:9092"
TOPIC = "telemetry.agent.in"

def main():
    try:
        p = KafkaProducer(
            bootstrap_servers=BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=5000,
            api_version_auto_timeout_ms=5000
        )
        print("Producer creado. Enviando 3 mensajes de prueba...")
        for i in range(3):
            fut = p.send(TOPIC, {"id":"unit_test_debug","unit_id":"unit_test_debug","var": i})
            try:
                meta = fut.get(timeout=5)
                print(f"Enviado {i} -> topic={meta.topic} partition={meta.partition} offset={meta.offset}")
            except Exception as e:
                print("Error enviando mensaje:", e)
                p.close()
                sys.exit(1)
        p.flush()
        p.close()
        print("OK")
    except Exception as e:
        print("Fallo al crear producer / conectar:", e)
        sys.exit(2)

if __name__ == "__main__":
    main()