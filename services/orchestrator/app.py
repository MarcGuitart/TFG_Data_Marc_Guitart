# ==== MÉTRICAS ONLINE =========================================================
import os, math
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter, Query, HTTPException, Body
from influxdb_client import InfluxDBClient
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import csv
from io import StringIO
import logging

# Import ScenarioManager
from scenarios import ScenarioManager

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

# Global state: store the last forecast horizon selected
_last_forecast_horizon = {}  # {"forecast_horizon": 1, "timestamp": datetime}


def _sanitize_numbers(o):
    """Recorre recursivamente dicts/listas y convierte NaN/Inf a None; convierte Decimals/numpy numbers a nativos."""
    import datetime
    
    # dict
    if isinstance(o, dict):
        return {k: _sanitize_numbers(v) for k, v in o.items()}
    # list/tuple
    if isinstance(o, (list, tuple)):
        return [_sanitize_numbers(v) for v in o]
    # datetime -> ISO string
    if isinstance(o, (datetime.datetime, datetime.date)):
        return o.isoformat()
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
    Field: w (float) - nota: el collector escribe "w", no "weight"
    
    Returns:
      {
        "model_name": [ {time: datetime, weight: float}, ... ],
        ...
      }
    """
    flux_weights = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="weights" and r.id=="{id_}" and r._field=="w")
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
                    "time": r.get_time().isoformat(),  # ✅ Convertir datetime a ISO string
                    "weight": float(weight_val),
                })
            except Exception:
                continue

    # Ordenar cada serie por tiempo
    for model_name in weights_by_model:
        weights_by_model[model_name].sort(key=lambda x: x["time"])
    
    return weights_by_model


def _query_chosen_errors(id_: str, start: str) -> List[Dict[str, Any]]:
    """
    AP2: Consulta los errores del modelo elegido desde InfluxDB.
    Measurement: chosen_error
    Tags: id
    Fields: error_abs, error_rel
    
    Returns:
      [ {time: datetime, error_abs: float, error_rel: float}, ... ]
    """
    flux_errors = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="chosen_error" and r.id=="{id_}")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns:["_time","error_abs","error_rel"])'''
    logger.debug("Flux chosen_errors:\n%s", flux_errors)
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux_errors)
    except Exception as e:
        logger.exception("Influx query failed for chosen_error")
        return []

    errors = []
    for t in tabs:
        for r in t.records:
            try:
                errors.append({
                    "time": r.get_time(),
                    "error_abs": float(r.values.get("error_abs", 0)) if r.values.get("error_abs") is not None else None,
                    "error_rel": float(r.values.get("error_rel", 0)) if r.values.get("error_rel") is not None else None,
                })
            except Exception:
                continue

    errors.sort(key=lambda x: x["time"])
    return errors


@app.get("/api/selector")
def get_selector_table(
    id: str = Query(..., description="series id"),
    hours: int = Query(24, ge=1, le=24*365)
):
    """
    AP2: Devuelve la tabla del selector adaptativo con:
    - Timestamp
    - Modelo elegido
    - Error relativo puntual (%)
    - Error absoluto puntual
    - Valor real y predicho
    """
    start = f"-{hours}h"
    
    try:
        var_series = _query_field("telemetry", id, "var", start)
        pred_series = _query_field("telemetry", id, "prediction", start)
        chosen_series = _query_chosen_model(id, start)
        chosen_errors = _query_chosen_errors(id, start)
    except Exception as e:
        logger.exception("Failed to query selector data")
        return JSONResponse(content={"id": id, "selector_table": [], "error": str(e)})
    
    if not chosen_series:
        return JSONResponse(content={"id": id, "selector_table": []})
    
    # Alinear var y prediction
    aligned_main = _align_by_time(var_series, pred_series, tol_seconds=120)
    
    # Crear índices
    chosen_by_time = {c["time"]: c["model"] for c in chosen_series}
    errors_by_time = {}
    for e in chosen_errors:
        errors_by_time[e["time"]] = {
            "error_abs": e.get("error_abs"),
            "error_rel": e.get("error_rel")
        }
    
    # Construir tabla
    selector_table = []
    for p in aligned_main:
        t = p["time"]
        chosen = chosen_by_time.get(t)
        if not chosen:
            continue
        
        err_info = errors_by_time.get(t, {})
        
        selector_table.append({
            "t": t.isoformat(),
            "t_ms": int(t.timestamp() * 1000),
            "chosen_model": chosen,
            "error_rel": err_info.get("error_rel"),
            "error_abs": err_info.get("error_abs"),
            "y_real": p["a"],
            "y_pred": p["b"],
        })
    
    return JSONResponse(content=_sanitize_numbers({
        "id": id,
        "selector_table": selector_table,
        "total_rows": len(selector_table)
    }))


@app.get("/api/series")
def get_series(
    id: str = Query(..., description="series id"),
    hours: int = Query(24, ge=1, le=24*365)
):
    """
    Returns the observed series (var), the hybrid prediction (prediction),
    the predictions per model, the chosen model, and errors at each instant.
    
    Now includes temporal semantics:
    - t_decision: moment when prediction was made (t)
    - horizon: number of slots ahead being predicted (m)
    """
    start = f"-{hours}h"
    
    # Get the horizon from the last execution (default to 1)
    global _last_forecast_horizon
    current_horizon = _last_forecast_horizon.get("forecast_horizon", 1)

    try:
        var_series = _query_field("telemetry", id, "var", start)
        pred_series = _query_field("telemetry", id, "prediction", start)
        yhat_by_model = _query_models_yhat(id, start)
        chosen_series = _query_chosen_model(id, start)  
        weights_by_model = _query_weights(id, start)    
        chosen_errors = _query_chosen_errors(id, start) 
        logger.info(f"[/api/series] id={id} var_series={len(var_series)} pred_series={len(pred_series)} yhat_by_model keys={list(yhat_by_model.keys())} chosen={len(chosen_series)} errors={len(chosen_errors)} weights={list(weights_by_model.keys())}")
    except Exception as e:
        logger.exception("Failed to query series for /api/series")
        return JSONResponse(content={
            "id": id,
            "observed": [],
            "predicted": [],
            "models": {},
            "chosen_models": [],
            "selector_table": [],
            "weights": {},
            "points": [],
            "error": str(e)
        })

    # Handle empty data gracefully
    if not var_series and not pred_series and not yhat_by_model:
        return JSONResponse(content={
            "id": id,
            "observed": [],
            "predicted": [],
            "models": {},
            "chosen_models": [],
            "selector_table": [],
            "weights": {},
            "points": [],
            "error": "No data found for this ID"
        })

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
    selector_table = []  # AP2: tabla del selector adaptativo

    # Crear índice de modelo elegido por tiempo
    chosen_by_time = {c["time"]: c["model"] for c in chosen_series}
    
    # AP2: Crear índice de errores por tiempo
    errors_by_time = {}
    for e in chosen_errors:
        errors_by_time[e["time"]] = {
            "error_abs": e.get("error_abs"),
            "error_rel": e.get("error_rel")
        }

    for t in times_sorted:
        b = bucket[t]
        ts_iso = t.isoformat()
        a_val = b.get("a")
        c_val = b.get("combined")
        chosen = chosen_by_time.get(t)  # Modelo elegido en este timestamp
        err_info = errors_by_time.get(t, {})  # AP2: errores de este timestamp

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

        # AP2: modelo elegido con error
        if chosen:
            chosen_models.append({"t": ts_iso, "model": chosen})
            # Tabla del selector adaptativo
            selector_table.append({
                "t": ts_iso,
                "t_ms": int(t.timestamp() * 1000),
                "chosen_model": chosen,
                "error_abs": err_info.get("error_abs"),
                "error_rel": err_info.get("error_rel"),
                "y_real": a_val,
                "y_pred": c_val,
            })

        # punto plano para CsvChart y LivePredictionChart
        # AP1 FIX: y_adaptive DEBE ser exactamente el valor del modelo elegido, no la predicción híbrida
        y_adaptive = b["models"].get(chosen) if chosen and chosen in b["models"] else c_val
        
        # Calcular error del ensemble (prediction final ponderada)
        ensemble_error_abs = None
        ensemble_error_rel = None
        ensemble_error_rel_mean = None  # MAPE para este punto
        if a_val is not None and c_val is not None:
            ensemble_error_abs = abs(c_val - a_val)
            ensemble_error_rel = (ensemble_error_abs / abs(a_val)) * 100 if a_val != 0 else 0
            ensemble_error_rel_mean = ensemble_error_rel  # Para este punto, es lo mismo
        
        point = {
            "t": int(t.timestamp() * 1000),  # epoch ms
            "timestamp": t.isoformat(),      # ISO timestamp para LivePredictionChart
            "t_decision": t.isoformat(),     # Momento de decisión (t) - para visualización
            "horizon": current_horizon,      # Horizonte de predicción (m slots)
            "var": a_val,                    # valor observado
            "yhat": y_adaptive,              # AP1: EXACTAMENTE el modelo elegido
            "prediction": c_val,             # predicción híbrida (legacy)
            "y_adaptive": y_adaptive,        # AP1: campo explícito para verificación
            "chosen_model": chosen,          # AP2: modelo elegido
            "chosen_error_abs": err_info.get("error_abs"),  # AP2: error absoluto del chosen
            "chosen_error_rel": err_info.get("error_rel"),  # AP2: error relativo del chosen
            "error_abs": ensemble_error_abs,  # Error absoluto del ENSEMBLE
            "error_rel": ensemble_error_rel,  # Error relativo del ENSEMBLE
            "error_rel_mean": ensemble_error_rel_mean,  # MAPE del ENSEMBLE (para ConfidenceEvolutionChart)
            "hyper_models": {                # Modelos individuales (5 modelos activos)
                "kalman": b["models"].get("kalman"),
                "linear": b["models"].get("linear"),
                "poly": b["models"].get("poly"),
                "alphabeta": b["models"].get("alphabeta"),
                "naive": b["models"].get("naive"),
            }
        }
        for model, yhat in b["models"].items():
            point[model] = yhat
        points.append(point)

    payload = {
        "id": id,
        "horizon": current_horizon,       # Horizonte de predicción (m slots)
        "observed": observed,
        "predicted": predicted,       # híbrida
        "models": models_payload,     # por modelo
        "chosen_models": chosen_models,  # AP2: modelo elegido por timestamp
        "selector_table": selector_table,  # AP2: tabla completa del selector
        "weights": weights_by_model,  # AP3: pesos por modelo
        "points": points,             # listo para CsvChart
        "data": points,               # TAMBIÉN como "data" para LivePredictionChart.jsx
        "total": len(points),         # Para que el componente pueda calcular progreso
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


# ============================================================================
# MULTI-HORIZON FORECAST ENDPOINT
# ============================================================================
@app.get("/api/forecast_multi_horizon")
def get_multi_horizon_forecast(
    id: str = Query(..., description="series id"),
    hours: int = Query(24, ge=1, le=24*365, description="lookback window")
):
    """
    Get the multi-horizon forecast for the LAST EXECUTED PIPELINE.
    
    This endpoint returns forecasts ONLY for the horizon that was selected
    when the pipeline was executed (stored in _last_forecast_horizon).
    
    If no pipeline has been executed, or forecast_horizon wasn't set,
    defaults to showing T+1.
    
    Returns:
        JSON with:
        - selected_horizon: the T+M that was executed
        - predictions: array of {time_t, time_t_plus_h, ground_truth_t, ground_truth_t_plus_h, prediction_t, confidence, error_rel, error_abs}
        - avg_confidence: average confidence for this horizon
        - avg_error_rel: average relative error
        - total_points: number of prediction points
    """
    global _last_forecast_horizon
    
    # Get the horizon from the last execution, default to 1
    selected_horizon = _last_forecast_horizon.get("forecast_horizon", 1)
    last_execution_time = _last_forecast_horizon.get("timestamp")
    
    logger.info(f"[MULTI_HORIZON] === Starting forecast for id={id}, horizon=T+{selected_horizon}, hours={hours} ===")
    logger.info(f"[MULTI_HORIZON] Last execution: {last_execution_time}")
    
    try:
        # 1) Get series data from the /api/series endpoint
        logger.info(f"[MULTI_HORIZON] Step 1: Querying series data...")
        
        # Call the series endpoint directly
        import httpx
        try:
            async_client = httpx.Client(timeout=30.0)
            res = async_client.get(f"http://localhost:8081/api/series?id={id}&hours={hours}")
            res.raise_for_status()
            series_data = res.json()
            async_client.close()
        except Exception as e:
            logger.error(f"[MULTI_HORIZON] Could not fetch series data: {e}")
            return JSONResponse(content={
                "id": id,
                "selected_horizon": selected_horizon,
                "predictions": [],
                "error": f"Could not fetch series data: {str(e)}"
            })
        
        # Extract points: each point has {"timestamp", "var" (ground truth), "prediction" or "y_adaptive"}
        points = series_data.get("points", [])
        if not points:
            logger.warning(f"[MULTI_HORIZON] No points found for series {id}")
            return JSONResponse(content={
                "id": id,
                "selected_horizon": selected_horizon,
                "predictions": [],
                "error": "No data points available for this series"
            })
        
        logger.info(f"[MULTI_HORIZON] Step 1 complete: {len(points)} points fetched")
        
        # 2) Calculate forecast ONLY for the selected horizon
        logger.info(f"[MULTI_HORIZON] Step 2: Calculating forecast for horizon T+{selected_horizon}...")
        
        # SLOT_MINUTES defines the timestep (typically 30 minutes)
        SLOT_MINUTES = 30
        
        h = selected_horizon
        predictions = []
        confidence_scores = []
        errors_rel = []
        
        # For each point, calculate what error would have been at horizon h
        for i in range(len(points) - h):  # Only consider points where we have ground truth at T+h
            current_point = points[i]
            target_point = points[i + h]
            
            # Current values
            time_current = current_point.get("timestamp")
            var_current = current_point.get("var")  # Ground truth at T
            pred_current = current_point.get("prediction") or current_point.get("y_adaptive")  # Ensemble prediction at T
            
            # Target values (at T+h)
            time_target = target_point.get("timestamp")
            var_target = target_point.get("var")  # Ground truth at T+h
            pred_target = pred_current  # We use the prediction made at T for T+h (as proxy)
            logger.info(f"[MULTI_HORIZON] === Processing horizon T+{h} ===")
            
            horizon_predictions = []
            confidence_scores = []
            errors_rel = []
            
            # For each point, calculate what error would have been at horizon h
            for i in range(len(points) - h):  # Only consider points where we have ground truth at T+h
                current_point = points[i]
                target_point = points[i + h]
                
                # Current values
                time_current = current_point.get("timestamp")
                var_current = current_point.get("var")  # Ground truth at T
                pred_current = current_point.get("prediction") or current_point.get("y_adaptive")  # Ensemble prediction at T
                
                # Target values (at T+h)
                time_target = target_point.get("timestamp")
                var_target = target_point.get("var")  # Ground truth at T+h
                pred_target = pred_current  # We use the prediction made at T for T+h (as proxy)
                
                if var_target is None or pred_target is None:
                    continue
            
            if var_target is None or pred_target is None:
                continue
            
            # Calculate error metrics
            error_abs = abs(pred_target - var_target)
            error_rel = 0
            confidence = 100
            
            if var_target != 0:
                error_rel = (error_abs / abs(var_target)) * 100
                confidence = max(0, min(100, 100 - error_rel))  # Bounded 0-100
            
            errors_rel.append(error_rel)
            confidence_scores.append(confidence)
            
            # Record prediction
            predictions.append({
                "index": i,
                "time_t": time_current,
                "time_t_plus_h": time_target,
                "ground_truth_t": var_current,
                "ground_truth_t_plus_h": var_target,
                "prediction_t": pred_current,
                "error_abs": error_abs,
                "error_rel": error_rel,
                "confidence": confidence
            })
            
            # Log first 3 points for verification
            if i < 3:
                var_str = f"{var_current:.4f}" if var_current is not None else "None"
                pred_str = f"{pred_current:.4f}" if pred_current is not None else "None"
                logger.info(f"[MULTI_HORIZON_VERIFY] H=T+{h}, Point index={i}:")
                logger.info(f"  T: {time_current}, var={var_str}, pred={pred_str}")
                logger.info(f"  T+{h}: {time_target}, var={var_target:.4f}")
                logger.info(f"  Error: abs={error_abs:.4f}, rel={error_rel:.2f}%, conf={confidence:.2f}%")
        
        # Calculate horizon statistics
        avg_confidence = None
        avg_error_rel = None
        
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        if errors_rel:
            avg_error_rel = sum(errors_rel) / len(errors_rel)
        
        conf_str = f"{avg_confidence:.2f}" if avg_confidence is not None else "N/A"
        err_str = f"{avg_error_rel:.2f}" if avg_error_rel is not None else "N/A"
        logger.info(f"[MULTI_HORIZON] Horizon T+{h} complete: {len(predictions)} points, "
                   f"avg_confidence={conf_str}%, avg_error={err_str}%")
        
        logger.info(f"[MULTI_HORIZON] === Forecast complete for horizon T+{selected_horizon} ===")
        
        return JSONResponse(content=_sanitize_numbers({
            "id": id,
            "selected_horizon": selected_horizon,
            "predictions": predictions,
            "avg_confidence": avg_confidence,
            "avg_error_rel": avg_error_rel,
            "total_points": len(predictions),
            "lookback_hours": hours,
            "slot_minutes": SLOT_MINUTES
        }))
        
    except Exception as e:
        logger.exception(f"[MULTI_HORIZON] ERROR calculating forecast for horizon T+{selected_horizon}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "id": id, "selected_horizon": selected_horizon}
        )



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


@app.get("/api/metrics/models/ranked")
def metrics_models_ranked(id: str = Query(..., description="series id"), start: str = Query("-7d")):
    """
    AP4: Devuelve métricas por modelo ORDENADAS POR PESO (para Top-3).
    Combina información de errores con pesos para mostrar ranking claro.
    """
    try:
        var_series = _query_field("telemetry", id, "var", start)
        weights_by_model = _query_weights(id, start)
    except Exception as e:
        logger.exception("Failed to query for metrics_models_ranked")
        raise HTTPException(status_code=502, detail=f"influx query failed: {e}")

    # Query all yhat points for this id
    flux_yhat = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:{start})
  |> filter(fn:(r)=> r._measurement=="telemetry_models" and r.id=="{id}" and r._field=="yhat")
  |> keep(columns:["_time","_value","model"])'''
    
    try:
        tabs = _metrics_q.query(org=INFLUX_ORG, query=flux_yhat)
    except Exception as e:
        logger.exception("Influx query failed for yhat all models in ranked metrics")
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

    # Calcular métricas por modelo
    result_overall: Dict[str, Dict[str, Any]] = {}
    
    for model, series in yhat_by_model.items():
        series.sort(key=lambda x: x["time"])
        aligned = _align_by_time(var_series, series)
        abs_list = []
        sq_list = []
        ape_list = []
        rel_list = []
        
        for p in aligned:
            err = p["b"] - p["a"]
            abs_v = abs(err)
            sq_v = err * err
            
            # Error relativo (%)
            if p["a"] != 0:
                rel_v = (err / p["a"]) * 100.0
            else:
                rel_v = 0.0 if abs(err) < 1e-9 else float('inf')
            
            ape_v = (abs(err / p["a"]) if p["a"] != 0 else 0.0)
            
            abs_list.append(abs_v)
            sq_list.append(sq_v)
            ape_list.append(ape_v)
            rel_list.append(rel_v)
        
        # Get latest weight for this model
        current_weight = None
        weight_mean = None
        if model in weights_by_model and weights_by_model[model]:
            current_weight = weights_by_model[model][-1]["weight"]
            weight_mean = sum(w["weight"] for w in weights_by_model[model]) / len(weights_by_model[model])
        
        mae = sum(abs_list) / len(abs_list) if abs_list else None
        rmse = math.sqrt(sum(sq_list) / len(sq_list)) if sq_list else None
        mape = sum(ape_list) / len(ape_list) if ape_list else None
        error_rel_mean = sum(rel_list) / len(rel_list) if rel_list else None
        
        result_overall[model] = {
            "model": model,
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "error_rel_mean": error_rel_mean,
            "weight_final": current_weight,
            "weight_mean": weight_mean,
            "n": len(abs_list)
        }

    # Ordenar por weight_final descendente para ranking
    ranked = sorted(
        result_overall.items(),
        key=lambda kv: kv[1].get("weight_final") or -float('inf'),
        reverse=True
    )
    
    # Agregar rank
    ranked_list = []
    for rank, (model_name, metrics) in enumerate(ranked, 1):
        metrics["rank"] = rank
        metrics["badge"] = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else ""
        ranked_list.append(metrics)
    
    sanitized = _sanitize_numbers({"id": id, "models": ranked_list})
    return JSONResponse(content=sanitized)

# Endpoint para obtener los IDs disponibles en InfluxDB
@app.get("/api/ids")
def get_available_ids():
    """Devuelve lista de IDs únicos disponibles en InfluxDB"""
    try:
        flux = f'''from(bucket:"{INFLUX_BUCKET}")
  |> range(start:-7d)
  |> filter(fn:(r)=> r._measurement=="telemetry")
  |> group(columns:["id"])
  |> distinct(column:"id")
  |> keep(columns:["id"])'''
        
        tables = _metrics_q.query(org=INFLUX_ORG, query=flux)
        ids = []
        seen = set()
        for table in tables:
            for record in table.records:
                id_val = record.values.get("id")
                if id_val and id_val not in seen:
                    ids.append(str(id_val))
                    seen.add(id_val)
        return {"ids": sorted(ids)}
    except Exception as e:
        logger.error(f"Error querying IDs: {e}", exc_info=True)
        return {"ids": []}

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
AGENT_URL       = os.getenv("AGENT_URL", "http://agent:8090")  # AP3: URL del agent

# ============================================================================
# AP3: Proxy endpoints para acceder a los datos del agent
# ============================================================================

@app.get("/api/agent/weights/{unit_id}")
def proxy_agent_weights(unit_id: str):
    """Obtain current weights of a HyperModel via agent"""
    try:
        r = httpx.get(f"{AGENT_URL}/api/weights/{unit_id}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {e}")

@app.get("/api/agent/history/{unit_id}")
def proxy_agent_history(unit_id: str, last_n: int = 100):
    """Obtain history of weights for analysis"""
    try:
        r = httpx.get(f"{AGENT_URL}/api/history/{unit_id}", params={"last_n": last_n}, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {e}")

@app.get("/api/agent/stats/{unit_id}")
def proxy_agent_stats(unit_id: str):
    """Obtain statistics by model for TFG memory"""
    try:
        r = httpx.get(f"{AGENT_URL}/api/stats/{unit_id}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {e}")

@app.get("/api/download_weights/{unit_id}")
def download_weights_csv(unit_id: str):
    try:
        # Obtain history of the agent
        r = httpx.get(f"{AGENT_URL}/api/history/{unit_id}", params={"last_n": 999999}, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        
        history = data.get("history", [])
        if not history:
            raise HTTPException(status_code=404, detail=f"No history for {unit_id}")
        
        # Convert a CSV in memory
        output = StringIO()
        fieldnames = list(history[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for entry in history:
            row = {}
            for k, v in entry.items():
                if isinstance(v, float):
                    row[k] = round(v, 6)
                else:
                    row[k] = v
            writer.writerow(row)
        
        csv_content = output.getvalue()

        # Save in /app/data for AI analysis
        csv_path = f"/app/data/weights_history_{unit_id}.csv"
        with open(csv_path, 'w') as f:
            f.write(csv_content)

        # Return as downloadable file
        filename = f"weights_history_{unit_id}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error generating CSV: {e}")

@app.post("/api/agent/export_csv/{unit_id}")
def proxy_agent_export_csv(unit_id: str):
    """AP3: Exportar historial a CSV"""
    try:
        r = httpx.post(f"{AGENT_URL}/api/export_csv/{unit_id}", timeout=30.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {e}")

# ============================================================================

@app.post("/api/run_window")
def run_window(source: str = Query("uploaded.csv"), speed_ms: int = Query(0), forecast_horizon: int = Query(1, ge=1, le=200)):
    """
    Dispara el window_loader con un CSV específico.
    
    Parámetros (query):
      - source: nombre del archivo CSV en /app/data (default: uploaded.csv)
      - speed_ms: delay en ms entre mensajes (default: 0 = sin delay)
      - forecast_horizon: horizonte de predicción seleccionado en frontend (T+N, default: 1)
    
    Uso: POST /api/run_window?source=archivo.csv&speed_ms=100&forecast_horizon=10
    """
    import time
    global _last_forecast_horizon
    
    logger.info(f"[orchestrator] run_window called: source={source}, speed_ms={speed_ms}, forecast_horizon={forecast_horizon}")
    
    # Save the forecast horizon for later use in multi-horizon endpoint
    _last_forecast_horizon["forecast_horizon"] = forecast_horizon
    _last_forecast_horizon["timestamp"] = datetime.now()
    logger.info(f"[orchestrator] Saved forecast_horizon={forecast_horizon} for this execution")
    
    # 1) Reset collector
    try:
        r_reset = httpx.post(COLLECTOR_RESET, timeout=30.0)
        r_reset.raise_for_status()
    except Exception as e:
        print(f"[orchestrator] collector reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"collector reset failed: {e}")

    # Pequeño delay para que el reset se propague
    time.sleep(1)

    # 2) Dispara loader con el CSV especificado y el horizonte
    payload = {
        "source": source,
        "speed_ms": speed_ms,
        "forecast_horizon": forecast_horizon  # Pass horizon to loader
    }
    
    try:
        print(f"[orchestrator] Triggering loader with source={source}, speed_ms={speed_ms}, forecast_horizon={forecast_horizon}")
        r_trig = httpx.post(LOADER_URL, json=payload, timeout=120.0)
        r_trig.raise_for_status()
        data = r_trig.json() if r_trig.text else {}
        print(f"[orchestrator] Loader response: {data}")
        return {"status": "success", "loader_response": data, "source": source, "forecast_horizon": forecast_horizon}
    except httpx.HTTPStatusError as e:
        print(f"[orchestrator] Loader HTTP error {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"loader trigger failed: {e.response.text}")
    except Exception as e:
        print(f"[orchestrator] Loader error: {e}")
        raise HTTPException(status_code=500, detail=f"loader trigger failed: {str(e)}")


@app.get("/api/forecast_horizon")
def get_forecast_horizon():
    """
    Retorna el horizonte de predicción guardado globalmente de la última ejecución.
    """
    global _last_forecast_horizon
    return {
        "forecast_horizon": _last_forecast_horizon.get("forecast_horizon", 1),
        "timestamp": _last_forecast_horizon.get("timestamp")
    }




@app.post("/api/reset_system")
def reset_system():
    """
    Completely resets the system to start a new experiment from scratch:
    3. Optionally clears InfluxDB (commented for safety)y)
    2. Resetea todos los HyperModels del agent (pesos e historial)
    Useful before running a new pipeline to avoid accumulation of
    
    Útil antes de ejecutar un nuevo pipeline para evitar acumulación de datos previos.
    """
    results = {
        "collector": {"status": "pending"},
        "agent": {"status": "pending"},
        "influxdb": {"status": "skipped", "message": "Manual cleanup required"}
    }
    
    # 1. Reset Collector
    try:
        r_collector = httpx.post(COLLECTOR_RESET, timeout=10.0)
        r_collector.raise_for_status()
        results["collector"] = {"status": "success", "response": r_collector.json()}
    except Exception as e:
        results["collector"] = {"status": "error", "message": str(e)}
    
    # 2. Reset Agent
    try:
        r_agent = httpx.post(f"{AGENT_URL}/api/reset_all", timeout=10.0)
        r_agent.raise_for_status()
        results["agent"] = {"status": "success", "response": r_agent.json()}
    except Exception as e:
        results["agent"] = {"status": "error", "message": str(e)}
    
    # 3. InfluxDB cleanup - Delete all previous data
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.delete_api import DeleteApi
        
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        delete_api = client.delete_api()
        
        # Delete ALL data
        start = "1970-01-01T00:00:00Z"
        stop = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"

        
        # List of ALL measurements that are written
        measurements = [
            "telemetry",           # predictions and real values
            "telemetry_models",    # predictions by individual model
            "weights",             # ensemble weights
            "chosen_model",        # chosen model
            "chosen_error",        # errors of the chosen model
            "model_errors",        # errors by model
            "model_rankings",      # model rankings
            "model_rewards",       # model rewards
            "weight_decisions"     # weight change decisions
        ]
        
        deleted_count = 0
        for measurement in measurements:
            try:
                delete_api.delete(start, stop, f'_measurement="{measurement}"', 
                                  bucket=INFLUX_BUCKET, org=INFLUX_ORG)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Could not delete {measurement}: {e}")
        
        client.close()
        results["influxdb"] = {
            "status": "success", 
            "message": f"Deleted {deleted_count}/{len(measurements)} measurements from InfluxDB",
            "measurements_deleted": deleted_count
        }
    except Exception as e:
        results["influxdb"] = {"status": "error", "message": str(e)}
    
    # Determinar status global
    all_success = (
        results["collector"]["status"] == "success" and
        results["agent"]["status"] == "success" and
        results["influxdb"]["status"] == "success"
    )
    
    return {
        "status": "success" if all_success else "partial",
        "timestamp": datetime.utcnow().isoformat(),
        "details": results,
        "message": "Complete system reset." if all_success else "Partial reset. Check details."
    }


# Uploads
UPLOAD_DIR = "/app/data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    dest_path = os.path.join(UPLOAD_DIR, "uploaded.csv") 
    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    # counts rows
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

# ==== GESTIÓN DE ESCENARIOS ====================================================

@app.post("/api/scenarios/save")
def save_scenario_endpoint(
    scenario_name: str = Query(..., description="Nombre del escenario (ej: escenario_0_baseline)"),
    unit_id: str = Query("Other", description="ID de la serie temporal")
):
    """
    Guarda el estado actual como un escenario para análisis posterior.
    
    Incluye:
    - Configuración del hypermodel (modo, decay, etc.)
    - Métricas agregadas (MAE, RMSE, distribución de modelos)
    - Historial completo de pesos
    """
    try:
        # 1. Obtener configuración del agente
        config_res = httpx.get(f"{AGENT_URL}/api/weights/{unit_id}", timeout=10.0)
        config_res.raise_for_status()
        config = {"hypermodel_mode": os.getenv("HYPERMODEL_MODE", "adaptive")}
        
        # 2. Obtener métricas agregadas del orchestrator
        metrics_res = httpx.get(f"http://localhost:8081/api/metrics/models/ranked", 
                                 params={"id": unit_id}, timeout=10.0)
        metrics_res.raise_for_status()
        metrics_data = metrics_res.json()
        
        # 3. Obtener historial completo del agente
        history_res = httpx.get(f"{AGENT_URL}/api/history/{unit_id}", 
                                params={"last_n": 999999}, timeout=30.0)
        history_res.raise_for_status()
        history = history_res.json().get("history", [])
        
        # 4. Guardar escenario
        filepath = ScenarioManager.save_scenario(
            scenario_name=scenario_name,
            unit_id=unit_id,
            config=config,
            metrics=metrics_data,
            history=history,
            metadata={
                "saved_from": "ui_button",
                "csv_source": "uploaded.csv"
            }
        )
        
        return {
            "success": True,
            "scenario_name": scenario_name,
            "filepath": filepath,
            "history_length": len(history),
            "metrics": metrics_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving scenario: {e}")

@app.get("/api/scenarios/list")
def list_scenarios_endpoint():
    """Lista todos los escenarios guardados"""
    try:
        scenarios = ScenarioManager.list_scenarios()
        return {
            "scenarios": scenarios,
            "total": len(scenarios)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing scenarios: {e}")

@app.get("/api/scenarios/load/{scenario_name}")
def load_scenario_endpoint(scenario_name: str):
    """Carga un escenario específico"""
    try:
        # Buscar archivo más reciente con ese nombre
        from pathlib import Path
        matches = list(Path("/app/data/scenarios").glob(f"{scenario_name}*.json"))
        if not matches:
            raise HTTPException(status_code=404, detail=f"Scenario {scenario_name} not found")
        
        latest = max(matches, key=lambda p: p.stat().st_mtime)
        data = ScenarioManager.load_scenario(str(latest))
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading scenario: {e}")

@app.post("/api/scenarios/compare")
def compare_scenarios_endpoint(scenario_names: List[str]):
    """Compara múltiples escenarios lado a lado"""
    try:
        comparison = ScenarioManager.compare_scenarios(scenario_names)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing scenarios: {e}")

@app.delete("/api/scenarios/delete/{scenario_name}")
def delete_scenario_endpoint(scenario_name: str):
    """Elimina un escenario guardado"""
    try:
        from pathlib import Path
        matches = list(Path("/app/data/scenarios").glob(f"{scenario_name}*.json"))
        if not matches:
            raise HTTPException(status_code=404, detail=f"Scenario {scenario_name} not found")
        
        latest = max(matches, key=lambda p: p.stat().st_mtime)
        success = ScenarioManager.delete_scenario(str(latest))
        
        if success:
            return {"success": True, "deleted": str(latest)}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete scenario")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting scenario: {e}")


@app.post("/api/analyze_report/{id}")
async def analyze_report(id: str):
    """
    Analiza el reporte exportado usando IA (Groq) con acceso completo al CSV
    para proporcionar un análisis profundo y accionable.
    """
    try:
        from groq import Groq
        import csv
        import os

        # Configure Groq API
        api_key = os.getenv("GROQ_API_KEY")
        
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="GROQ_API_KEY not configured. Get free API key at: https://console.groq.com/keys"
            )

        # Reads the complete exported CSV
        csv_path = f"/app/data/weights_history_{id}.csv"
        
        if not os.path.exists(csv_path):
            raise HTTPException(
                status_code=404,
                detail=f"No export found for series '{id}'. Please export the report first."
            )

        # Reads the complete exported CSV and extracts key information
        csv_data = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)
        
        if not csv_data:
            raise HTTPException(status_code=404, detail="CSV file is empty")

        # Analyze data structure
        total_points = len(csv_data)
        first_row = csv_data[0]
        last_row = csv_data[-1]

        # Extract columns de modelos (weight_*)
        model_names = [col.replace('weight_', '') for col in first_row.keys() if col.startswith('weight_')]
        
        # Compute final statistics for each model
        model_stats = {}
        for model in model_names:
            weights = []
            predictions = []
            
            for row in csv_data:
                try:
                    w = float(row.get(f'weight_{model}', 0))
                    weights.append(w)
                    
                    pred = float(row.get(f'pred_{model}', 0))
                    predictions.append(pred)
                except (ValueError, TypeError):
                    continue
            
            if weights:
                model_stats[model] = {
                    "weight_initial": round(weights[0], 4),
                    "weight_final": round(weights[-1], 4),
                    "weight_mean": round(sum(weights) / len(weights), 4),
                    "weight_max": round(max(weights), 4),
                    "weight_min": round(min(weights), 4),
                    "prediction_final": round(predictions[-1], 4) if predictions else 0
                }
        
        # Obtener valores reales y predicción ensemble
        real_values = [float(row.get('var', 0)) for row in csv_data if row.get('var')]
        ensemble_predictions = [float(row.get('prediction', 0)) for row in csv_data if row.get('prediction')]
        
        # Calcular error del ensemble (MAE y MAPE)
        ensemble_errors = []
        ensemble_ape = []
        for i in range(min(len(real_values), len(ensemble_predictions))):
            err = abs(ensemble_predictions[i] - real_values[i])
            ensemble_errors.append(err)
            
            # MAPE
            if real_values[i] != 0:
                ape = abs(err / real_values[i])
                ensemble_ape.append(ape)
        
        ensemble_mae = sum(ensemble_errors) / len(ensemble_errors) if ensemble_errors else 0
        ensemble_mape = (sum(ensemble_ape) / len(ensemble_ape) * 100) if ensemble_ape else 0
        
        # Calcular MAE y MAPE por modelo
        for model in model_names:
            preds = [float(row.get(f'pred_{model}', 0)) for row in csv_data]
            reals = [float(row.get('var', 0)) for row in csv_data]
            
            mae_list = []
            mape_list = []
            for i in range(min(len(preds), len(reals))):
                err = abs(preds[i] - reals[i])
                mae_list.append(err)
                if reals[i] != 0:
                    mape_list.append(abs(err / reals[i]))
            
            if model in model_stats:
                model_stats[model]['mae'] = round(sum(mae_list) / len(mae_list), 4) if mae_list else 0
                model_stats[model]['mape'] = round((sum(mape_list) / len(mape_list) * 100), 2) if mape_list else 0
        
        # Identificar tendencias de pesos
        weight_evolution = {}
        for model in model_names:
            weights = [float(row.get(f'weight_{model}', 0)) for row in csv_data]
            if len(weights) > 10:
                # Comparar primer 25% vs último 25%
                first_quarter = sum(weights[:len(weights)//4]) / (len(weights)//4)
                last_quarter = sum(weights[-len(weights)//4:]) / (len(weights)//4)
                trend = "Increasing" if last_quarter > first_quarter * 1.2 else "Decreasing" if last_quarter < first_quarter * 0.8 else "Stable"
                weight_evolution[model] = trend
        
        # Construir prompt detallado con TODOS los datos
        csv_sample = "\n".join([
            f"Point {i+1}: real={row.get('var', 'N/A')}, ensemble_pred={row.get('prediction', 'N/A')}, chosen_model={row.get('chosen_model', 'N/A')}"
            for i, row in enumerate(csv_data[:5])  # Primeros 5 puntos como muestra
        ])
        
        csv_sample += "\n...\n"
        csv_sample += "\n".join([
            f"Point {len(csv_data)-4+i}: real={row.get('var', 'N/A')}, ensemble_pred={row.get('prediction', 'N/A')}, chosen_model={row.get('chosen_model', 'N/A')}"
            for i, row in enumerate(csv_data[-5:])  # Últimos 5 puntos
        ])
        
        prompt = f"""You are an expert analyst in adaptive prediction systems and ensemble learning.

