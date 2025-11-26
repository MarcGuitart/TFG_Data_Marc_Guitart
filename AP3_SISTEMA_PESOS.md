# AP3: Sistema de Pesos por Modelo (Sistema de Ranking)

## 📋 Descripción General

El **AP3** implementa un sistema de **puntos acumulativos con ranking** que permite evaluar el rendimiento histórico de cada modelo. A diferencia del AP2 (que elige el mejor modelo por instante), AP3 asigna **pesos crecientes o decrecientes** basados en el desempeño relativo.

## 🎯 Cómo Funciona

### Algoritmo de Actualización de Pesos (AP3)

En cada timestamp cuando llega un nuevo `y_t`:

1. **Penalización base**: Restar 1 punto a todos los modelos
2. **Ranking por error**: Ordenar modelos por error ascendente (mejor primero)
3. **Asignación de puntos**: 
   - Mejor modelo → M puntos (M = número de modelos)
   - Segundo mejor → M-1 puntos
   - ...
   - Peor modelo → 1 punto
4. **Acumulación**: Los pesos se van acumulando paso a paso
5. **Contraste real**: Los pesos pueden ser negativos, lo que demuestra claramente cuál modelo falla

### Ejemplo Numérico

Supongamos 3 modelos (linear_8, poly2_12, ab_fast) con pesos iniciales = 1.0

**Timestamp 1**: y_real = 5.0
- linear_8 predice 4.9 → error = 0.1
- poly2_12 predice 5.5 → error = 0.5
- ab_fast predice 5.0 → error = 0.0 ✓ (mejor)

Ranking: ab_fast (0.0) < linear_8 (0.1) < poly2_12 (0.5)

Cálculo de pesos:
```
Para todos: weights -= 1.0
  linear_8: 1.0 - 1.0 = 0.0
  poly2_12: 1.0 - 1.0 = 0.0
  ab_fast: 1.0 - 1.0 = 0.0

Puntos por ranking (M=3):
  ab_fast (rank 0): 0.0 + 3 = 3.0  ✓
  linear_8 (rank 1): 0.0 + 2 = 2.0
  poly2_12 (rank 2): 0.0 + 1 = 1.0
```

**Timestamp 2**: y_real = 6.0
- linear_8 predice 6.1 → error = 0.1
- poly2_12 predice 5.5 → error = 0.5
- ab_fast predice 5.8 → error = 0.2

Ranking: linear_8 (0.1) < ab_fast (0.2) < poly2_12 (0.5)

Cálculo de pesos (acumulativo):
```
Para todos: weights -= 1.0
  linear_8: 2.0 - 1.0 = 1.0
  poly2_12: 1.0 - 1.0 = 0.0
  ab_fast: 3.0 - 1.0 = 2.0

Puntos por ranking:
  linear_8 (rank 0): 1.0 + 3 = 4.0  ✓
  ab_fast (rank 1): 2.0 + 2 = 4.0
  poly2_12 (rank 2): 0.0 + 1 = 1.0
```

Con el tiempo, los modelos con mejor error acumulado tendrán pesos más altos.

## 🏗️ Cambios Implementados

### 1. Backend - Agent (`services/agent/hypermodel/hyper_model.py`)

```python
def update_weights(self, y_true: float):
    """AP3: Sistema de ranking con puntos"""
    
    # 1) Restar 1 a todos los pesos
    for name in self.w:
        self.w[name] -= 1.0
    
    # 2) Ordenar modelos por error ascendente
    ranked = sorted(errors.items(), key=lambda kv: kv[1])
    M = len(ranked)
    
    # 3) Asignar puntos: M al mejor, M-1 al segundo, ..., 1 al peor
    for rank, (name, _) in enumerate(ranked):
        reward = M - rank
        self.w[name] += reward
```

**Cambio clave**: Ahora los pesos se actualizan con un **ranking de puntos** en lugar de un promedio ponderado normalizado.

### 2. Backend - Agent (`services/agent/main.py`)

Ya enviaba `hyper_weights` en el mensaje enriquecido:
```python
enriched["hyper_weights"] = weights
```

### 3. Backend - Collector (`services/window_collector/main.py`)

Ya guardaba los weights en InfluxDB:
```python
Point("weights")
    .tag("id", unit)
    .tag("model", model_name)
    .field("weight", w)
    .time(tsc, WritePrecision.S)
```

### 4. Backend - Orchestrator (`services/orchestrator/app.py`)

**Nueva función `_query_weights()`**:
```python
def _query_weights(id_: str, start: str = "-7d"):
    """Query weights evolution from InfluxDB"""
    # Devuelve {model_name: [{time, weight}, ...], ...}
```

