# ==== MÉTRICAS ONLINE =========================================================
import os, math
from typing import List, Dict, Any
from decimal import Decimal
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Query, HTTPException
from influxdb_client import InfluxDBClient
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import csv
from io import StringIO
import logging

# Reutiliza las mismas ENV que el resto del servicio
INFLUX_URL    = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG    = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")

# Crea query_api aquí sin interferir con otros clientes que puedas tener
_metrics_q = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG).query_api()
app = FastAPI(title="orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


router_metrics = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Configura el logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("metrics_debug")


def _sanitize_numbers(o):
    """Recorre recursivamente dicts/listas y convierte NaN/Inf a None; convierte Decimals/numpy numbers a nativos."""
    # dict
    if isinstance(o, dict):
        return {k: _sanitize_numbers(v) for k, v in o.items()}
    # list/tuple
    if isinstance(o, (list, tuple)):
        return [_sanitize_numbers(v) for v in o]
    # Decimal
    if isinstance(o, Decimal):
        try:
            f = float(o)
        except Exception:
            return None
        return None if (math.isnan(f) or not math.isfinite(f)) else f
    # numbers (int, float, numpy types)
    if isinstance(o, (int, float)):
        try:
            f = float(o)
            if math.isnan(f) or not math.isfinite(f):
                return None
            # if it is an integer-value float, keep as int for nicer JSON
            if isinstance(o, float) and f.is_integer():
                return int(f)
            return f
        except Exception:
            return None
    # fallback: leave as-is (strings, bools, None)
    return o

def _flux_combined(id_: str, start: str) -> str:
    # kept for compatibility but not used; prefer per-field queries in Python
    return f'''
import "math"

// combined helper (deprecated)
'''

def _flux_models(id_: str, start: str) -> str:
    # kept for compatibility but not used; prefer per-field queries in Python
    return f'''
import "math"

// models helper (deprecated)
'''


def _query_models_yhat(id_: str, start: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Devuelve para un id dado todas las series yhat por modelo desde telemetry_models:
      { model_name: [ {time, value}, ... ], ... }
    """
    flux_yhat = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="telemetry_models" and r.id=="{id_}" and r._field=="yhat")
  |> keep(columns:["_time","_value","model"])'''
    logger.debug("Flux yhat all models (for series):\n%s", flux_yhat)
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux_yhat)
    except Exception as e:
        logger.exception("Influx query failed for yhat all models (series)")
        raise

    yhat_by_model: Dict[str, List[Dict[str, Any]]] = {}
    for t in tabs:
        for r in t.records:
            model = r.values.get("model")
            v = r.values.get("_value")
            if model is None or v is None:
                continue
            try:
                yhat_by_model.setdefault(model, []).append({
                    "time": r.get_time(),
                    "value": float(v),
                })
            except Exception:
                continue

    # Ordenar cada serie por tiempo
    for series in yhat_by_model.values():
        series.sort(key=lambda x: x["time"])
    return yhat_by_model


def _query_chosen_model(id_: str, start: str) -> List[Dict[str, Any]]:
    """
    Devuelve la serie de modelos elegidos (AP2 - modo adaptativo):
      [ {time: datetime, model: str}, ... ]
    """
    flux_chosen = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="chosen_model" and r.id=="{id_}" and r._field=="model")
  |> keep(columns:["_time","_value"])'''
    logger.debug("Flux chosen model:\n%s", flux_chosen)
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux_chosen)
    except Exception as e:
        logger.exception("Influx query failed for chosen_model")
        raise

    chosen = []
    for t in tabs:
        for r in t.records:
            v = r.values.get("_value")
            if v is None:
                continue
            try:
                chosen.append({
                    "time": r.get_time(),
                    "model": str(v),
                })
            except Exception:
                continue

    # Ordenar por tiempo
    chosen.sort(key=lambda x: x["time"])
    return chosen


def _query_weights(id_: str, start: str = "-7d"):
    """
    AP3: Consulta la evolución de pesos por modelo desde InfluxDB.
    Measurement: weights
    Tags: id, model
    Field: weight (float)
    
    Returns:
      {
        "model_name": [ {time: datetime, weight: float}, ... ],
        ...
      }
    """
    flux_weights = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="weights" and r.id=="{id_}" and r._field=="weight")
  |> keep(columns:["_time","_value","model"])'''
    logger.debug("Flux weights:\n%s", flux_weights)
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux_weights)
    except Exception as e:
        logger.exception("Influx query failed for weights")
        raise

    weights_by_model = {}
    for t in tabs:
        for r in t.records:
            model_name = r.values.get("model")
            weight_val = r.values.get("_value")
            if model_name is None or weight_val is None:
                continue
            try:
                if model_name not in weights_by_model:
                    weights_by_model[model_name] = []
                weights_by_model[model_name].append({
                    "time": r.get_time(),
                    "weight": float(weight_val),
                })
            except Exception:
                continue

    # Ordenar cada serie por tiempo
    for model_name in weights_by_model:
        weights_by_model[model_name].sort(key=lambda x: x["time"])
    
    return weights_by_model


@app.get("/api/series")
def get_series(
    id: str = Query(..., description="series id"),
    hours: int = Query(24, ge=1, le=24*365)
):
    """
    Devuelve la serie observada (var), la predicha híbrida (prediction),
    las predicciones por modelo, y el modelo elegido en cada instante (AP2).
    """
    start = f"-{hours}h"

    try:
        var_series = _query_field("telemetry", id, "var", start)
        pred_series = _query_field("telemetry", id, "prediction", start)
        yhat_by_model = _query_models_yhat(id, start)
        chosen_series = _query_chosen_model(id, start)  # AP2: modelo elegido
        weights_by_model = _query_weights(id, start)    # AP3: pesos por modelo
        logger.info(f"[/api/series] id={id} var_series={len(var_series)} pred_series={len(pred_series)} yhat_by_model keys={list(yhat_by_model.keys())} chosen={len(chosen_series)} weights={list(weights_by_model.keys())}")
    except Exception as e:
        logger.exception("Failed to query series for /api/series")
        raise HTTPException(status_code=502, detail=f"influx query failed: {e}")

    # 1) Alineamos var y prediction híbrida como antes
    aligned_main = _align_by_time(var_series, pred_series, tol_seconds=120)

    # 2) Alineamos var con cada modelo por separado
    aligned_models: Dict[str, List[Dict[str, Any]]] = {}
    for model, series in yhat_by_model.items():
        aligned_models[model] = _align_by_time(var_series, series, tol_seconds=120)

    # 3) Construimos índices por timestamp para poder fusionar todo
    from collections import defaultdict
    import datetime

    # map tiempo -> {a: var, combined: pred_hibrida, models: {name: yhat}}
    bucket: Dict[datetime.datetime, Dict[str, Any]] = {}

    def _ensure_bucket(t):
        if t not in bucket:
            bucket[t] = {"models": {}}
        return bucket[t]

    # var + prediction híbrida
    for p in aligned_main:
        t = p["time"]
        b = _ensure_bucket(t)
        b["a"] = p["a"]        # var
        b["combined"] = p["b"] # prediction híbrida

    # por modelo
    for model, aligned in aligned_models.items():
        for p in aligned:
            t = p["time"]
            b = _ensure_bucket(t)
            # a debería ser el mismo valor real, si no existe aún lo ponemos
            if "a" not in b:
                b["a"] = p["a"]
            b["models"][model] = p["b"]

    # 4) Ordenamos por tiempo y construimos payloads
    times_sorted = sorted(bucket.keys())

    observed = []
    predicted = []
    models_payload: Dict[str, List[Dict[str, Any]]] = {m: [] for m in yhat_by_model.keys()}
    points = []
    chosen_models = []  # AP2: lista de modelos elegidos por timestamp

    # Crear índice de modelo elegido por tiempo
    chosen_by_time = {c["time"]: c["model"] for c in chosen_series}

    for t in times_sorted:
        b = bucket[t]
        ts_iso = t.isoformat()
        a_val = b.get("a")
        c_val = b.get("combined")
        chosen = chosen_by_time.get(t)  # Modelo elegido en este timestamp

        # lista clásica como ya tenías
        if a_val is not None:
            observed.append({"t": ts_iso, "y": a_val})
        if c_val is not None:
            predicted.append({"t": ts_iso, "y_hat": c_val})

        # por modelo
        for model, yhat in b["models"].items():
            models_payload.setdefault(model, []).append({
                "t": ts_iso,
                "y_hat": yhat
            })

        # AP2: modelo elegido
        if chosen:
            chosen_models.append({"t": ts_iso, "model": chosen})

        # punto plano para CsvChart
        point = {
            "t": int(t.timestamp() * 1000),  # epoch ms
            "var": a_val,
            "prediction": c_val,
            "chosen_model": chosen,  # AP2: agregar modelo elegido
        }
        for model, yhat in b["models"].items():
            point[model] = yhat
        points.append(point)

    payload = {
        "id": id,
        "observed": observed,
        "predicted": predicted,       # híbrida
        "models": models_payload,     # por modelo
        "chosen_models": chosen_models,  # AP2: modelo elegido por timestamp
        "weights": weights_by_model,  # AP3: pesos por modelo
        "points": points,             # listo para CsvChart
    }
    return JSONResponse(content=_sanitize_numbers(payload))




def _query_field(measurement: str, id_: str, field: str, start: str) -> List[Dict[str, Any]]:
    """Query Influx for a single measurement/field and return list of {time: datetime, value: float} records."""
    flux = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="{measurement}" and r.id=="{id_}" and r._field=="{field}")
  |> keep(columns:["_time","_value","_field","_measurement"])'''
    logger.debug("Running flux for field: %s", flux)
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux)
    except Exception as e:
        logger.exception("Influx query failed for field %s.%s", measurement, field)
        raise
    out = []
    for t in tabs:
        for r in t.records:
            v = r.values.get("_value")
            if v is None:
                continue
            try:
                out.append({"time": r.get_time(), "value": float(v)})
            except Exception:
                continue
    # sort by time
    out.sort(key=lambda x: x["time"])
    return out

from datetime import timedelta

def _align_by_time(a: List[Dict[str, Any]], b: List[Dict[str, Any]], tol_seconds: int = 120) -> List[Dict[str, Any]]:
    """
    Empareja puntos si sus timestamps están a menos de tol_seconds de diferencia.
    a: serie observada (var)
    b: serie predicha (prediction)
    """
    ia = 0
    ib = 0
    res: List[Dict[str, Any]] = []
    tol = timedelta(seconds=tol_seconds)

    # Asumimos que ya vienen ordenados por tiempo (y en _query_field los ordenas)
    while ia < len(a) and ib < len(b):
        ta = a[ia]["time"]
        tb = b[ib]["time"]
        dt = tb - ta

        if abs(dt) <= tol:
            # Match
            res.append({
                "time": tb,         # timestamp de la predicción
                "a": a[ia]["value"], # var
                "b": b[ib]["value"]  # prediction
            })
            ia += 1
            ib += 1
        elif ta < tb:
            ia += 1
        else:
            ib += 1

    return res



@router_metrics.get("/combined")
def metrics_combined(id: str = Query(..., description="series id"), start: str = Query("-7d")) -> Dict[str, Any]:
    # Query var and prediction series separately
    try:
        var_series = _query_field("telemetry", id, "var", start)
        pred_series = _query_field("telemetry", id, "prediction", start)
    except Exception as e:
        logger.exception("Failed to query var/prediction series")
        raise HTTPException(status_code=502, detail=f"influx query failed: {e}")
    
    logger.debug("metrics_combined: len(var_series)=%d len(pred_series)=%d", len(var_series), len(pred_series))
    if var_series:
        logger.debug("metrics_combined: first var ts=%s", var_series[0]["time"].isoformat())
    if pred_series:
        logger.debug("metrics_combined: first pred ts=%s", pred_series[0]["time"].isoformat())


    aligned = _align_by_time(var_series, pred_series)

    # daily aggregation: group by date (UTC)
    from collections import defaultdict
    daily_map = defaultdict(list)
    abs_list = []
    sq_list = []
    ape_list = []
    for p in aligned:
        t = p["time"]
        date = t.date().isoformat()
        err = p["b"] - p["a"]
        abs_v = abs(err)
        sq_v = err * err
        ape_v = (abs(err / p["a"]) if p["a"] != 0 else 0.0)
        daily_map[date].append((abs_v, sq_v, ape_v))
        abs_list.append(abs_v)
        sq_list.append(sq_v)
        ape_list.append(ape_v)

    daily = []
    for d, vals in sorted(daily_map.items()):
        ma = sum(v[0] for v in vals) / len(vals)
        rs = math.sqrt(sum(v[1] for v in vals) / len(vals))
        mp = sum(v[2] for v in vals) / len(vals)
        daily.append({"time": d, "mae": ma, "rmse": rs, "mape": mp})

    overall = {
        "mae": (sum(abs_list)/len(abs_list)) if abs_list else None,
        "rmse": (math.sqrt(sum(sq_list)/len(sq_list)) if sq_list else None),
        "mape": (sum(ape_list)/len(ape_list)) if ape_list else None,
        "n": len(abs_list)
    }

    sanitized = _sanitize_numbers({"id": id, "daily": daily, "overall": overall})
    return JSONResponse(content=sanitized)

@router_metrics.get("/models")
def metrics_models(id: str = Query(..., description="series id"), start: str = Query("-7d")) -> Dict[str, Any]:
    # For models we need per-model yhat vs var. Query var once and yhat by model.
    try:
        var_series = _query_field("telemetry", id, "var", start)
    except Exception as e:
        logger.exception("Failed to query var series for models")
        raise HTTPException(status_code=502, detail=f"influx query failed: {e}")

    # Query all yhat points for this id
    flux_yhat = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="telemetry_models" and r.id=="{id}" and r._field=="yhat")
  |> keep(columns:["_time","_value","model"])'''
    logger.debug("Flux yhat all models:\n%s", flux_yhat)
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux_yhat)
    except Exception as e:
        logger.exception("Influx query failed for yhat all models")
        raise HTTPException(status_code=502, detail=f"influx query failed: {e}")

    # Organize yhat by model
    yhat_by_model: Dict[str, List[Dict[str, Any]]] = {}
    for t in tabs:
        for r in t.records:
            model = r.values.get("model")
            v = r.values.get("_value")
            if model is None or v is None:
                continue
            try:
                yhat_by_model.setdefault(model, []).append({"time": r.get_time(), "value": float(v)})
            except Exception:
                continue

    # Now compute per-model aligned metrics
    result_daily: Dict[str, List[Dict[str, Any]]] = {}
    result_overall: Dict[str, Dict[str, Any]] = {}
    
    # AP4: Query weights for each model
    try:
        weights_by_model = _query_weights(id, start)
    except Exception as e:
        logger.exception("Failed to query weights for AP4")
        weights_by_model = {}
    
    for model, series in yhat_by_model.items():
        series.sort(key=lambda x: x["time"])
        aligned = _align_by_time(var_series, series)
        abs_list = []
        sq_list = []
        ape_list = []
        daily_map = {}
        for p in aligned:
            t = p["time"]
            date = t.date().isoformat()
            err = p["b"] - p["a"]
            abs_v = abs(err)
            sq_v = err * err
            ape_v = (abs(err / p["a"]) if p["a"] != 0 else 0.0)
            daily_map.setdefault(date, []).append((abs_v, sq_v, ape_v))
            abs_list.append(abs_v)
            sq_list.append(sq_v)
            ape_list.append(ape_v)
        # daily list
        daily_list = []
        for d, vals in sorted(daily_map.items()):
            ma = sum(v[0] for v in vals) / len(vals)
            rs = math.sqrt(sum(v[1] for v in vals) / len(vals))
            mp = sum(v[2] for v in vals) / len(vals)
            daily_list.append({"time": d, "mae": ma, "rmse": rs, "mape": mp})

        # Get latest weight for this model
        current_weight = None
        if model in weights_by_model and weights_by_model[model]:
            current_weight = weights_by_model[model][-1]["weight"]
        
        result_daily[model] = daily_list
        result_overall[model] = {
            "mae": (sum(abs_list)/len(abs_list)) if abs_list else None,
            "rmse": (math.sqrt(sum(sq_list)/len(sq_list)) if sq_list else None),
            "mape": (sum(ape_list)/len(ape_list)) if ape_list else None,
            "weight": current_weight,
            "n": len(abs_list)
        }

    sanitized = _sanitize_numbers({"id": id, "daily": result_daily, "overall": result_overall})
    return JSONResponse(content=sanitized)

# Asegura registrar el router en tu app FastAPI existente
try:
    app.include_router(router_metrics)
except NameError:
    # Si por estructura tu app se llama distinto, expón el router y lo incluyes donde instancies FastAPI
    METRICS_ROUTER = router_metrics


import httpx
from fastapi import HTTPException

LOADER_URL      = os.getenv("LOADER_URL", "http://window_loader:8083/trigger")
COLLECTOR_RESET = os.getenv("COLLECTOR_URL", "http://window_collector:8082/reset")

@app.post("/api/run_window")
def run_window():
    """
    Demo mínima:
      1) reset collector
      2) dispara loader con un CSV fijo en /app/data
    """
    # 1) reset collector
    try:
        r_reset = httpx.post(COLLECTOR_RESET, timeout=30.0)
        r_reset.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"collector reset failed: {e}")

    # 2) dispara loader con CSV de pruebas
    # Ajusta el nombre al que tengas en ../data dentro del repo
    payload = {
        "source": "uploaded.csv",  
        "speed_ms": 0
    }
    try:
        r_trig = httpx.post(LOADER_URL, json=payload, timeout=120.0)
        r_trig.raise_for_status()
        data = r_trig.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"loader trigger failed: {e}")

    return {"loader_response": data}


# Uploads
UPLOAD_DIR = "/app/data"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/api/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    dest_path = os.path.join(UPLOAD_DIR, "uploaded.csv")  # <-- nombre fijo
    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    # contar filas de forma barata
    try:
        text = contents.decode("utf-8", errors="ignore").splitlines()
        reader = csv.DictReader(text)
        rows = sum(1 for _ in reader)
    except Exception:
        rows = None

    return {
        "filename": "uploaded.csv",
        "path": dest_path,
        "rows": rows,
    }
