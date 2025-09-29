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

    # Mapea al formato estándar id,timestamp,var si “Input” era CSV
    if not df.empty and "__src_format" in df.columns and (df["__src_format"] == "csv").any():
        # Elegimos v1 como “var”
        select_cols = []
        if set(["unit_id", "ts", "v1"]).issubset(df.columns):
            out = df[["unit_id", "ts", "v1"]].rename(columns={
                "unit_id": "id", "ts": "timestamp", "v1": "var"
            })
            # (opcional) ordenar por clave
            out = out.sort_values(["id", "timestamp"])
            out.to_csv(OUTPATH.replace(".parquet", ".csv"), index=False)
            return {"rows": len(out), "path": OUTPATH.replace(".parquet", ".csv")}
        # Si no tenemos ese layout, caemos a la salida genérica abajo

    # SALIDA GENÉRICA (igual que antes)
    if not df.empty:
        if OUTPATH.endswith(".parquet"):
            df.to_parquet(OUTPATH, index=False)
        elif OUTPATH.endswith(".csv"):
            df.to_csv(OUTPATH, index=False)
        else:
            df.to_json(OUTPATH, orient="records", lines=True)

    return {"rows": len(df), "path": OUTPATH}



if __name__ == "__main__":
    t = threading.Thread(target=run_consumer, daemon=True)
    t.start()
    uvicorn.run(app, host="0.0.0.0", port=8082)
