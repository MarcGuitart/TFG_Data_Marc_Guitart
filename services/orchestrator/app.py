from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import httpx, requests, time, os
from fastapi import UploadFile, File
import aiofiles
from dotenv import load_dotenv
from fastapi import HTTPException

# === METRICS STATE ===
start_time = time.time()
points_written = 0
last_flush_rows = 0

# === CONFIG ===
MODEL_PATH = os.getenv("MODEL_PATH", "/app/data/model_naive_daily.json")
load_dotenv("config/app.env")
LOADER_URL = os.getenv("LOADER_URL", "http://window_loader:8083/trigger")
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://window_collector:8082/reset")
COLLECTOR_FLUSH = os.getenv("COLLECTOR_FLUSH", "http://window_collector:8082/flush")

# === APP ===
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
    async with aiofiles.open(path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    return {"saved": True, "path": path}


@app.post("/api/run_window")
def run_window():
    global last_flush_rows
    try:
        r = requests.post(LOADER_URL, json={"source": "uploaded.csv"})
        r.raise_for_status()
        loader_response = r.json()

        # consultar collector
        try:
            r2 = requests.get(COLLECTOR_FLUSH, timeout=5)
            if r2.ok:
                data = r2.json()
                last_flush_rows = data.get("rows", 0)
        except Exception as e:
            print(f"[orchestrator] error al consultar collector: {e}")

        return {"triggered": True, "status_code": 200, "loader_response": loader_response}
    except Exception as e:
        return {"triggered": False, "status_code": 500, "error": str(e)}

@app.get("/api/flush")
async def flush():
    async with httpx.AsyncClient() as client:
        r = await client.get(COLLECTOR_FLUSH)
        return r.json()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics/prometheus")
def metrics_prometheus():
    uptime = int(time.time() - start_time)
    return PlainTextResponse(
        f"uptime_sec {uptime}\n"
        f"points_written {points_written}\n"
        f"last_flush_rows {last_flush_rows}\n"
    )

@app.get("/api/model/export")
def model_export():
    try:
        with open(MODEL_PATH, "r") as f:
            return {"model": json.load(f)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="model not found")

@app.get("/metrics")
def metrics():
    uptime = int(time.time() - start_time)
    return {
        "uptime_sec": uptime,
        "points_written": points_written,
        "last_flush_rows": last_flush_rows,
    }

@app.post("/trigger")
def trigger():
    # reset collector
    try:
        requests.post(COLLECTOR_URL, timeout=5)
    except Exception:
        pass

    try:
        r = requests.post(LOADER_URL, json={"source": "uploaded.csv"}, timeout=5)
        try:
            payload = r.json()
        except Exception:
            payload = {"raw": r.text, "note": "loader no devolvió JSON"}
        return {
            "status": "ok",
            "triggered": True,
            "loader_status_code": r.status_code,
            "loader_response": payload,
        }
    except Exception as e:
        return {"status": "error", "triggered": False, "message": str(e)}
