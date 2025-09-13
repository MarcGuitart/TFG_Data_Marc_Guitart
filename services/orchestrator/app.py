from fastapi import FastAPI
import os, requests

try:
    from metrics import METRICS
except Exception:
    METRICS = None

LOADER_URL = os.getenv("LOADER_URL", "http://window_loader:8081/start")
COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://window_collector:8082/reset")

app = FastAPI(title="Orchestrator", version="0.1.0")

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
