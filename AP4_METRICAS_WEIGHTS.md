# 🏆 ACTION POINT 4 – Tabla de Métricas con Weights y Top-3 Modelos

**Fecha:** 26 Noviembre 2025  
**Status:** ✅ IMPLEMENTADO

---

## 🎯 Objetivo

Enriquecer la tabla de métricas de modelos para incluir:
1. **Columna Weight**: Peso acumulado de cada modelo (desde AP3)
2. **Ordenamiento**: Ordenar por weight descendente (mejores primero)
3. **Top-3 Destacado**: Mostrar solo los 3 mejores modelos en la tabla principal
4. **Ranking Visual**: Usar emojis 🥇🥈🥉 para mostrar posiciones

---

## 📋 Requisitos Cumplidos

✅ **Backend `/api/metrics/models`**:
- Incluir weight actual en respuesta
- Obtener último valor de weight de InfluxDB
- Incluir en estructura JSON por modelo

✅ **Frontend `MetricsPanel`**:
- Nueva columna "Weight" en tabla
- Ordenamiento automático por weight descendente
- Mostrar solo top-3 en tabla principal
- Tabla adicional con todos los modelos (si hay > 3)

✅ **Discurso AP4**:
- "El agente no solo predice, también te dice qué modelos son candidatos"
- Ranking visual con medallas de oro/plata/bronce
- Explicación de cómo funcionan los pesos

---

## 🔧 Cambios Implementados

### 1. Backend: `services/orchestrator/app.py`

#### Cambio: Incluir pesos en `/api/metrics/models` (líneas 481-520)

**Antes:**
```python
result_overall[model] = {
    "mae": ...,
    "rmse": ...,
    "mape": ...,
    "n": ...
}
```

**Después:**
```python
# AP4: Query weights for each model
try:
    weights_by_model = _query_weights(id, start)
except Exception as e:
    logger.exception("Failed to query weights for AP4")
    weights_by_model = {}

# ... en el loop de cada modelo ...

# Get latest weight for this model
current_weight = None
if model in weights_by_model and weights_by_model[model]:
    current_weight = weights_by_model[model][-1]["weight"]

result_overall[model] = {
    "mae": ...,
    "rmse": ...,
    "mape": ...,
    "weight": current_weight,  # ← NUEVO
    "n": ...
}
```

**Respuesta JSON ahora:**
```json
{
  "id": "TestSeries",
  "overall": {
    "ab_fast": {
      "mae": 0.456,
      "rmse": 0.567,
      "mape": 0.123,
      "weight": 45.2,
      "n": 100
    },
    "linear_8": {
      "mae": 0.512,
      "rmse": 0.634,
      "mape": 0.156,
      "weight": -12.3,
      "n": 100
    },
    "poly2_12": {
      "mae": 0.489,
      "rmse": 0.598,
      "mape": 0.134,
      "weight": 8.1,
      "n": 100
    }
  },
  "daily": { ... }
}
```

---

### 2. Frontend: `frontend/src/components/MetricsPanel.jsx`

#### Cambios Principales:

**A) Nueva función `getTop3Models()`:**
```javascript
const getTop3Models = (modelsOverall) => {
  const modelArray = Object.entries(modelsOverall).map(([name, stats]) => ({
    name,
    ...stats
  }));
  
  // Ordenar por weight descendente
  modelArray.sort((a, b) => {
    const weightA = a.weight ?? -Infinity;
    const weightB = b.weight ?? -Infinity;
    return weightB - weightA;
  });
  
  // Retornar solo top-3
  return modelArray.slice(0, 3);
};
```

