# services/agent/main.py
import os, json, time, socket, datetime, threading, logging, collections
from datetime import datetime, timedelta, timezone
from kafka import KafkaConsumer, KafkaProducer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.delete_api import DeleteApi
from fastapi import FastAPI
import uvicorn
from hypermodel.hyper_model import HyperModel
from datetime import datetime, timedelta, timezone

def now_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc)

def shift_ts_to_today(ts_str: str | None) -> datetime:
    """
    Mantiene la fecha y hora del CSV pero las traslada al pasado reciente.
    Calcula cuántos días atrás estaba el timestamp original y lo traslada
    manteniendo esa distancia relativa, pero dentro de la ventana de retention.
    """
    base = now_utc()
    if not ts_str:
        return base
    
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        original_dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return base
    
    # Referencia: usamos una fecha base del CSV (primera fecha que aparezca)
    reference_date = datetime(2025, 3, 10)  # Primera fecha del CSV típico
    
    # Calculamos cuántos segundos han pasado desde la referencia
    delta_seconds = (original_dt - reference_date).total_seconds()
    
    # Creamos un timestamp 7 días atrás desde ahora y sumamos el delta
    # Esto asegura que incluso el último punto del CSV esté en el pasado
    base_past = base - timedelta(days=7)  # 7 días atrás (dentro de retention)
    
    # Sumamos el delta desde la referencia
    result_dt = base_past + timedelta(seconds=delta_seconds)
    
    return result_dt

def parse_ts_keep_date(ts_str):
    """Parsea 'YYYY-mm-dd HH:MM:SS' o ISO y conserva fecha y hora; salida UTC."""
    if not ts_str:
        return now_utc()
    s = str(ts_str).replace("T", " ").replace("Z", "")
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        dt = datetime.utcnow()
    return dt.replace(tzinfo=timezone.utc)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent")

# === MODELOS ===
try:
    # Modelo previo (lo conservamos para compatibilidad con learner/estado)
    from agent.model import NaiveDailyProfileModel
except ModuleNotFoundError:
    from model import NaiveDailyProfileModel

# --- HyperModel (nuevo) ---
# Permitimos dos rutas de import para no depender del layout exacto del paquete
try:
    from agent.hypermodel.hyper_model import HyperModel
except ModuleNotFoundError:
    try:
        from hypermodel.hyper_model import HyperModel
    except ModuleNotFoundError:
        # fallback muy directo si lo tienes plano
        from hyper_model import HyperModel

# === CONFIG ===
FLAVOR = os.getenv("FLAVOR", "inference")
BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TIN = os.getenv("TOPIC_AGENT_IN", "telemetry.agent.in")
TOUT = os.getenv("TOPIC_AGENT_OUT", "telemetry.agent.out")
# arriba, junto a otras ENV
PRESERVE_DATES = os.getenv("PRESERVE_DATES", "false").lower() == "true"


INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin_token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "tfg")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "pipeline")
MAX_ROWS_PER_UNIT = int(os.getenv("MAX_ROWS_PER_UNIT", "1000"))

LEARN_LOOKBACK_DAYS = int(os.getenv("LEARN_LOOKBACK_DAYS", "30"))
LEARN_PERIOD_SEC    = int(os.getenv("LEARN_PERIOD_SEC", "86400"))

# --- HyperModel config ---
HYPER_CFG_PATH = os.getenv("HYPERMODEL_CONFIG", "/app/hypermodel/model_config.json")
HYPER_DECAY    = float(os.getenv("HYPERMODEL_DECAY", "0.95"))
HYPER_W_CAP    = float(os.getenv("HYPERMODEL_W_CAP", "10.0"))
HYPER_MODE     = os.getenv("HYPERMODEL_MODE", "adaptive")  # "weighted" o "adaptive"
BUFFER_LEN     = int(os.getenv("BUFFER_LEN", "32"))  # tamaño ventana por id

# === HTTP app (health) ===
app = FastAPI()

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/api/weights/{unit_id}")
def get_weights(unit_id: str):
    """AP3: Devuelve los pesos actuales de un HyperModel por unit_id"""
    hm = hyper_by_id.get(unit_id)
    if not hm:
        return {"error": f"No HyperModel for {unit_id}", "weights": {}}
    return {"unit_id": unit_id, "weights": hm.export_state()}

