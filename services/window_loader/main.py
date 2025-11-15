import os, time, json
import pandas as pd
from kafka import KafkaProducer
from fastapi import FastAPI, HTTPException
import uvicorn

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC_RAW = os.getenv("TOPIC_RAW", "telemetry.raw")                   # opcional (telemetría normalizada)
TOPIC_AGENT_IN = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")    # entrada al agente
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))
DATA_DIR = "/app/data"
# pacing para simular streaming (0 = sin espera)
PLAY_SPEED_MS_DEFAULT = int(os.getenv("PLAY_SPEED_MS", "0"))

app = FastAPI()

def _producer():
    return KafkaProducer(
        bootstrap_servers=BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

def _read_any(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".csv":
        try:
            df = pd.read_csv(path, skipinitialspace=True)  # ← clave
        except UnicodeDecodeError:
            print("[loader] CSV no es UTF-8; reintento con latin-1…")
            df = pd.read_csv(path, encoding="latin-1", skipinitialspace=True)
        except Exception as e:
            print(f"[loader] error leyendo CSV (primer intento): {e}")
            df = pd.read_csv(path, header=None, names=["timestamp", "id", "var"])
            print("[loader] leído como CSV sin encabezado con columnas timestamp,id,var")
        df.columns = [c.strip() for c in df.columns]       # ← asegura sin espacios
        df["__src_format"] = "csv"
        return df
    elif ext == ".parquet":
        df = pd.read_parquet(path)
        df.columns = [c.strip() for c in df.columns]       # ← simetría
        df["__src_format"] = "parquet"
        return df
    else:
        raise ValueError(f"Formato no soportado: {ext}")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    # 1) NORMALIZA CABECERAS
    df.columns = [str(c).strip().lower() for c in df.columns] 

    # 2) RENOMBRADOS COMUNES
    rename_map = {}
    for src, dst in [("time","timestamp"), ("unit","id"), ("category","id"),
                     ("value","var"), ("traffic","var"), ("count","var"), ("y","var")]:
        if src in df.columns and dst not in df.columns:
            rename_map[src] = dst
    if rename_map:
        df = df.rename(columns=rename_map)

    # 3) COLUMNAS MÍNIMAS
    required = ["timestamp", "id", "var"]
    if set(required) - set(df.columns):
        # fallback si trae exactamente 3 columnas con nombres raros:
        if len(df.columns) == 3:
            df.columns = required
        else:
            missing = [c for c in required if c not in df.columns]
            raise ValueError(f"Faltan columnas requeridas: {missing}; columnas={list(df.columns)}")

    # 4) TIPOS + LIMPIEZA
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["id"] = df["id"].astype(str).str.strip()     # 👈 recorta IDs
    df["var"] = pd.to_numeric(df["var"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["timestamp", "var"])
    if len(df) != before:
        print(f"[loader] descartadas {before-len(df)} filas por NaN en timestamp/var")

    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.sort_values(by=["timestamp"], kind="stable").reset_index(drop=True)
    return df


def _emit_dataframe(df: pd.DataFrame, speed_ms: int = 0):
    prod = _producer()
    rows = df.to_dict(orient="records")

    # resumen
    ids = sorted(set(r["id"] for r in rows))
    t0 = rows[0]["timestamp"] if rows else None
    t1 = rows[-1]["timestamp"] if rows else None
    print(f"[loader] ids={ids}  rows={len(rows)}  window=[{t0} .. {t1}]  speed_ms={speed_ms}")

    # envío
    if BATCH_SIZE <= 1:
        for r in rows:
            prod.send(TOPIC_AGENT_IN, r)
            # copia normalizada opcional al topic RAW
            if TOPIC_RAW:
                prod.send(TOPIC_RAW, r)
            if speed_ms > 0:
                time.sleep(speed_ms / 1000.0)
    else:
        # envío por lotes (sin pacing entre registros)
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i+BATCH_SIZE]
            for r in batch:
                prod.send(TOPIC_AGENT_IN, r)
                if TOPIC_RAW:
                    prod.send(TOPIC_RAW, r)
            prod.flush()
            if speed_ms > 0:
                time.sleep(speed_ms / 1000.0)

    prod.flush()

@app.post("/trigger")
async def trigger_window_loader(payload: dict = {}):
    """
    payload:
      - source: nombre del fichero dentro de /app/data (obligatorio)
      - speed_ms: pacing opcional (ms entre mensajes) — override de PLAY_SPEED_MS
      - id_prefix: prefijo opcional para los ids (ej. 'unit-') para demos
    """
    source = payload.get("source")
    if not source:
        raise HTTPException(status_code=400, detail="missing 'source'")
    speed_ms = int(payload.get("speed_ms", PLAY_SPEED_MS_DEFAULT))
    id_prefix = payload.get("id_prefix")

    path = os.path.join(DATA_DIR, source)
    print(f"[loader] intentando abrir {path}")
    print(f"[loader] contenido de /app/data: {os.listdir(DATA_DIR)}")

    df = _read_any(path)
    df = _normalize(df)

    if id_prefix:
        df["id"] = id_prefix + df["id"].astype(str)

    _emit_dataframe(df, speed_ms=speed_ms)

    # persistimos la versión normalizada para inspección
    ext = ".csv" if (df.get("__src_format") == "csv").any() else ".parquet"
    out_path = os.path.join(DATA_DIR, f"processed_window{ext}")
    if ext == ".csv":
        df.to_csv(out_path, index=False)
    else:
        df.to_parquet(out_path, index=False)

    return {"rows": int(len(df)), "path": out_path, "unique_ids": sorted(df["id"].unique().tolist())}

def start(path: str):
    """Compat: misma lógica que trigger() pero recibiendo una ruta absoluta."""
    df = _read_any(path)
    df = _normalize(df)
    _emit_dataframe(df, speed_ms=PLAY_SPEED_MS_DEFAULT)
    out_path = os.path.join(DATA_DIR, f"processed_window{'.csv' if (df.get('__src_format') == 'csv').any() else '.parquet'}")
    if (df.get("__src_format") == "csv").any():
        df.to_csv(out_path, index=False)
    else:
        df.to_parquet(out_path, index=False)
    return {"rows": int(len(df)), "path": out_path, "unique_ids": sorted(df["id"].unique().tolist())}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8083)
