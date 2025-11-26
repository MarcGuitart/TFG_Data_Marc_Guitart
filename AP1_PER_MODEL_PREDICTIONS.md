# ACTION POINT 1 - Per-Model Predictions Visualization

## ✅ STATUS: COMPLETED

**Date:** 25 November 2025  
**Objective:** Display ALL model predictions separately to analyze which model performs better in different scenarios

---

## 🎯 What the Tutor Wants

1. **See each model's behavior separately** over the real time series (not averages or abstract metrics)
2. **Simple adaptive agent** that switches models based on which performs better at each instant
3. **Weights/rewards system** per model showing accumulated evidence of performance (visible in metrics table, ideally top-3)

**TFG Requirements:**
- Demonstrate this as an **experimental tool** (avoid going "blind" when testing models)
- Show it's **easy to integrate in production** (new Kafka topic → 4 clicks → prediction running)
- **Timeline:** All code and results ready ~December 8th, then only writing the thesis

---

## 📊 Implementation Details

### Backend: Per-Model Prediction Endpoint

**Endpoint:** `GET /api/series?id={id}&hours={hours}`

**Response Structure:**
```json
{
  "id": "Other",
  "observed": [
    {"t": "2025-11-25T17:00:00+00:00", "y": 0.197159}
  ],
  "predicted": [
    {"t": "2025-11-25T17:00:00+00:00", "y_hat": 0.196370}
  ],
  "models": {
    "ab_fast": [
      {"t": "2025-11-25T17:00:00+00:00", "y_hat": 0.197002}
    ],
    "linear_8": [
      {"t": "2025-11-25T17:00:00+00:00", "y_hat": 0.197441}
    ],
    "poly2_12": [
      {"t": "2025-11-25T17:00:00+00:00", "y_hat": 0.194464}
    ]
  },
  "points": [
    {
      "t": 1764090000000,
      "var": 0.197159,
      "prediction": 0.196370,
      "ab_fast": 0.197002,
      "linear_8": 0.197441,
      "poly2_12": 0.194464
    }
  ]
}
```

**Key Changes:**
- Added `_query_models_yhat()` helper that queries `telemetry_models` measurement from InfluxDB
- Modified `/api/series` to return:
  - `observed`: Real values (var)
  - `predicted`: Combined HyperModel prediction (weighted average)
  - `models`: Per-model predictions as separate series
  - `points`: Flattened format ready for `CsvChart` component

**Files Modified:**
- `services/orchestrator/app.py` (lines 98-228)

---

### Agent: HyperModel Per-Model Predictions

**HyperModel System:**
```python
class HyperModel:
    def predict(self, series) -> Tuple[float, Dict[str, float]]:
        """
        Returns:
          y_hat: Combined prediction (weighted average)
          preds_by_model: {model_name: prediction, ...}
        """
        preds = {m.name: float(m.predict(series)) for m in self.models}
        # ... weighted combination logic ...
        return float(y_hat), preds
```

**Active Models** (from `model_config.json`):
1. **linear_8**: Linear regression on last 8 points
2. **poly2_12**: Polynomial degree 2 on last 12 points  
3. **ab_fast**: Alpha-Beta filter (α=0.85, β=0.01)

**Adaptive Weights:**
- Models are weighted based on inverse error: `w = 1 / (ε + |y_true - y_pred|)`
- Weights decay over time: `w_new = decay * w_old + (1-decay) * score`
- Configurable via ENV: `HYPERMODEL_DECAY=0.95`, `HYPERMODEL_W_CAP=10.0`

**Files:**
- `services/agent/main.py` (lines 293-334): Prediction loop with weight updates
- `services/agent/hypermodel/hyper_model.py`: HyperModel class
- `services/agent/hypermodel/model_config.json`: Model configuration

---

### Collector: Writing Per-Model Data to InfluxDB

**InfluxDB Measurements:**
1. **telemetry**: Observed values (`var`) and combined prediction (`prediction`)
2. **telemetry_models**: Per-model predictions (`yhat`) with tags:
   - `id`: series identifier
   - `model`: model name (linear_8, poly2_12, ab_fast)
3. **weights**: Model weights over time (optional telemetry)

**Write Logic:**
```python
def write_to_influx(rec):
    per_model = rec.get("hyper_models")
    if isinstance(per_model, dict):
        for model_name, yhat_m in per_model.items():
            _write_api.write(
                bucket=INFLUX_BUCKET,
                record=(
                    Point("telemetry_models")
                    .tag("id", unit)
                    .tag("model", str(model_name))
                    .field("yhat", float(yhat_m))
                    .time(ts_pred, WritePrecision.S)
                ),
            )
```

**Files Modified:**
- `services/window_collector/main.py` (lines 79-97)

---

### Frontend: Visualization

**Component:** `DataPipelineLiveViewer.jsx`

**New Button:** "Load backend series (per-model)"
- Fetches `/api/series` endpoint
- Displays per-model predictions alongside real values

**Visualization:**
- **Blue solid line**: Real observed values (`var`)
- **Orange dashed line**: Combined HyperModel prediction
- **Colored lines**: Individual model predictions
  - Green: `ab_fast`
  - Purple: `linear_8`
  - Pink: `poly2_12`

**Chart Component:** `CsvChart.jsx`
- Automatically detects extra keys (model names) in data points
- Renders each model as a separate `<Line>` component
- Dynamic color palette for up to 5 models

