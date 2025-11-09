from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import PlainTextResponse
import httpx, requests, time, os, aiofiles, json
from influxdb_client import InfluxDBClient
from datetime import datetime, timedelta

try:
    from metrics import METRICS
except Exception:
    METRICS = None

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")

LOADER_URL = os.getenv("LOADER_URL", "http://window_loader:8083/trigger")
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://window_collector:8082/reset")
COLLECTOR_FLUSH = os.getenv("COLLECTOR_FLUSH", "http://window_collector:8082/flush")


app = FastAPI(title="Orchestrator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

def _influx_query():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG).query_api()

def _ts_ms(dt) -> int:
    return int(dt.timestamp() * 1000)

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


# ============================================================
#  POST /api/upload_csv — guarda CSV subido
# ============================================================
@app.post("/api/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    path = os.path.join(DATA_DIR, "uploaded.csv")
    async with aiofiles.open(path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)
    return {"saved": True, "path": path}

# ============================================================
#  POST /api/run_window — limpia bucket, lanza loader y espera datos
# ============================================================
@app.post("/api/run_window")
def run_window():
    last_flush_rows = 0
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
        r = requests.post(LOADER_URL, json={"source": "uploaded.csv"})
        r.raise_for_status()
        loader_response = r.json()

        # Espera activa hasta que haya puntos reales (observed/prediction) del primer ID
        ids = loader_response.get("unique_ids") or []
        id0 = ids[0] if ids else None
        q = _influx_query()
        for _ in range(40):  # ~20s
            time.sleep(0.5)
            try:
                rf = requests.get(COLLECTOR_FLUSH, timeout=3)
                if rf.ok:
                    last_flush_rows = rf.json().get("rows", 0)
            except Exception:
                pass
            if id0:
                flux_check = f'''
from(bucket:"{INFLUX_BUCKET}")
  |> range(start: -24h)
  |> filter(fn:(r)=> r._measurement=="telemetry" and r.id=="{id0}" and (r._field=="var" or r._field=="prediction"))
  |> limit(n:1)
'''
                tabs = q.query(flux_check)
                if any(True for t in tabs for _r in t.records):
                    break

        return {
            "triggered": True,
            "status_code": 200,
            "loader_response": loader_response,
            "loader_rows": loader_response.get("rows"),
            "rows_flushed": last_flush_rows,
        }
    except Exception as e:
        return {"triggered": False, "status_code": 500, "error": str(e)}

# ============================================================
#  GET /api/ids — lista de series (tag id)
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
#  GET /api/series — observado + predicho normalizados
# ============================================================
@app.get("/api/series")
def get_series(id: str | None = Query(default=None), hours: int = Query(default=48, ge=1, le=720)):
    q = _influx_query()
    tag_filter = f'|> filter(fn: (r) => r.id == "{id}" or r.unit == "{id}")' if id else ''
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
    obs = [{"t": _ts_ms(r.get_time()), "y": float(r.get_value())}
           for t in q.query(flux_obs) for r in t.records]
    pred = [{"t": _ts_ms(r.get_time()), "y_hat": float(r.get_value())}
            for t in q.query(flux_pred) for r in t.records]
    obs.sort(key=lambda x: x["t"]); pred.sort(key=lambda x: x["t"])
    return {"observed": obs, "predicted": pred}

# ============================================================
#  GET /api/weights — pesos del HyperModel
# ============================================================
@app.get("/api/weights")
def get_weights(id: str = Query(...), hours: int = Query(default=48, ge=1, le=720)):
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