import os, json, threading
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
_buffer = []
_lock = threading.Lock()
_last_by_key = {}

@app.on_event("startup")
def start_bg():
    threading.Thread(target=run_consumer, daemon=True).start()

def run_consumer():
    consumer = KafkaConsumer(
        TOUT,
        bootstrap_servers=BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="collector-v1",
    )
    producer = KafkaProducer(
        bootstrap_servers=BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    # Campos de clave para deduplicar (orden estable)
    key_fields = [s.strip() for s in os.getenv("DEDUP_KEY", "ts,unit_id").split(",") if s.strip()]

    for msg in consumer:
        rec = msg.value
        # Publica en 'telemetry.processed' como “sink” intermedio (opcional)
        producer.send(TPROC, rec)

        # Construye la clave y guarda la última versión
        k = tuple(rec.get(f) for f in key_fields)
        with _lock:
            _last_by_key[k] = rec

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
        return {"rows": 0, "path": OUTPATH}

    # detectar formato original
    ext = ".parquet"
    if "__src_format" in df.columns:
        if (df["__src_format"] == "csv").any():
            ext = ".csv"

    out_path = OUTPATH.replace(".parquet", ext)
    if ext == ".csv":
        df.to_csv(out_path, index=False)
    else:
        df.to_parquet(out_path, index=False)

    return {"rows": len(df), "path": out_path}


if __name__ == "__main__":
    t = threading.Thread(target=run_consumer, daemon=True)
    t.start()
    uvicorn.run(app, host="0.0.0.0", port=8082)