**Files Modified:**
- `frontend/src/components/DataPipelineLiveViewer.jsx` (lines 141-160, 419-444)
- `frontend/src/components/CsvChart.jsx` (already had dynamic model support)

---

## 🧪 Verification

### 1. Check Agent Logs
```bash
docker logs docker-agent-1 --tail 30 | grep pred
```

**Expected Output:**
```
INFO:agent:[pred] id=Other y=0.222165 y_hat=0.228401 buf=32 models=linear_8,poly2_12,ab_fast
```

### 2. Check InfluxDB Data
```bash
docker exec docker-influxdb-1 influx query \
  'from(bucket:"pipeline") 
   |> range(start:-1h) 
   |> filter(fn:(r)=> r._measurement=="telemetry_models") 
   |> limit(n:10)' \
  -o tfg -t admin_token
```

**Expected Output:**
```
Table: keys: [_start, _stop, _field, _measurement, id, model]
id:string    model:string    _time:time                     _value:float
Other        ab_fast         2025-11-25T17:00:00Z          0.197002
Other        linear_8        2025-11-25T17:00:00Z          0.197441
Other        poly2_12        2025-11-25T17:00:00Z          0.194464
```

### 3. Test Backend Endpoint
```bash
curl "http://localhost:8081/api/series?id=Other&hours=1" | jq .
```

**Expected Keys:** `id`, `observed`, `predicted`, `models`, `points`

### 4. Frontend Test
1. Open http://localhost:5173
2. Upload CSV file
3. Click "🚀 Ejecutar agente"
4. Select ID from dropdown
5. Click "Load backend series (per-model)"
6. **Verify:** Chart shows Real (blue), Pred (orange dashed), and 3 colored model lines

---

## 📸 Screenshots Required for AP1

### Screenshot 1: All Models Overlaid
**What to capture:**
- Full browser window showing `DataPipelineLiveViewer`
- Chart with:
  - Real data (blue line)
  - Combined prediction (orange dashed)
  - All 3 model lines (green, purple, pink)
- Legend clearly visible showing all series names
- Metadata box showing: ID, Points count, Models list

**Filename:** `AP1_all_models_overlay.png`

### Screenshot 2: Metrics Table (Per-Model)
**What to capture:**
- Click "Load metrics" button
- MetricsPanel showing:
  - Combined metrics (MAE, RMSE, MAPE)
  - Per-model metrics table
  - Weights column showing adaptive learning

**Filename:** `AP1_per_model_metrics.png`

### Screenshot 3: InfluxDB Query
**What to capture:**
- Terminal showing InfluxDB query for `telemetry_models`
- Table output with multiple models visible

**Filename:** `AP1_influxdb_verification.png`

---

## 📝 Analysis for Thesis

### Observations to Make:

1. **Traffic Peak Behavior:**
   - "En este pico de tráfico, el modelo `linear_8` predice mejor porque captura la tendencia lineal ascendente"
   - "El modelo `poly2_12` se adapta más rápido a cambios curvos en la serie"

2. **Smooth Zones:**
   - "En zonas suaves, el modelo `ab_fast` (Alpha-Beta) mantiene predicciones más estables"
   - "Los modelos polinomiales tienden a sobreajustar en datos ruidosos"

3. **Adaptive Weighting:**
   - "El sistema de pesos adapta automáticamente la confianza en cada modelo"
   - "Modelos con menor error acumulado reciben mayor peso en la predicción combinada"

4. **Production Readiness:**
   - "Agregar un nuevo modelo solo requiere: (1) implementar clase BaseModel, (2) añadir a model_config.json, (3) reiniciar agente"
   - "El sistema de Kafka permite integración sin downtime: nuevo topic → configuración → start"

---

## 🚀 Next Steps (AP2 & AP3)

### AP2: Adaptive Agent
- Implement model selection based on recent performance
- Add threshold-based switching logic
- Log model switches for analysis

### AP3: Weights Dashboard
- Display top-3 models by weight
- Show weight evolution over time
- Add model performance histogram

---

## 📦 Files Changed Summary

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `services/orchestrator/app.py` | 98-228 | Added per-model series endpoint |
| `services/agent/main.py` | 293-334 | Per-model prediction and weight updates |
| `services/window_collector/main.py` | 79-97 | Write per-model data to InfluxDB |
| `frontend/src/components/DataPipelineLiveViewer.jsx` | 141-160, 419-444 | UI for per-model visualization |
| `frontend/src/components/CsvChart.jsx` | (no changes needed) | Already had dynamic model support |

---

## ✅ Completion Checklist

- [x] Backend returns per-model predictions in `/api/series`
- [x] Agent generates per-model predictions via HyperModel
- [x] Collector writes per-model data to InfluxDB `telemetry_models`
- [x] Frontend displays per-model chart with legend
- [x] InfluxDB verification query works
- [x] Docker images rebuilt and services restarted
- [ ] Screenshots captured (pending user action)
- [ ] Analysis text written for thesis (pending user action)

---

**Status:** READY FOR SCREENSHOTS AND ANALYSIS

The system is now fully functional and displays all per-model predictions. The user should:
1. Load a CSV file
2. Execute the agent
3. Click "Load backend series (per-model)"
4. Take screenshots
5. Analyze which models perform better in different scenarios
6. Document findings for the thesis
