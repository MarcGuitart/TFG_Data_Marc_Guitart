# 🚀 RESUMEN INTEGRAL - AP1, AP2, AP3, AP4

**Fecha:** 26 Noviembre 2025  
**Status:** ✅ TODOS LOS APS IMPLEMENTADOS

---

## 📊 Tabla Resumen de Action Points

| AP | Nombre | Descripción | Estado |
|----|--------|-------------|--------|
| **AP1** | Predicciones por Modelo | Visualizar predicciones individuales de cada modelo | ✅ |
| **AP2** | Selector Adaptativo | Elegir automáticamente el mejor modelo por timestamp | ✅ |
| **AP3** | Evolución de Pesos | Ranking acumulativo basado en performance | ✅ |
| **AP4** | Tabla de Métricas | Top-3 modelos con weights integrados | ✅ |

---

## 🏗️ Arquitectura General

```
┌──────────────────────────────────────────────────────────┐
│                        FRONTEND                          │
│                   (React + Vite)                         │
│                                                          │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  AP1: Gráficos │  │ AP2: Tabla  │  │ AP3: Pesos  │  │
│  │   Individuales │  │  Selector   │  │  Evolución  │  │
│  │                │  │  Adaptativo │  │             │  │
│  └────────────────┘  └─────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ AP4: Tabla de Métricas (Top-3 + Weights)        │   │
│  │  🏆 Modelo 1 | Weight: 45.2  | MAE: 0.456       │   │
│  │  🥈 Modelo 2 | Weight: 8.1   | MAE: 0.489       │   │
│  │  🥉 Modelo 3 | Weight: -12.3 | MAE: 0.512       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
           ↓ fetch /api/series, /api/metrics/models
┌──────────────────────────────────────────────────────────┐
│                      BACKEND                            │
│                  (FastAPI)                              │
│                                                          │
│  /api/series → {observed, predicted, models, chosen,    │
│               weights}                                  │
│                                                          │
│  /api/metrics/models → {mae, rmse, mape, weight}       │
└──────────────────────────────────────────────────────────┘
           ↓ query InfluxDB
┌──────────────────────────────────────────────────────────┐
│                    INFLUXDB                             │
│                                                          │
│  • telemetry (observed var + hybrid prediction)         │
│  • telemetry_models (per-model predictions)             │
│  • chosen_model (AP2: modelo elegido)                   │
│  • weights (AP3: pesos acumulativos)                    │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 Descripción Detallada de Cada AP

### 🎯 AP1: Predicciones por Modelo

**Objetivo:** Mostrar predicciones individuales de cada modelo lado a lado

**Localización:**
- Frontend: `DataPipelineLiveViewer.jsx` - Sección "📈 Vista Individual por Modelo"
- Backend: `/api/series` devuelve `yhat_by_model`

**Flujo:**
1. User selecciona una serie (TestSeries)
2. Frontend solicita `/api/series?id=TestSeries`
3. Backend retorna predicciones de cada modelo
4. Frontend renderiza gráficos individuales:
   - Eje X: Timestamp
   - Eje Y: Valor predicho por modelo
   - Comparación: Real (azul) vs Modelo (color específico)

**Modelos mostrados:**
- `ab_fast` (verde)
- `linear_8` (índigo)
- `poly2_12` (rosa)
- Otros según disponibles

**Cálculo:** Directo de InfluxDB measurement `telemetry_models`

---

### 🎯 AP2: Selector Adaptativo

**Objetivo:** Mostrar qué modelo fue elegido en cada timestamp

**Localización:**
- Frontend: `DataPipelineLiveViewer.jsx` - Sección "🎯 Selector Adaptativo"
- Backend: `/api/series` devuelve `chosen_model`
- Lógica: `services/agent/main.py` → `apply_selector()`

**Flujo:**
1. Agent ejecuta en cada timestamp:
   ```python
   errors = {model: abs(error) for model, error in model_predictions}
   best_model = min(errors, key=errors.get)
   # Guardar en InfluxDB
   ```

2. Frontend muestra tabla:
   | Timestamp | Modelo Elegido |
   |-----------|----------------|
   | 2025-11-26 10:30:00 | ab_fast |
   | 2025-11-26 10:30:01 | poly2_12 |

**Criterio:** Menor error absoluto en ese instante

**Insight:** "El agente elige dinámicamente el mejor modelo momento a momento"

---

### 🎯 AP3: Evolución de Pesos (Ranking)

**Objetivo:** Acumular score para cada modelo basado en su performance

**Localización:**
- Backend: `services/agent/hypermodel/hyper_model.py` → `update_weights()`
- Almacenamiento: InfluxDB measurement `weights`

**Algoritmo:**
```python
# 1. Penalización base
for model in models:
    weights[model] -= 1.0

# 2. Ranking por error
ranked = sorted(models.items(), key=lambda kv: kv[1])  # ascendente error

