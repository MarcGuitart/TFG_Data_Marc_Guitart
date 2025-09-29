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
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    except Exception as e:
        # Siempre devuelve JSON para que el orchestrator no casque con r.json()
        raise HTTPException(status_code=400, detail={"error": str(e), "path": path})

    p = _producer()
    for _, row in df.iterrows():
        msg = row.to_dict()
        p.send(TOPIC_RAW, msg)
        p.send(TOPIC_AGENT_IN, msg)
        p.flush()
        time.sleep(0.001)
    return {"sent": len(df), "path": path}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
