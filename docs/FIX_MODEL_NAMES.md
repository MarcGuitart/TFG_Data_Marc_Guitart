# Fix: Model Names Consistency (base → naive)

## Problem Identified
The system had an **inconsistency in model naming**:
- **Backend Configuration**: Used "base" as the model name for the naive/baseline model
- **Frontend Constants**: Expected "naive" as the model name
- **Result**: The naive model was NOT being counted in the frontend (only 4 models visible instead of 5)

## Root Cause
In `/services/agent/hypermodel/model_config.json`, the last model entry was:
```json
{ "type": "base", "name": "base", "params": {}, "init_weight": 0.0 }
```

But frontend expected:
```javascript
export const KNOWN_MODELS = ["linear", "poly", "alphabeta", "kalman", "naive"];
```

## Changes Made

### 1. Backend Configuration
**File**: `/services/agent/hypermodel/model_config.json`
- Changed: `"type": "base", "name": "base"` 
- To: `"type": "naive", "name": "naive"`

### 2. Backend Model Code
**File**: `/services/agent/hypermodel/naive_model.py`
- Changed default parameter from `name: str = "base"` 
- To: `name: str = "naive"`

### 3. Frontend - LivePredictionChart
**File**: `/frontend/src/components/LivePredictionChart.jsx`
- Changed: `base: point.hyper_models?.base || null`
- To: `naive: point.hyper_models?.naive || null`

### 4. Frontend - WeightEvolutionChart
**File**: `/frontend/src/components/WeightEvolutionChart.jsx`
- Updated data processing: `weight_base` → `weight_naive`
- Updated models array: removed "base", added "naive"
- Updated gradient: `colorBase` → `colorNaive`, `MODEL_COLORS.base` → `MODEL_COLORS.naive`
- Updated AreaChart: `dataKey="weight_base"` → `dataKey="weight_naive"`

## Result
✅ **All 5 models now properly recognized**:
1. Linear
2. Polynomial
3. Alpha-Beta
4. Kalman
5. **Naive** (previously "base")

The "Complete Global Analysis - All Data" panel now correctly shows:
- **Modelos Activos: 5** (instead of 4)
- All 5 models in the distribution chart
- All 5 weight evolution traces

## Notes
- The frontend's `PredictionPanel.jsx` had a `displayModelName()` function mapping "base" → "naive" which is no longer needed but doesn't hurt
- All visualization components (AP1GlobalChart, CsvChart, etc.) will now correctly recognize the "naive" model name