**B) Nueva sección "🏆 Top-3 Models":**
```jsx
<h4 className="metrics-subtitle">
  🏆 Top-3 Models (AP4 - Ranked by Weight)
</h4>
<table className="metrics-table--ap4">
  <thead>
    <tr>
      <th>Rank</th>
      <th>Model</th>
      <th>Weight</th>
      <th>MAE</th>
      <th>RMSE</th>
      <th>MAPE</th>
      <th>n</th>
    </tr>
  </thead>
  <tbody>
    {getTop3Models(models.overall).map((model, idx) => (
      <tr key={model.name} className={idx === 0 ? "metrics-row--best" : ""}>
        <td className="metrics-rank">
          {idx === 0 ? "🥇" : idx === 1 ? "🥈" : "🥉"}
        </td>
        <td className="metrics-model-name">{model.name}</td>
        <td className="metrics-weight">
          <strong>{model.weight?.toFixed(2) ?? "-"}</strong>
        </td>
        {/* ... resto de columnas ... */}
      </tr>
    ))}
  </tbody>
</table>
```

**C) Tabla adicional "All Models" (si hay > 3):**
- Mostrada solo si hay más de 3 modelos
- Ordenada también por weight descendente
- Permite ver ranking completo

---

### 3. Frontend: `frontend/src/components/MetricsPanel.css`

#### Nuevos Estilos:

```css
/* AP4: Estilos para tabla de top-3 modelos */
.metrics-table--ap4 {
  margin-top: 8px;
}

.metrics-table--ap4 thead {
  background-color: #f0f4f8;
}

.metrics-table--ap4 th {
  background-color: #e8f1ff;
  color: #1e40af;
  font-weight: 700;
}

.metrics-row--best {
  background-color: #fef3c7;  /* Destacado en amarillo */
}

.metrics-rank {
  text-align: center;
  font-size: 1rem;
}

.metrics-model-name {
  font-family: monospace;
  font-weight: 600;
}

.metrics-weight {
  color: #00a3ff;
  font-weight: 700;
  text-align: right;
}
```

---

## 📊 Flujo de Datos AP4

```
┌─────────────────────────────────────────────────────────┐
│ Frontend: "Load metrics" button                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ GET /api/metrics/models?id=TestSeries&start=-3d        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Backend: metrics_models()                               │
│  1. Query telemetry_models → per-model yhat           │
│  2. Query telemetry → var (observed)                   │
│  3. Calcular MAE, RMSE, MAPE por modelo               │
│  4. ❌ [NEW AP4] Query weights → weight actual        │
│  5. Retornar JSON con weight en cada modelo           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend: MetricsPanel recibe JSON                      │
│  1. Extrae models.overall                              │
│  2. ❌ [NEW AP4] Función getTop3Models()              │
│  3. Renderiza tabla con top-3 ordenados por weight    │
│  4. Si hay > 3: muestra tabla "All Models"            │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 Visualización

### Antes (Sin AP4):
```
Per-model (telemetry_models)
┌─────────────┬──────────┬──────────┬──────────┬────┐
│ Model       │ MAE      │ RMSE     │ MAPE     │ n  │
├─────────────┼──────────┼──────────┼──────────┼────┤
│ ab_fast     │ 0.456000 │ 0.567000 │ 0.123000 │100 │
│ linear_8    │ 0.512000 │ 0.634000 │ 0.156000 │100 │
│ poly2_12    │ 0.489000 │ 0.598000 │ 0.134000 │100 │
└─────────────┴──────────┴──────────┴──────────┴────┘
```

### Después (Con AP4):
```
🏆 Top-3 Models (AP4 - Ranked by Weight)
💡 Ordenados por weight descendente...

┌──────┬──────────────┬────────┬──────────┬──────────┬──────────┬────┐
│ Rank │ Model        │ Weight │ MAE      │ RMSE     │ MAPE     │ n  │
├──────┼──────────────┼────────┼──────────┼──────────┼──────────┼────┤
│ 🥇   │ ab_fast      │ 45.20  │ 0.456000 │ 0.567000 │ 0.123000 │100 │
│ 🥈   │ poly2_12     │  8.10  │ 0.489000 │ 0.598000 │ 0.134000 │100 │
│ 🥉   │ linear_8     │-12.30  │ 0.512000 │ 0.634000 │ 0.156000 │100 │
└──────┴──────────────┴────────┴──────────┴──────────┴──────────┴────┘

