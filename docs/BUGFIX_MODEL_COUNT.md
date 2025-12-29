# Fix: Model Count Detection in PredictionPanel

## Problem
The **"Modelos Activos" (Active Models)** counter in **Complete Global Analysis - All Data** was showing **0 models** instead of the expected **5 models** (linear, poly, alphabeta, kalman, naive).

## Root Cause
The detection logic was incorrect in two ways:

### First Attempt (Wrong)
```javascript
// ❌ ATTEMPT 1: Looking for y_ prefix
if (k.startsWith("y_") && k !== "y_real") {
  const modelName = k.substring(2);
  if (ALL_MODELS.includes(modelName)) {
    modelKeys.add(modelName);
  }
}
```
Problem: The backend sends model data as **direct keys**, not as `y_` prefixed columns. The data structure from `/api/series` endpoint contains:
```json
{
  "var": 0.5,
  "prediction": 0.45,
  "kalman": 0.48,      // Direct key, NOT "y_kalman"
  "linear": 0.46,
  "poly": 0.47,
  "alphabeta": 0.49,
  "naive": 0.44
}
```

### Second Attempt (Also Wrong)
```javascript
// ❌ ATTEMPT 2: Looking for y_ prefix (still wrong)
// Same issue - models don't come with y_ prefix
```

## Correct Solution
Iterate through `ALL_MODELS` and check if each model has numeric data in the points:

```javascript
// ✅ CORRECT: Check for direct model keys
for (const modelName of ALL_MODELS) {
  for (const point of points) {
    // Models come as direct keys: kalman, linear, poly, alphabeta, naive
    if (typeof point[modelName] === "number") {
      modelKeys.add(modelName);
      break; // Model found, no need to check more points
    }
  }
}
```

Key improvements:
1. **Direct key lookup**: Models are accessed as `point["linear"]`, not `point["y_linear"]`
2. **Type validation**: Ensure the value is numeric
3. **Early break**: Once a model is found, skip to next model (optimization)
4. **Comprehensive**: Checks all known models from `ALL_MODELS` constant

## Impact
- **Before**: 0 models shown (completely broken detection)
- **After**: 5 models correctly detected and displayed

## Files Modified
- `frontend/src/components/PredictionPanel.jsx` (lines 189-224)

## Testing
- Verify the counter now shows 5 in "Modelos Activos"
- Ensure all 5 model names appear in the distribution chart
- Confirm confidence score calculation still works
- Check that data filtering by model still functions correctly

## Data Structure Reference
Backend `/api/series` endpoint returns points with this structure:
```javascript
{
  t: 1000000000,              // epoch ms
  timestamp: "2025-12-29...",
  var: 0.5,                   // observed value
  prediction: 0.45,           // ensemble prediction
  chosen_model: "linear",     // selected model
  kalman: 0.48,               // model predictions (DIRECT KEYS)
  linear: 0.46,
  poly: 0.47,
  alphabeta: 0.49,
  naive: 0.44,
  hyper_models: { ... }       // also available
}
```

