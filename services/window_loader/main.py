import os, time
import pandas as pd
from kafka import KafkaProducer
from fastapi import FastAPI
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

@app.post("/start")
def start():
    df = pd.read_parquet(DATA_PATH) if DATA_PATH.endswith(".parquet") else pd.read_csv(DATA_PATH)
    p = _producer()
    for i, row in df.iterrows():
        msg = row.to_dict()
        p.send(TOPIC_RAW, msg)
        p.send(TOPIC_AGENT_IN, msg)  # pasa al agente
        p.flush()
        time.sleep(0.001)  # simula streaming; ajusta por frecuencia real
    return {"sent": len(df)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