# 3. Reward por posición
M = len(ranked)
for rank, (model, error) in enumerate(ranked):
    reward = M - rank  # M puntos al mejor, 1 al peor
    weights[model] += reward
```

**Ejemplo con 3 modelos:**
- Timestamp T1: Errors = [ab_fast: 0.1, linear_8: 0.3, poly2_12: 0.2]
  - Ranking: ab_fast (1º), poly2_12 (2º), linear_8 (3º)
  - Rewards: ab_fast +3, poly2_12 +2, linear_8 +1
  - Penalización: todos -1
  - Net: ab_fast +2, poly2_12 +1, linear_8 0
  
**Visualización:**
- Gráfico de líneas: Evolución temporal de weights
- Eje X: Timestamp
- Eje Y: Peso acumulado
- Línea por modelo

**Insight:** "Los pesos muestran consistencia del modelo a largo plazo"

---

### 🎯 AP4: Tabla de Métricas con Weights

**Objetivo:** Mostrar ranking de modelos con métricas + weight actual

**Localización:**
- Frontend: `MetricsPanel.jsx` - Sección "🏆 Top-3 Models"
- Backend: `/api/metrics/models` incluye weight
- Datos: Últimos 3 días de datos

**Estructura Tabla (Top-3):**
```
┌──────┬──────────┬─────────┬──────────┬──────────┬────┐
│ Rank │ Model    │ Weight  │ MAE      │ RMSE     │ n  │
├──────┼──────────┼─────────┼──────────┼──────────┼────┤
│ 🥇   │ ab_fast  │  45.2   │ 0.456000 │ 0.567000 │100 │
│ 🥈   │ poly2_12 │   8.1   │ 0.489000 │ 0.598000 │100 │
│ 🥉   │ linear_8 │ -12.3   │ 0.512000 │ 0.634000 │100 │
└──────┴──────────┴─────────┴──────────┴──────────┴────┘
```

**Columnas:**
- **Rank**: 🥇🥈🥉 (posición)
- **Model**: Nombre del modelo
- **Weight**: Valor acumulado desde AP3 (último valor)
- **MAE**: Error Medio Absoluto (últimos 3 días)
- **RMSE**: Error Cuadrático Medio
- **n**: Número de predicciones

**Orden:** Descendente por weight (mejores primero)

**Características:**
- Si hay > 3 modelos: tabla adicional "All Models" con ranking completo
- Fondo amarillo para ganador (🥇)
- Color azul para columna Weight
- Monospace para nombres

**Cálculo:**
1. Query InfluxDB `telemetry_models` → per-model MAE/RMSE/MAPE
2. Query InfluxDB `weights` → obtener último weight por modelo
3. Combinar en respuesta JSON
4. Frontend ordena y renderiza

---

## 🔄 Flujo Integrado: AP1 → AP2 → AP3 → AP4

```
Timestamp T → Model Predictions (AP1)
   ↓
Apply Selector (AP2) → Choose Best
   ↓
Update Weights (AP3) → Accumulate Score
   ↓
Show Ranking (AP4) → Display Top-3
```

### Ejemplo Práctico:

**Datos de entrada (AP1):**
```
T=10:30:00
  ab_fast: yhat=10.2, error=0.1
  linear_8: yhat=9.8, error=0.5
  poly2_12: yhat=10.1, error=0.2
  Real: 10.3
```

**AP2 Decision:**
```
Best model = ab_fast (error 0.1 < otros)
Guardar: chosen_model = "ab_fast"
```

**AP3 Weights Update:**
```
Ranking:
  1º: ab_fast (error 0.1)
  2º: poly2_12 (error 0.2)
  3º: linear_8 (error 0.5)

Rewards:
  ab_fast: -1 + 3 = +2
  poly2_12: -1 + 2 = +1
  linear_8: -1 + 1 = 0

New Weights:
  ab_fast: 45.2 + 2 = 47.2
  poly2_12: 8.1 + 1 = 9.1
  linear_8: -12.3 + 0 = -12.3