SYSTEM CONTEXT:
This is a SOFT ensemble prediction system combining 5 different models:
- **linear**: Simple linear regression
- **poly**: Polynomial regression (degree 2)
- **alphabeta**: Alpha-Beta filter (trend tracking)
- **kalman**: Kalman filter (Bayesian optimal)
- **naive**: Naive model (last observed value / persistence)

The system adjusts model WEIGHTS in real-time based on recent performance.
Final prediction: prediction = Σ(weight_i × pred_i)

EXPERIMENT DATA:
Total processed points: {total_points}
Ensemble MAE: {round(ensemble_mae, 4)}
Ensemble MAPE: {round(ensemble_mape, 2)}%
Overall Accuracy: {round(100 - ensemble_mape, 2)}%

MODEL STATISTICS:
{chr(10).join([f"**{model}**:" + chr(10) + 
               f"  - MAE: {stats.get('mae', 'N/A')}" + chr(10) +
               f"  - MAPE: {stats.get('mape', 'N/A')}%" + chr(10) +
               f"  - Initial weight: {stats['weight_initial']}" + chr(10) +
               f"  - Final weight: {stats['weight_final']}" + chr(10) +
               f"  - Average weight: {stats['weight_mean']}" + chr(10) +
               f"  - Weight range: [{stats['weight_min']}, {stats['weight_max']}]" + chr(10) +
               f"  - Trend: {weight_evolution.get(model, 'N/A')}" + chr(10) +
               f"  - Final prediction: {stats['prediction_final']}"
               for model, stats in sorted(model_stats.items(), key=lambda x: x[1]['weight_final'], reverse=True)])}

