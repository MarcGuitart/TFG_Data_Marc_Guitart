from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import PlainTextResponse
import httpx, requests, time, os, aiofiles, json
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta

# === METRICS STATE ===
start_time = time.time()
points_written = 0
last_flush_rows = 0

# === INFLUXDB CONFIG ===
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")

# === CONFIG ===
MODEL_PATH = os.getenv("MODEL_PATH", "/app/data/model_naive_daily.json")
load_dotenv("config/app.env")
LOADER_URL = os.getenv("LOADER_URL", "http://window_loader:8083/trigger")
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://window_collector:8082/reset")
COLLECTOR_FLUSH = os.getenv("COLLECTOR_FLUSH", "http://window_collector:8082/flush")

# === APP INIT ===
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- helpers ----------
def _influx_query():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG).query_api()

def _ts_ms(dt) -> int:
    # Influx client ya devuelve timezone-aware → pasamos a epoch ms
    return int(dt.timestamp() * 1000)

# ============================================================
#  POST /api/upload_csv — guarda CSV subido
# ============================================================
@app.post("/api/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    """Guarda el CSV subido en /app/data/uploaded.csv"""
    path = os.path.join(DATA_DIR, "uploaded.csv")
    async with aiofiles.open(path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    print(f"[orchestrator] CSV recibido y guardado en {path}")
    return {"saved": True, "path": path}

# ---------- debug placeholders (opcionales) ----------
@app.get("/kafka/in")
def kafka_in():
    return {"messages": []}

@app.get("/kafka/out")
def kafka_out():
    return {"messages": []}

@app.get("/agent")
def agent_status():
    return {"logs": []}

@app.get("/debug/ls")
def debug_ls():
    files = []
    for name in os.listdir("/app/data"):
        p = os.path.join("/app/data", name)
        try:
            st = os.stat(p)
            files.append({"name": name, "size": st.st_size, "mtime": st.st_mtime})
        except Exception as e:
            files.append({"name": name, "error": str(e)})
    return {"dir": "/app/data", "files": files}

# ============================================================
#  GET /api/series — observado + predicho normalizados
# ============================================================
@app.get("/api/series")
def get_series(
    id: str | None = Query(default=None),
    hours: int = Query(default=48, ge=1, le=24*30)
):
    """
    Devuelve:
    {
      "observed":  [{ "t": <epoch_ms>, "y": <float> }, ...],
      "predicted": [{ "t": <epoch_ms>, "y_hat": <float> }, ...]
    }
    Lee measurement=telemetry con fields 'var' (observado) y 'prediction' (y_hat).
    """
    q = _influx_query()

    tag_filter = ''
    if id:
        # intentamos por 'id' y, por compatibilidad antigua, por 'unit'
        tag_filter = f'|> filter(fn: (r) => r.id == "{id}" or r.unit == "{id}")'

    flux_obs = f'''
from(bucket:"{INFLUX_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn:(r)=> r._measurement == "telemetry" and r._field == "var")
  {tag_filter}
  |> keep(columns: ["_time","_value"])
  |> sort(columns: ["_time"])
'''
    flux_pred = f'''
from(bucket:"{INFLUX_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn:(r)=> r._measurement == "telemetry" and r._field == "prediction")
  {tag_filter}
  |> keep(columns: ["_time","_value"])
  |> sort(columns: ["_time"])
'''

    observed = [{"t": _ts_ms(r.get_time()), "y": float(r.get_value())}
                for t in q.query(flux_obs) for r in t.records]
    predicted = [{"t": _ts_ms(r.get_time()), "y_hat": float(r.get_value())}
                 for t in q.query(flux_pred) for r in t.records]

    # Aseguramos orden
    observed.sort(key=lambda x: x["t"])
    predicted.sort(key=lambda x: x["t"])

    # Fallback: si no hay nada y no se pasó id, devolvemos vacío (UI debe manejarlo)
    return {"observed": observed, "predicted": predicted}

# ============================================================
#  GET /api/weights — pesos del HyperModel en el tiempo
# ============================================================
@app.get("/api/weights")
def get_weights(
    id: str = Query(..., description="flow id (tag 'id' en Influx)"),
    hours: int = Query(default=48, ge=1, le=24*30)
):
    """
    Devuelve lista plana con los pesos por modelo:
    [ { "t": <epoch_ms>, "model": "<name>", "w": <float> }, ... ]
    Requiere que el collector escriba measurement='weights' (tag id, tag model, field w).
    Si aún no se persisten pesos, devolverá [].
    """
    q = _influx_query()
    flux = f'''
from(bucket:"{INFLUX_BUCKET}")
  |> range(start: -{hours}h)
  |> filter(fn:(r)=> r._measurement == "weights" and r.id == "{id}" and r._field == "w")
  |> keep(columns: ["_time","model","_value"])
  |> sort(columns: ["_time"])
'''
    rows = [{"t": _ts_ms(r.get_time()), "model": r.values.get("model"), "w": float(r.get_value())}
            for t in q.query(flux) for r in t.records]
    rows.sort(key=lambda x: x["t"])
    return rows

# ============================================================
#  GET /api/ids — lista de series disponibles (tag id)
# ============================================================
@app.get("/api/ids")
def list_ids():
    flux = f'''
import "influxdata/influxdb/schema"
schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "id")
'''
    tabs = _influx_query().query(flux)
    ids = sorted({ r.get_value() for t in tabs for r in t.records if r.get_value() })
    return {"ids": ids}

# ============================================================
#  POST /api/run_window — limpia bucket, lanza loader y hace flush
# ============================================================
@app.post("/api/run_window")
def run_window():
    global last_flush_rows
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        delete_api = client.delete_api()
        delete_api.delete(
            start="1970-01-01T00:00:00Z",
            stop=(datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            predicate=""
        )
        print("[orchestrator] bucket limpiado antes de procesar nuevo CSV")

        r = requests.post(LOADER_URL, json={"source": "uploaded.csv"})
        r.raise_for_status()
        loader_response = r.json()

        # margen breve agent->collector->influx
        for _ in range(6):
            time.sleep(1)
            try:
                r2 = requests.get(COLLECTOR_FLUSH, timeout=3)
                if r2.ok:
                    data = r2.json()
                    last_flush_rows = data.get("rows", 0)
                if last_flush_rows:
                    break
            except Exception:
                pass

        return {
            "triggered": True,
            "status_code": 200,
            "loader_response": loader_response,
            "loader_rows": loader_response.get("rows"),
            "rows_flushed": last_flush_rows,
        }

    except Exception as e:
        print(f"[orchestrator] error en run_window: {e}")
        return {"triggered": False, "status_code": 500, "error": str(e)}

# ============================================================
#  Otros endpoints auxiliares
# ============================================================
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
    """Manual trigger: resetea collector y lanza loader"""
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
