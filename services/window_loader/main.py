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
        # 1) lectura robusta de CSV
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            print("[loader] CSV no es UTF-8; reintento con latin-1…")
            df = pd.read_csv(path, encoding="latin-1")
        except Exception as e:
            print(f"[loader] error leyendo CSV (primer intento): {e}")
            # fallback: sin encabezado, 3 columnas esperadas
            try:
                df = pd.read_csv(path, header=None, names=["timestamp", "id", "var"])
                print("[loader] leído como CSV sin encabezado con columnas timestamp,id,var")
            except Exception as e2:
                print(f"[loader] error leyendo CSV (fallback sin header): {e2}")
                raise
    elif ext == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Formato no soportado: {ext}")

    # 2) normalización de columnas mínimas
    #    ajusta estos renames si tu CSV usa otros nombres
    rename_map = {}
    # mapeos comunes
    for src, dst in [("time","timestamp"), ("unit","id"), ("value","var"), ("category","id")]:
        if src in df.columns and dst not in df.columns:
            rename_map[src] = dst
    if rename_map:
        df = df.rename(columns=rename_map)

    # columnas obligatorias
    required = ["timestamp", "id", "var"]
    missing = [c for c in required if c not in df.columns]
    # fallback: si hay exactamente 3 columnas y faltan requeridas, forzar nombres
    if missing:
        if len(df.columns) == 3:
            print(f"[loader] normalizando columnas genéricas -> {required}")
            df.columns = required
            missing = []
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}; columnas={list(df.columns)}")

    # 3) formateo de timestamp a 'YYYY-MM-DD HH:MM:SS'
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        bad = int(df["timestamp"].isna().sum())
        print(f"[loader] WARNING: {bad} filas con timestamp inválido")
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 4) tipo numérico de var
    df["var"] = pd.to_numeric(df["var"], errors="coerce")
    # limpia espacios y asegura id str
    df["id"] = df["id"].astype(str).str.strip()
    # descarta filas sin var o timestamp
    before = len(df)
    df = df.dropna(subset=["timestamp", "var"])
    if len(df) != before:
        print(f"[loader] descartadas {before-len(df)} filas por NaN en timestamp/var")

    # anotamos el formato en el dataframe
    df["__src_format"] = "csv" if ext == ".csv" else "parquet"

    # 5) produce a Kafka
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