DATA SAMPLE (first and last points):
{csv_sample}

REQUIRED ANALYSIS:
Provide a DEEP and INSIGHTFUL analysis in Markdown format with the following sections:

## Executive Summary
Concise description of overall system performance (2-3 lines) with accuracy metrics.

## Model Performance Analysis

### Top Performers
Identify the 2-3 best models and explain:
- Why they have high weights
- What time series characteristics favor these models
- When they are most effective
- Specific MAE and MAPE values

### Weak Models
Identify underperforming models and explain:
- Why they have low weights
- What patterns they CANNOT capture effectively
- Their contribution to ensemble diversity

## Weight Evolution

Analyze how weights changed during the experiment:
- Which models gained confidence over time?
- Which models lost confidence?
- What does this indicate about the underlying data patterns?
- Stability analysis (convergence vs oscillation)

## Technical Insights

- **Ensemble Stability**: Did weights converge or continue oscillating? What does this mean?
- **Model Diversity**: Does the system rely on multiple models or is it dominated by one?
- **Prediction Quality**: Is the MAE/MAPE acceptable? How does it compare to baseline (naive)?
- **Error Distribution**: Are errors consistent or do they vary significantly throughout the series?
- **Recommendations**: Specific suggestions for improvement based on observed patterns

FORMAT REQUIREMENTS:
- Use clean Markdown with headers (##, ###)
- NO EMOJIS - professional technical report style
- Be specific and quantitative with actual numbers from the data
- Avoid vague generalities - reference specific metrics
- Length: 700-1000 words
- Tone: Professional, technical, data-driven
- Language: ENGLISH

CRITICAL: Base your analysis EXCLUSIVELY on the REAL DATA provided above. Do not make assumptions about missing data or use placeholder reasoning. If real values show MAE=0, question if this indicates perfect prediction or data quality issues."""

        # Llamar a Groq API
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert data scientist in time series forecasting, ensemble methods, and adaptive systems. You provide deep, quantitative analysis based on actual data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.6,
        )
        
        analysis = response.choices[0].message.content
        
        return {
            "success": True,
            "analysis": analysis,
            "series_id": id,
            "total_points": total_points,
            "ensemble_mae": round(ensemble_mae, 6),
            "model_stats": model_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
            
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Export file not found. Please export the report first using the 'Export Report' button."
        )
    except Exception as e:
        logger.error(f"Error in AI analysis: {e}")
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")


@app.post("/api/analyze_report_advanced/{id}")
async def analyze_report_advanced(
    id: str,
    body: dict = Body(...)
):
    """
    Análisis avanzado con IA usando:
    1. Pipeline report (datos de la última ejecución)
    2. Export report opcional (CSV con histórico de weights y rankings)
    
    Proporciona análisis profundo y contextualizado.
    """
    try:
        from groq import Groq
        import csv
        import json
        
        pipeline_report = body.get("pipeline_report", {})
        export_report_csv = body.get("export_report")
        export_filename = body.get("export_filename", "")
        
        # Configurar Groq API
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY not configured. Get free API key at: https://console.groq.com/keys"
            )
        
        # Context for AI

        pipeline_context = f"""
            ## Pipeline Execution Report

            **Series ID:** {pipeline_report.get('id', 'Unknown')}
            **Total Data Points:** {pipeline_report.get('total', 0)}

            ### Data Points Sample (first 5):
            """
        points = pipeline_report.get('points', [])[:5]
        for i, p in enumerate(points, 1):
            pipeline_context += f"\n{i}. Timestamp: {p.get('timestamp', 'N/A')}"
            pipeline_context += f"\n   - Real value: {p.get('var', 'N/A')}"
            pipeline_context += f"\n   - Prediction: {p.get('prediction', 'N/A')}"
            pipeline_context += f"\n   - Chosen model: {p.get('chosen_model', 'N/A')}"
            pipeline_context += f"\n   - Error: {p.get('chosen_error_abs', 'N/A')} (rel: {p.get('chosen_error_rel', 'N/A')}%)"
        
        # ===== Preparar contexto del export report =====
        export_context = ""
        if export_report_csv:
            export_context = f"\n\n## Historical Export Report\n\n**File:** {export_filename}\n\n### CSV Preview (first 10 rows):\n\n"
            csv_lines = export_report_csv.split('\n')
            # Header + primeras 10 filas
            preview_lines = csv_lines[:11]
            export_context += '\n'.join(preview_lines)
            export_context += "\n\n"
            
            # Análisis estadístico del CSV
            try:
                reader = csv.DictReader(export_report_csv.split('\n'))
                rows = list(reader)
                
                if rows:
                    # Extraer nombres de modelos

                    # Export CSV Context
                    model_names = [col.replace('w_', '') for col in rows[0].keys() if col.startswith('w_')]
                    
                    # Selection statistics
                    selections = {}
                    weights_evolution = {m: [] for m in model_names}
                    rankings_by_model = {m: [] for m in model_names}
                    
                    for row in rows:
                        chosen = row.get('chosen_by_error', '')
                        if chosen:
                            selections[chosen] = selections.get(chosen, 0) + 1
                        
                        for model in model_names:
                            w_key = f'w_{model}'
                            r_key = f'rank_{model}'
                            if w_key in row:
                                try:
                                    weights_evolution[model].append(float(row[w_key]))
                                except:
                                    pass
                            if r_key in row:
                                try:
                                    rankings_by_model[model].append(int(row[r_key]))
                                except:
                                    pass
                    
                    # Análisis de selección
                    export_context += f"### Model Selection Summary ({len(rows)} steps):\n\n"
                    for model in sorted(selections.keys(), key=lambda m: selections[m], reverse=True):
                        pct = (selections[model] / len(rows)) * 100
                        export_context += f"- **{model}**: {selections[model]} times ({pct:.1f}%)\n"
                    
                    # Análisis de pesos
                    export_context += f"\n### Weight Evolution:\n\n"
                    for model in model_names:
                        if weights_evolution[model]:
                            initial = weights_evolution[model][0]
                            final = weights_evolution[model][-1]
                            avg = sum(weights_evolution[model]) / len(weights_evolution[model])
                            max_w = max(weights_evolution[model])
                            min_w = min(weights_evolution[model])
                            export_context += f"\n**{model}:**\n"
                            export_context += f"  - Initial: {initial:.4f} → Final: {final:.4f}\n"
                            export_context += f"  - Average: {avg:.4f} (Range: {min_w:.4f} to {max_w:.4f})\n"
                    
                    # Análisis de rankings
                    export_context += f"\n### Average Rankings (lower is better):\n\n"
                    for model in model_names:
                        if rankings_by_model[model]:
                            avg_rank = sum(rankings_by_model[model]) / len(rankings_by_model[model])
                            export_context += f"- **{model}**: {avg_rank:.2f}\n"
            
            except Exception as e:
                logger.warning(f"Error parsing export CSV: {e}")
                export_context += f"\n(Could not fully parse CSV: {str(e)})"
        
        # ===== Crear prompt contextualizado para IA =====
        analysis_prompt = f"""
You are an expert data scientist specializing in ensemble learning, time series forecasting, and adaptive prediction systems.

Analyze the following report in DEEP DETAIL with specific, actionable insights:

{pipeline_context}

{export_context}

---

Please provide a comprehensive analysis covering:

1. **Model Performance Patterns**
   - Which models performed best in different periods?
   - Are there specific data characteristics where certain models excel?
   - How consistent is each model's performance?

2. **Weight Adaptation Quality**
   - Is the weight evolution system working effectively?
   - Are weights converging to stable values or oscillating?
   - Do the weights correlate with actual model performance?

3. **Selection Decisions**
   - How frequently was each model selected?
   - Is there diversity in model selection or dominance by one model?
   - Are selection patterns correlated with data characteristics?

4. **System Stability & Convergence**
   - Is the ensemble showing signs of overfitting to certain patterns?
   - How responsive is the system to changes in data characteristics?
   - Recommendations for weight decay, learning rates, or system parameters?

5. **Actionable Insights**
   - What specific improvements could enhance predictions?
   - Should any models be removed, replaced, or reweighted?
   - Any data quality issues or anomalies to investigate?

Provide specific numbers, percentages, and data-driven evidence for all claims.
Use markdown formatting for clarity.
"""

        # Chat Completion Call Details

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert data scientist in time series forecasting and ensemble learning. Provide deep, quantitative, actionable analysis based on the actual data provided."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            max_tokens=4000,
            temperature=0.7,
        )
        
        analysis = response.choices[0].message.content
        
        return {
            "success": True,
            "analysis": analysis,
            "series_id": id,
            "analysis_type": "advanced",
            "pipeline_points": len(points),
            "export_file": export_filename if export_report_csv else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in advanced AI analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