📊 All Models
(tabla con todos, también ordenados por weight)
```

---

## 💡 Discurso para Tesis

### AP4 - Selector Inteligente:

> "**El agente no solo realiza predicciones híbridas, sino que además proporciona un ranking de modelos basado en pesos acumulativos.**
>
> Como se observa en la tabla de métricas (AP4), el sistema:
>
> 1. **Calcula weights** (AP3): Acumula puntos según rendimiento relativo
> 2. **Ordena modelos**: Muestra top-3 con mayor weight en posición destacada
> 3. **Comunica confianza**: 🥇🥈🥉 indican qué modelos son más fiables
>
> Esto permite al usuario identificar rápidamente:
> - ¿Cuál es el mejor modelo para esta serie?
> - ¿Cuál es el peor?
> - ¿Cuál es el candidato alternativo?"

---

## ✅ Verificación de Implementación

### Checklist:

- [x] Backend `/api/metrics/models` devuelve weight
- [x] Weight es el último valor de InfluxDB.weights
- [x] Frontend `MetricsPanel` muestra tabla top-3
- [x] Tabla ordenada por weight descendente
- [x] Medallas 🥇🥈🥉 asignadas correctamente
- [x] Columna "Weight" visible y destacada (azul)
- [x] Tabla "All Models" mostrada si hay > 3
- [x] CSS con estilos AP4
- [x] Documentación creada

---

## 🚀 Cómo Probar AP4

### 1. Cargar datos:
```bash
1. Abre http://localhost:5173
2. Carga CSV: data/test_csvs/sine_300.csv
3. Click: "🚀 Ejecutar agente"
4. Espera 20 segundos
```

### 2. Ver AP4:
```bash
1. Selecciona "TestSeries"
2. Click: "Load metrics"
3. Desplázate hasta "🏆 Top-3 Models"
4. Verás tabla ordenada por weight
```

### 3. Verificar datos:
```bash
# En terminal:
curl "http://localhost:8081/api/metrics/models?id=TestSeries&start=-3d" | jq .overall
```

Deberías ver:
```json
{
  "ab_fast": {
    "mae": 0.456,
    "rmse": 0.567,
    "mape": 0.123,
    "weight": 45.2,
    "n": 100
  },
  ...
}
```

---

## 📈 Impacto

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Información mostrada** | MAE, RMSE, MAPE, n | + Weight |
| **Orden tabla** | Aleatorio | Descendente por weight |
| **Top modelos** | Todos mostrados | Top-3 destacado |
| **Claridad decisión** | Media | Alta (ranking claro) |
| **Insight usuario** | "¿Cuál es mejor?" | "Aquí está el ranking" |

---

## 📁 Archivos Modificados

✅ `services/orchestrator/app.py` (líneas 481-520)
- Agregar query de weights
- Incluir weight en respuesta

✅ `frontend/src/components/MetricsPanel.jsx` (completo)
- Nueva función getTop3Models()
- Nueva tabla "🏆 Top-3 Models"
- Nueva tabla "📊 All Models"

✅ `frontend/src/components/MetricsPanel.css`
- Estilos `.metrics-table--ap4`
- Estilos `.metrics-row--best`
- Estilos `.metrics-weight`

---

## 🎯 Relación con Otros APs

| AP | Descripción | Estado |
|----|-------------|--------|
| AP1 | Predicciones por modelo | ✅ Implementado |
| AP2 | Selector adaptativo | ✅ Implementado |
| AP3 | Evolución de pesos (ranking) | ✅ Implementado |
| **AP4** | **Tabla de métricas con weights** | **✅ NUEVO** |

---

**Status:** ✅ LISTO PARA USAR  
**Versión:** 1.0  
**Archivo:** AP4_METRICAS_WEIGHTS.md