```

**AP4 Display (después de 100 timestamps):**
```
🏆 ab_fast | Weight: 47.2 | MAE: 0.456
🥈 poly2_12 | Weight: 9.1 | MAE: 0.489
🥉 linear_8 | Weight: -12.3 | MAE: 0.512
```

---

## 📊 Almacenamiento en InfluxDB

### Measurement: `telemetry`
```
timestamp | id | var | prediction | _measurement | _field
2025-11-26T10:30:00Z | TestSeries | 10.3 | 10.15 | telemetry | var
2025-11-26T10:30:00Z | TestSeries | 10.3 | 10.15 | telemetry | prediction
```

### Measurement: `telemetry_models`
```
timestamp | id | model | yhat | _measurement | _field
2025-11-26T10:30:00Z | TestSeries | ab_fast | 10.2 | telemetry_models | yhat
2025-11-26T10:30:00Z | TestSeries | linear_8 | 9.8 | telemetry_models | yhat
2025-11-26T10:30:00Z | TestSeries | poly2_12 | 10.1 | telemetry_models | yhat
```

### Measurement: `chosen_model` (AP2)
```
timestamp | id | model | _measurement | _field
2025-11-26T10:30:00Z | TestSeries | ab_fast | chosen_model | model
```

### Measurement: `weights` (AP3/AP4)
```
timestamp | id | model | weight | _measurement | _field
2025-11-26T10:30:00Z | TestSeries | ab_fast | 47.2 | weights | weight
2025-11-26T10:30:00Z | TestSeries | linear_8 | -12.3 | weights | weight
2025-11-26T10:30:00Z | TestSeries | poly2_12 | 9.1 | weights | weight
```

---

## 📁 Archivos Clave

| Componente | Archivo | Función |
|-----------|---------|---------|
| **Backend - Selector** | `services/agent/main.py` | Elegir mejor modelo (AP2) |
| **Backend - Weights** | `services/agent/hypermodel/hyper_model.py` | Actualizar pesos (AP3) |
| **Backend - API Series** | `services/orchestrator/app.py` | GET /api/series (AP1,AP2,AP3) |
| **Backend - API Metrics** | `services/orchestrator/app.py` | GET /api/metrics/models (AP4) |
| **Frontend - Visualización** | `frontend/src/components/DataPipelineLiveViewer.jsx` | Gráficos (AP1,AP2,AP3) |
| **Frontend - Métricas** | `frontend/src/components/MetricsPanel.jsx` | Tabla top-3 (AP4) |
| **Base Datos** | `docker/docker-compose.yml` | InfluxDB + Kafka |

---

## 💾 Endpoints Utilizados

| Endpoint | Propósito | APs |
|----------|-----------|-----|
| `GET /api/series?id=X` | Obtener series de predicciones | AP1,AP2,AP3 |
| `GET /api/metrics/models?id=X` | Obtener métricas con weights | AP4 |
| `POST /api/upload_csv` | Subir datos para procesar | General |

---

## 🎯 Insights Clave para Tesis

### Narrativa General:
> "El agente implementa un sistema adaptativo de selección de modelos de predicción que combina:
>
> 1. **Múltiples modelos** (AP1): Se generan predicciones independientes
> 2. **Selector dinámico** (AP2): Elige el mejor modelo momento a momento
> 3. **Ranking histórico** (AP3): Acumula puntos para medir confiabilidad
> 4. **Recomendador** (AP4): Muestra top-3 modelos para decisiones futuras"

### AP1 Insight:
- Permite visualizar qué modelo predice mejor en qué situación
- Útil para debugging y comprensión del comportamiento

### AP2 Insight:
- La selección adaptativa es más eficaz que usar un modelo fijo
- Demuestra capacidad de aprendizaje online del sistema

### AP3 Insight:
- Los pesos acumulativos capturan tendencias a largo plazo
- Identifican modelos consistentemente buenos vs. inconsistentes

### AP4 Insight:
- El ranking permite tomar decisiones basadas en datos
- Los usuarios pueden confiar en los modelos top-3 para nuevas predicciones
- Comunicación clara del agente: "estos son los mejores"

---

## ✅ Checklist de Validación

- [x] AP1: Gráficos individuales por modelo
- [x] AP2: Tabla selector adaptativo con timestamps
- [x] AP3: Gráfico evolución de pesos con líneas por modelo
- [x] AP4: Tabla top-3 con weights ordenados descendentemente
- [x] Backend incluye pesos en `/api/metrics/models`
- [x] Frontend calcula ordenamiento y top-3
- [x] CSS con estilos diferenciados (medallas, colores)
- [x] InfluxDB almacena todos los datos
- [x] Docker: todos servicios levantados
- [x] Documentación completa

---

## 🚀 Cómo Usar el Sistema Completo

```bash
# 1. Asegurar que Docker está corriendo
docker ps

# 2. Abrir frontend
http://localhost:5173

# 3. Cargar CSV
Upload: data/test_csvs/sine_300.csv

# 4. Ejecutar agente
Click: "🚀 Ejecutar agente"

# 5. Ver resultados

# AP1: Gráficos individuales
→ "Vista Individual por Modelo"

# AP2: Selector
→ "Selector Adaptativo - Modelo Elegido"

# AP3: Evolución de pesos
→ "Evolución de Pesos (AP3)"

# AP4: Tabla de métricas
→ "Load metrics"
→ "🏆 Top-3 Models (AP4)"
```

---

**Status:** ✅ SISTEMA COMPLETO Y FUNCIONAL  
**Versión:** 1.0  
**Documentación:** AP1_AP2_AP3_AP4_INTEGRAL.md