@app.get("/api/history/{unit_id}")
def get_history(unit_id: str, last_n: int = 100):
    """AP3: Devuelve el historial de pesos para análisis"""
    hm = hyper_by_id.get(unit_id)
    if not hm:
        return {"error": f"No HyperModel for {unit_id}", "history": []}
    history = hm.get_history()
    return {
        "unit_id": unit_id,
        "total_steps": len(history),
        "history": history[-last_n:] if last_n else history
    }

@app.get("/api/stats/{unit_id}")
def get_model_stats(unit_id: str):
    """AP3: Estadísticas por modelo para la memoria del TFG"""
    hm = hyper_by_id.get(unit_id)
    if not hm:
        return {"error": f"No HyperModel for {unit_id}"}
    return {
        "unit_id": unit_id,
        "stats": hm.get_model_stats(),
        "choices_diff": hm.get_choices_diff_count()
    }


# Agent-side export handler showing filename and storage location

@app.post("/api/export_csv/{unit_id}")
def export_csv(unit_id: str):
    """Export history to CSV for analysis in Excel"""
    hm = hyper_by_id.get(unit_id)
    if not hm:
        return {"error": f"No HyperModel for {unit_id}"}
    
    filepath = f"/app/data/weights_history_{unit_id}.csv"
    result = hm.export_history_csv(filepath)
    return {"unit_id": unit_id, "filepath": result}

@app.post("/api/reset/{unit_id}")
def reset_hypermodel(unit_id: str):
    """
    Resets the HyperModel for a specific unit:
    - Resets weights to 0
    - Clears prediction history
    - Resets counters
    - Resets base model buffers (for reproducibility)
    - Clears observation buffer

    Useful for starting experiments from scratch without prior memory accumulation.
    """
    hm = hyper_by_id.get(unit_id)
    if not hm:
        return {"error": f"No HyperModel for {unit_id}", "status": "not_found"}
    
    # Reset completo (incluye modelos base)
    hm.reset_complete()
    
    # Limpiar buffer de observaciones
    if unit_id in buffers_by_id:
        buffers_by_id[unit_id].clear()
    
    # Limpiar última predicción
    if unit_id in last_pred_by_id:
        del last_pred_by_id[unit_id]
    
    log.info(f"[reset] HyperModel, buffer y predicciones reseteados completamente para {unit_id}")
    
    return {
        "status": "reset",
        "unit_id": unit_id,
        "weights": dict(hm.w),
        "history_length": len(hm._history),
        "buffer_length": len(buffers_by_id.get(unit_id, [])),
        "message": f"HyperModel {unit_id} reiniciado a estado inicial (pesos, historial, buffers de observaciones)"
    }

@app.post("/api/reset_all")
def reset_all_hypermodels():
    """
    Reset ALL the active HyperModels and their observation buffers.
    Useful for completely clearing the system before a new experiment.
    """
    reset_count = 0
    unit_ids = []
    
    for unit_id, hm in list(hyper_by_id.items()):
        # Reset completo (incluye modelos base)
        hm.reset_complete()
        
        # Limpiar buffer de observaciones
        if unit_id in buffers_by_id:
            buffers_by_id[unit_id].clear()
        
        # Limpiar última predicción
        if unit_id in last_pred_by_id:
            del last_pred_by_id[unit_id]
        
        reset_count += 1
        unit_ids.append(unit_id)
        log.info(f"[reset_all] HyperModel, buffer and predictions reset for {unit_id}")

    return {
        "status": "reset_all",
        "reset_count": reset_count,
        "unit_ids": unit_ids,
        "message": f"{reset_count} HyperModels completely reset (weights, history, observation buffers)"
    }

# === CLIENTES Influx ===
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
delete_api: DeleteApi = client.delete_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

# === UTILIDADES TIEMPO ===

def select_ts(ts_str):
    return parse_ts_keep_date(ts_str) if PRESERVE_DATES else shift_ts_to_today(ts_str)


# === ESPERA KAFKA ===
def wait_for_kafka(broker: str, timeout=300):
    host, port = broker.split(":")
    port = int(port)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, port), timeout=3):
                log.info(f"Kafka OK en {broker}")
                return
        except Exception as e:
            log.info(f"Esperando Kafka {broker} ... {e}")
            time.sleep(2)
    raise RuntimeError(f"Kafka no disponible en {broker}")

