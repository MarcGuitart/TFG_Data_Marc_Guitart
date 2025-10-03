import os, time
import pandas as pd
from kafka import KafkaProducer
from fastapi import FastAPI, HTTPException
import uvicorn
import json

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC_RAW = os.getenv("TOPIC_RAW", "telemetry.raw")
TOPIC_AGENT_IN = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))
DATA_PATH = os.getenv("DATA_PATH", "/app/data/sample_window.parquet")
DATA_DIR = "/app/data"

app = FastAPI()

def _producer():
    return KafkaProducer(bootstrap_servers=BROKER,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

@app.post("/trigger")
async def trigger_window_loader(payload: dict = {}):
    source = payload.get("source")
    if not source:
        raise HTTPException(status_code=400, detail="missing 'source'")
    path = f"/app/data/{source}"
    return start(path)

def start(path: str):
    print(f"[loader] intentando abrir {path}")
    print(f"[loader] contenido de /app/data: {os.listdir('/app/data')}")
    
    ext = os.path.splitext(path)[-1].lower()

    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Formato no soportado: {ext}")

    # anotamos el formato en el dataframe
    df["__src_format"] = "csv" if ext == ".csv" else "parquet"

    # produce a Kafka
    producer = _producer()
    for _, row in df.iterrows():
        record = row.to_dict()
        producer.send(TOPIC_AGENT_IN, record)
    producer.flush()

    # salida en el mismo formato
    output_path = os.path.join(DATA_DIR, f"processed_window{ext}")
    if ext == ".csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_parquet(output_path, index=False)

    return {"rows": len(df), "path": output_path}

