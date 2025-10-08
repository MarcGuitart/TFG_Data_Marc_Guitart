import os, json, threading, socket, time
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from fastapi import FastAPI
import uvicorn

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")
TPROC = os.getenv("TOPIC_PROCESSED", "telemetry.processed")
OUTPATH = os.getenv("OUTPUT_PATH", "/app/data/processed_window.parquet")
os.makedirs(os.path.dirname(OUTPATH), exist_ok=True)

app = FastAPI()
_lock = threading.Lock()
_last_by_key = {}


def wait_for_kafka(broker="kafka:9092", timeout=120):
    host, port = broker.split(":")
    port = int(port)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                print(f"[collector] ✅ Kafka OK en {broker}")
                return
        except Exception as e:
            print(f"[collector] esperando Kafka {broker} ... {e}")
            time.sleep(2)
    raise RuntimeError(f"[collector] ❌ Kafka no disponible en {broker}")


def run_consumer():
    wait_for_kafka(BROKER)

    while True:
        try:
            consumer = KafkaConsumer(
                TOUT,
                bootstrap_servers=BROKER,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                group_id="collector-v3"
            )
            consumer.poll(timeout_ms=1000)
            consumer.seek_to_beginning()
            print(f"[collector] ✅ Suscrito a {TOUT}, esperando mensajes...")

            producer = KafkaProducer(
                bootstrap_servers=BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )

            key_fields = [s.strip() for s in os.getenv("DEDUP_KEY", "timestamp,id").split(",") if s.strip()]

            for msg in consumer:
                try:
                    rec = json.loads(msg.value.decode("utf-8"))
                except Exception as e:
                    print("[collector] ❌ Error decoding message:", e)
                    continue

                # Publica en 'telemetry.processed'
                producer.send(TPROC, rec)

                # Deduplicación
                k = tuple(rec.get(f) for f in key_fields)
                with _lock:
                    _last_by_key[k] = rec

                print(f"[collector] ⚙️ recibido: {k}")

        except Exception as e:
            print(f"[collector] ⚠️ Error en consumer loop: {e}")
            time.sleep(5)


@app.on_event("startup")
def start_bg():
    threading.Thread(target=run_consumer, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset():
    global _last_by_key
    with _lock:
        _last_by_key = {}
    try:
        os.remove(OUTPATH)
    except FileNotFoundError:
        pass
    return {"status": "reset"}


@app.get("/flush")
def flush():
    with _lock:
        snapshot = list(_last_by_key.values())

    df = pd.DataFrame(snapshot)
    if df.empty:
        print("[collector] ⚠️ No hay datos para flush()")
        return {"rows": 0, "path": OUTPATH}

    ext = ".parquet"
    if "__src_format" in df.columns and (df["__src_format"] == "csv").any():
        ext = ".csv"

    out_path = OUTPATH.replace(".parquet", ext)
    if ext == ".csv":
        df.to_csv(out_path, index=False)
    else:
        df.to_parquet(out_path, index=False)

    print(f"[collector] 💾 Guardado {len(df)} filas en {out_path}")
    return {"rows": len(df), "path": out_path}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