# === MODELO DIARIO (legacy) ===
MODEL_PATH = os.getenv("MODEL_PATH", "/app/data/model_naive_daily.json")
SLOT_MINUTES = int(os.getenv("SLOT_MINUTES", "30"))
PRED_HORIZON_MIN = int(os.getenv("PRED_HORIZON_MIN", str(SLOT_MINUTES)))
model = NaiveDailyProfileModel(slot_minutes=SLOT_MINUTES, horizon_slots=max(1, PRED_HORIZON_MIN // SLOT_MINUTES))
try:
    if os.path.exists(MODEL_PATH):
        model.load(MODEL_PATH)
except Exception as e:
    log.warning("no se pudo cargar modelo diario: %s", e)

# === CAP POR UNIDAD ===
def enforce_cap_per_unit():
    q = client.query_api()
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "id")
    '''
    units = [r.get_value() for t in q.query(org=INFLUX_ORG, query=flux) for r in t.records]
    for u in units:
        flux2 = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "telemetry" and r["id"] == "{u}")
          |> count()
        '''
        tables = q.query(org=INFLUX_ORG, query=flux2)
        count = sum(r.get_value() for t in tables for r in t.records)
        if count > MAX_ROWS_PER_UNIT:
            start = "1970-01-01T00:00:00Z"
            stop = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            delete_api.delete(start, stop, f'_measurement="telemetry" AND id="{u}"',
                              bucket=INFLUX_BUCKET, org=INFLUX_ORG)
            log.info("purgados datos antiguos de id=%s", u)

def auto_purge():
    while True:
        try:
            enforce_cap_per_unit()
        except Exception as e:
            log.error("Error en auto-purge: %s", e)
        time.sleep(300)

# Automatic exportation of histories to CSV
CSV_EXPORT_PERIOD = int(os.getenv("CSV_EXPORT_PERIOD_SEC", "300"))  # cada 5 min

def auto_export_csv():
    """Automatically exports histories to CSV for offline analysis"""
    while True:
        time.sleep(CSV_EXPORT_PERIOD)
        try:
            for unit_id, hm in list(hyper_by_id.items()):
                if hm._history:  # Only if there is data
                    filepath = f"/app/data/weights_history_{unit_id}.csv"
                    result = hm.export_history_csv(filepath)
                    log.info("CSV exported: %s (%d steps)", result, len(hm._history))
        except Exception as e:
            log.error("Error exporting CSV: %s", e)

# === ESCRITURA TELEMETRÍA ===
def write_timeseries(rec):
    unit = rec.get("unit_id") or rec.get("id") or "unknown"
    p = Point("telemetry").tag("id", unit)
    fields_added = False
    # Aceptamos alias comunes y v1..v5
    value_fields = ["var", "value", "traffic", "count", "y", "v1", "v2", "v3", "v4", "v5"]
    for f in value_fields:
        if f in rec and rec[f] is not None:
            try:
                p = p.field(f, float(rec[f]))
                fields_added = True
            except Exception as e:
                log.warning("field cast error: %s rec=%s", e, rec)
            break
    if not fields_added:
        p = p.field("dummy", 1.0)
    ts = select_ts(rec.get("timestamp"))
    p = p.time(ts, WritePrecision.S)
    if "var" in rec and rec["var"] is not None:
        try:
            model.update_buffer(float(rec["var"]))  # legacy buffer (no interfiere)
        except Exception:
            pass
    try:
        write_api.write(bucket=INFLUX_BUCKET, record=p)
        log.info("✅ Escrito telemetry.var: unit=%s ts=%s", unit, ts)
    except Exception as e:
        log.error("❌ Error escribiendo telemetry.var: %s", e)

def write_prediction(unit: str, when: datetime, yhat: float):
    p = Point("telemetry").tag("id", unit).field("prediction", float(yhat)).time(when, WritePrecision.S)
    try:
        write_api.write(bucket=INFLUX_BUCKET, record=p)
        log.info("✅ Escrito telemetry.prediction: unit=%s ts=%s", unit, when)
    except Exception as e:
        log.error("❌ Error escribiendo telemetry.prediction: %s", e)

# === TRAINER (legacy, compatible con tag id) ===
def query_training_rows(unit: str, lookback_days: int = LEARN_LOOKBACK_DAYS):
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{lookback_days}d)
      |> filter(fn: (r) => r["_measurement"] == "telemetry" and r["id"] == "{unit}" and r["_field"] == "var")
      |> keep(columns: ["_time","_value"])
      |> sort(columns: ["_time"])
    '''
    tables = client.query_api().query(org=INFLUX_ORG, query=flux)
    rows = []
    for t in tables:
        for r in t.records:
            rows.append({"_time": r.get_time(), "var": float(r.get_value())})
    return rows

def learner_loop():
    while True:
        try:
            flux_units = f'''
            import "influxdata/influxdb/schema"
            schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "id")
            '''
            tabs = client.query_api().query(org=INFLUX_ORG, query=flux_units)
            units = list({ r.get_value() for t in tabs for r in t.records if r.get_value() })
            for u in units:
                rows = query_training_rows(u, lookback_days=LEARN_LOOKBACK_DAYS)
                if rows:
                    try:
                        model.update(rows)
                        log.info("learner: updated model with %d rows for id=%s", len(rows), u)
                        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
                        model.save(MODEL_PATH)
                    except Exception as e:
                        log.error("learner: error updating/saving model: %s", e)
        except Exception as e:
            log.error("learner error: %s", e)
        time.sleep(LEARN_PERIOD_SEC)



# === HYPERMODEL STATE (por id) ===
buffers_by_id: dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque(maxlen=BUFFER_LEN))
hyper_by_id: dict[str, HyperModel] = {}
last_pred_by_id: dict[str, float] = {}


def get_hyper_for(unit_id: str) -> HyperModel:
    hm = hyper_by_id.get(unit_id)
    if hm is None:
        # instantiate a HyperModel per id so that weights are independent per stream
        hm = HyperModel(cfg_path=HYPER_CFG_PATH, decay=HYPER_DECAY, w_cap=HYPER_W_CAP, mode=HYPER_MODE)
        hyper_by_id[unit_id] = hm
        log.info("[hypermodel] creado para id=%s (cfg=%s, decay=%.3f, w_cap=%.1f, mode=%s)",
                 unit_id, HYPER_CFG_PATH, HYPER_DECAY, HYPER_W_CAP, HYPER_MODE)
    return hm

# === MAIN LOOP ===
def main():
    wait_for_kafka(BROKER, timeout=300)
    consumer = KafkaConsumer(
        TIN,
        bootstrap_servers=BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="agent-v2-greedy"  # Cambiar para resetear offset
    )
    producer = KafkaProducer(
        bootstrap_servers=BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    threading.Thread(target=auto_purge, daemon=True).start()
    threading.Thread(target=learner_loop, daemon=True).start()
    threading.Thread(target=auto_export_csv, daemon=True).start()  # AP3: exportación CSV

    log.info("escuchando %s y publicando en %s", TIN, TOUT)


    for msg in consumer:
        try:
            rec = msg.value
            log.info("[in] %s", rec)
        except Exception as e:
            log.error("error deserializando: %s %s", e, msg.value)
            continue

        try:
            write_timeseries(rec)
        except Exception as e:
            log.error("influx write error: %s", e)


        # Nearby evaluation block: Contrast auditable

        try:
            unit = rec.get("unit_id") or rec.get("id") or "unknown"
            y_real = rec.get("var")
            base_ts = select_ts(rec.get("timestamp"))
            # ts_pred is calculated later after we know the horizon

            best_model = None
            ts_str = rec.get("timestamp") or base_ts.isoformat()
            if unit in last_pred_by_id and y_real is not None:
                hm = get_hyper_for(unit)
                try:
                    # Passing timestamp
                    best_model = hm.update_weights(float(y_real), ts=ts_str)
                except Exception as e:
                    log.warning("[hypermodel] update_weights error: %s", e)

            buf = buffers_by_id[unit]
            if y_real is not None:
                try:
                    buf.append(float(y_real))
                except Exception:
                    pass

            # The evaluation block: y_true vs stored y_hat, score update, overwrite

            # Get horizon from message (sent by loader) or fall back to env variable
            # forecast_horizon from message is in SLOTS (1 = T+1, 5 = T+5)
            msg_horizon = rec.get("forecast_horizon")
            if msg_horizon is not None:
                horizon_slots = max(1, int(msg_horizon))
                horizon_minutes = horizon_slots * SLOT_MINUTES
            else:
                # Fall back to environment variable
                horizon_slots = max(1, PRED_HORIZON_MIN // SLOT_MINUTES)
                horizon_minutes = PRED_HORIZON_MIN

            log.info(f"[horizon] Using horizon_slots={horizon_slots} (T+{horizon_slots}, {horizon_minutes} min)")

            hm = get_hyper_for(unit)
            # Pass horizon to HyperModel so each model predicts T+M instead of T+1
            y_hat, preds_by_model = hm.predict(list(buf), horizon=horizon_slots)
            weights = hm.export_state()
            chosen_model = hm.get_chosen_model()  # Chosen model
            last_errors = hm.get_last_errors()     # Last step absolute errors
            last_errors_rel = hm.get_last_errors_rel()  # Relative errors
            chosen_error = hm.get_chosen_error()   # Chosen model error
            last_pred_by_id[unit] = y_hat

            # Calculate ts_pred based on the horizon
            ts_pred = base_ts + timedelta(minutes=horizon_minutes)  # t + m
            
            log.info("[pred-ts] base=%s ts_pred=%s horizon=T+%d delta_min=%.1f",
                base_ts.isoformat(), ts_pred.isoformat(), horizon_slots,
                (ts_pred - base_ts).total_seconds()/60.0)
            

            # Preserving the horizon and writing the prediction
            # KEY: Separamos semántica temporal:
            # - t_decision (base_ts): momento en que se genera la predicción
            # - t_target (ts_pred): momento futuro que se está prediciendo
            # - horizon: número de slots adelante (m)

            write_prediction(unit, ts_pred, y_hat)

            # 4) Publicamos mensaje enriquecido (compatible + telemetría HyperModel)
            enriched = dict(rec)
            enriched["yhat"] = float(y_hat)                  # COMPAT: collector la escribe en 'prediction'
            enriched["ts_pred"] = ts_pred.strftime("%Y-%m-%d %H:%M:%S")  # t + m (evaluation time)
            enriched["ts_decision"] = base_ts.strftime("%Y-%m-%d %H:%M:%S")  # t (decision time)
            enriched["ts_influx"] = base_ts.strftime("%Y-%m-%d %H:%M:%S")  # Timestamp que usamos para InfluxDB
            enriched["horizon"] = horizon_slots  # m (number of slots ahead)
            enriched["mode"] = FLAVOR
            if "timestamp" in enriched and "ts" not in enriched:
                enriched["ts"] = enriched["timestamp"]

            # Telemetría opcional (por si luego la colectas en otra measurement)
            enriched["hyper_y_hat"] = float(y_hat)
            enriched["hyper_models"] = preds_by_model
            enriched["hyper_weights"] = weights
            enriched["hyper_chosen"] = chosen_model       # Modelo elegido (AP2)
            enriched["hyper_errors"] = last_errors        # Errores absolutos por modelo
            enriched["hyper_errors_rel"] = last_errors_rel  # AP2: Errores relativos por modelo
            
            # AP2: Error específico del modelo elegido
            enriched["chosen_error_abs"] = chosen_error.get("abs", 0.0)
            enriched["chosen_error_rel"] = chosen_error.get("rel", 0.0)
            
            # AP3: Información adicional del sistema de pesos con memoria
            last_entry = hm.get_last_history_entry()
            if last_entry:
                enriched["chosen_by_error"] = last_entry.get("chosen_by_error", "")
                enriched["chosen_by_weight"] = last_entry.get("chosen_by_weight", "")
                enriched["choices_differ"] = last_entry.get("choices_differ", False)
                enriched["decay_share"] = last_entry.get("decay_share", 0.0)
                # Rankings de este step
                enriched["rankings"] = {name: last_entry.get(f"rank_{name}", 0) for name in hm.model_names}
                enriched["rewards"] = {name: last_entry.get(f"reward_{name}", 0) for name in hm.model_names}

            producer.send(TOUT, enriched)
            producer.flush()

            log.info("[pred] id=%s y=%s y_hat=%.6f buf=%d models=%s chosen=%s",
                     unit, str(y_real), y_hat, len(buf), ",".join(preds_by_model.keys()), chosen_model or "N/A")

            # 5) Pequeño efecto demo (tu lógica original)
            if FLAVOR != "training" and "v1" in rec:
                try: enriched["v1"] = round(float(rec["v1"]) * 1.1, 6)
                except: pass

        except Exception as e:
            log.error("prediction error: %s", e)
            # En error, preserva flujo original
            if "timestamp" in rec and "ts" not in rec:
                rec["ts"] = rec["timestamp"]
            producer.send(TOUT, rec)

if __name__ == "__main__":
    log.info("conectado a Influx %s, bucket=%s, org=%s", INFLUX_URL, INFLUX_BUCKET, INFLUX_ORG)
    log.info("escuchando %s y publicando en %s", TIN, TOUT)
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8090, log_level="warning"), daemon=True).start()
    main()