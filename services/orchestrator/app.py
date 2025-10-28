from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
import httpx, requests, time, os, aiofiles, json
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta
from fastapi import Query


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

@app.get("/kafka/in")
def kafka_in():
    # Si quieres, podrías leer últimos N mensajes de un topic con kafka-python.
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
@app.get("/api/series")
def get_series(
    id: str | None = Query(default=None),
    hours: int = Query(default=48, ge=1, le=24*30)
):
    def _run_query(tag_filter: str):
        flux = f'''
        from(bucket:"{INFLUX_BUCKET}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r._measurement == "telemetry" and (r._field == "var" or r._field == "prediction"))
          {tag_filter}
          |> keep(columns: ["_time","_field","_value"])
          |> sort(columns: ["_time"])
        '''
        tables = q.query(flux)
        out = {"var": [], "prediction": []}
        for t in tables:
            for r in t.records:
                out[r.get_field()].append({"ts": r.get_time().isoformat(), "value": float(r.get_value())})
        return out

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    q = client.query_api()

    data = {}
    if id:
        # intenta por 'id' y, por compat, por 'unit'
        data = _run_query(f'|> filter(fn: (r) => r.id == "{id}" or r.unit == "{id}")')

    # fallback: si está vacío, trae sin filtro
    if not data or (not data["var"] and not data["prediction"]):
        data = _run_query("")  # sin filtro

    return data

@app.get("/api/ids")
def list_ids():
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "id")
    '''
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    tabs = client.query_api().query(flux)
    ids = sorted({ r.get_value() for t in tabs for r in t.records if r.get_value() })
    return {"ids": ids}

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

        # da un margen breve a agent->collector->influx (mejor que 5 fijo)
        for _ in range(6):
            time.sleep(1)
            try:
                r2 = requests.get(COLLECTOR_FLUSH, timeout=3)
                if r2.ok:
                    data = r2.json()
                    last_flush_rows = data.get("rows", 0)
                # si ya hay algo, salimos antes
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