**Actualización de `/api/series`**:
- Consulta weights con `_query_weights()`
- Devuelve en el payload: `"weights": weights_by_model`

### 5. Frontend (`frontend/src/components/DataPipelineLiveViewer.jsx`)

**Nuevo panel "⚖️ Evolución de Pesos"**:
- Gráfico con evolución temporal de pesos para cada modelo
- Colores según modelo
- Información sobre el algoritmo del sistema de ranking
- Tabla con últimos pesos

## 📊 Flujo de Datos (AP3)

```
[CSV Upload] 
    ↓
[Frontend] → Kafka: telemetry.agent.in
    ↓
[Agent] 
  - Predice con todos los modelos
  - Calcula errores
  - UPDATE_WEIGHTS: ranking + puntos (AP3)
  - Envía: hyper_weights en mensaje enriquecido
    ↓
[Collector]
  - Lee hyper_weights
  - Escribe en InfluxDB measurement "weights"
    ↓
[InfluxDB]
  - Measurement: weights
  - Tags: id, model
  - Field: weight (float)
    ↓
[Orchestrator]
  - _query_weights(): consulta evolución
  - /api/series: devuelve "weights" en payload
    ↓
[Frontend]
  - Carga "weights"
  - Dibuja gráfico y tabla
```

## ✅ Verificación

### 1. Logs del Agente

Después de procesar datos, deberías ver en los logs:
```
[pred] id=TestSeries y=0.XXX y_hat=0.XXX buf=32 models=ab_fast,linear_8,poly2_12 chosen=linear_8
```

Los pesos se actualizan internamente pero no aparecen en los logs (se guardan en InfluxDB).

### 2. InfluxDB

Query para verificar weights:
```flux
from(bucket:"pipeline")
  |> range(start:-24h)
  |> filter(fn:(r)=> r._measurement=="weights")
  |> filter(fn:(r)=> r.id=="TestSeries")
```

Deberías ver puntos con:
- Tags: id, model
- Field: weight (valores crecientes/decrecientes)

### 3. API

```bash
curl http://localhost:8081/api/series?id=TestSeries&hours=24
```

En la respuesta, deberías ver:
```json
{
  "weights": {
    "linear_8": [
      {"time": "2025-11-26T18:30:00Z", "weight": 4.5},
      {"time": "2025-11-26T18:35:00Z", "weight": 6.2},
      ...
    ],
    "poly2_12": [...],
    "ab_fast": [...]
  }
}
```

### 4. Frontend

1. Abre http://localhost:5173
2. Carga CSV (sine_300.csv)
3. Ejecuta agente
4. Carga series
5. Debajo del selector adaptativo, verás: "⚖️ Evolución de Pesos (AP3)"
   - Gráfico con línea por modelo
   - Tabla con últimos pesos

## 🧪 Prueba Completa

1. **Preparar datos**:
   ```bash
   # Usar sine_300.csv que tiene 300 puntos
   ```

2. **Ejecutar pipeline**:
   - Frontend: Cargar CSV
   - Frontend: Click "Ejecutar agente"
   - Esperar 15 segundos

3. **Verificar en logs**:
   ```bash
   docker logs docker-agent-1 --tail 50 | grep "\[pred\]"
   ```

4. **Verificar InfluxDB**:
   ```bash
   docker exec docker-influxdb-1 influx query \
     'from(bucket:"pipeline") \
     |> range(start:-24h) \
     |> filter(fn:(r)=> r._measurement=="weights" and r.id=="TestSeries")'
   ```

5. **Ver en frontend**:
   - Ir a http://localhost:5173
   - Cargar series nuevamente
   - Ver panel "⚖️ Evolución de Pesos"

## 📈 Interpretación de Resultados

- **Pesos crecientes**: El modelo está mejorando
- **Pesos decrecientes**: El modelo está empeorando
- **Pesos negativos**: El modelo falla consistentemente (contraste real)
- **Líneas paralelas**: Los modelos tienen rendimiento similar
- **Divergencia**: Hay un ganador claro

Para tu tesis:
> "El sistema AP3 demuestra cómo los pesos acumulativos diferencian claramente el rendimiento relativo. Un modelo con pesos = 50.0 frente a otro con pesos = -10.0 muestra cómo el ranking acumula evidencia del desempeño histórico."

## 🎓 Conexión con Tesis

AP3 es el puente entre **observar predicciones individuales (AP1)** y **elegir dinámicamente (AP2)** hacia **cuantificar el rendimiento histórico (AP3)**.

Esto permite argumento como:
- "El sistema de pesos AP3 proporciona transparencia sobre qué modelo es más confiable"
- "La acumulación de puntos de ranking permite detectar cambios en patrones de datos"
- "Los pesos negativos crean contraste que facilita la toma de decisiones"
