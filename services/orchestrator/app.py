
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
import aiofiles, os, httpx
from dotenv import load_dotenv
import os, requests

try:
    from metrics import METRICS
except Exception:
    METRICS = None

LOADER_URL = os.getenv("LOADER_URL", "http://window_loader:8081/start")
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://window_collector:8082/reset")
load_dotenv("config/app.env")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_methods=["*"],
    allow_headers=["*"],
)


DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

@app.post("/api/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    path = os.path.join(DATA_DIR, "uploaded.csv")
    async with aiofiles.open(path, "wb") as f:
        content = await file.read()
        await f.write(content)
    return {"saved": True, "path": path}

@app.post("/api/run_window")
async def run_window():
    # reset collector
    async with httpx.AsyncClient() as client:
        await client.post("http://window_collector:8082/reset")
        # dispara el loader
        r = await client.post("http://window_loader:8081/trigger", json={"source":"uploaded"})
        return {"triggered": True, "loader_response": r.json()}

@app.get("/api/flush")
async def flush():
    async with httpx.AsyncClient() as client:
        r = await client.get("http://window_collector:8082/flush")
        return r.json()

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/metrics")
def metrics():
    return METRICS.as_dict() if METRICS else {"status":"no-metrics"}

@app.post("/trigger")
def trigger():
    # reset collector (best-effort)
    try:
        requests.post(COLLECTOR_URL, timeout=5)
    except Exception as e:
        pass  # o guarda el error si te interesa

    try:
        r = requests.post(LOADER_URL, timeout=5)
        try:
            payload = r.json()
        except Exception:
            payload = {"raw": r.text, "note": "loader no devolvió JSON"}
        return {"status": "ok", "triggered": True, "loader_status_code": r.status_code, "loader_response": payload}
    except Exception as e:
        return {"status": "error", "triggered": False, "message": str(e)}
