# No Persistence in AI Analysis Endpoints: Streaming Responses Only

## Problema Identificado

**Síntesis:** Los endpoints de análisis con IA (Groq) retornan respuestas directamente al cliente sin persistencia en base de datos. El análisis es **ephemeral** (en memoria), no almacenado.

**Ubicación:** `/services/orchestrator/app.py`, líneas 1474-1920

**Impacto:** 
- ✓ Análisis en tiempo real sin latencia de escritura a BD
- ✗ Sin caché de análisis anteriores
- ✗ Cada petición regenera análisis (costo de API Groq repetido)
- ✗ Sin auditoría histórica de análisis realizados

---

## Zona 1: Endpoint de Análisis Simple (Sin Persistencia) ✗

### Ubicación: POST /api/analyze_report/{id}
**Archivo:** `/services/orchestrator/app.py`  
**Rango:** Líneas 1474-1720

### Flujo de Ejecución

#### Línea 1474-1476: Decorador y Firma
```python
@app.post("/api/analyze_report/{id}")
async def analyze_report(id: str):
    """
    Analiza el reporte exportado usando IA (Groq) con acceso completo al CSV
    para proporcionar un análisis profundo y accionable.
    """
```

**Observación:** Decorador describe lo que HACE (analiza), NO lo que PERSISTE.

---

#### Líneas 1481-1490: Inicialización (SIN write_api)
```python
try:
    from groq import Groq
    import csv
    import os
    
    # Configurar Groq API
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise HTTPException(
            status_code=500, 
            detail="GROQ_API_KEY not configured..."
        )
```

**Observación:** 
- ✗ **NO se importa InfluxDBClient**
- ✗ **NO se inicializa write_api**
- ✗ **Únicas importaciones:** Groq, csv, os

---

#### Líneas 1495-1510: Lectura de CSV (Input)
```python
# Leer el CSV exportado completo
csv_path = f"/app/data/weights_history_{id}.csv"

if not os.path.exists(csv_path):
    raise HTTPException(
        status_code=404,
        detail=f"No export found for series '{id}'..."
    )

# Leer CSV y extraer información clave
csv_data = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    csv_data = list(reader)
```

**Patrón:** Lee datos del filesystem (entrada), NO escribe a BD.

---

#### Líneas 1512-1605: Procesamiento de Datos
```python
# Analizar estructura de datos
total_points = len(csv_data)
first_row = csv_data[0]
last_row = csv_data[-1]

# Extraer columnas de modelos (weight_*)
model_names = [col.replace('weight_', '') for col in first_row.keys() 
               if col.startswith('weight_')]

# Calcular estadísticas finales de cada modelo
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
```

**Crítico:** 
- ✗ **Calcula estadísticas en memoria** (Python dictionaries, lists)
- ✗ **NO crea Point() de InfluxDB**
- ✗ **NO invoca write_api()**
- ✗ **Datos permanecen SOLO en memoria local**

---

#### Líneas 1685-1700: Llamada a Groq API
```python
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

prompt = f"""You are an expert analyst in adaptive prediction systems..."""

# Llamar a Groq API
client = Groq(api_key=api_key)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are an expert data scientist..."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=3000,
    temperature=0.6,
)

analysis = response.choices[0].message.content
```

**Observación:**
- ✓ Llama a Groq API
- ✓ Obtiene análisis completo en `analysis` variable
- ✗ **NO guarda análisis en ningún lado**

---

#### Líneas 1702-1709: Retorno (SIN Persistencia)
```python
return {
    "success": True,
    "analysis": analysis,              # ← Texto de Groq retornado al cliente
    "series_id": id,
    "total_points": total_points,
    "ensemble_mae": round(ensemble_mae, 6),
    "model_stats": model_stats,
    "timestamp": datetime.utcnow().isoformat()
}
```

**Crítico:**
- ✓ Respuesta JSON retornada al cliente HTTP
- ✗ **NINGÚN campo persiste a InfluxDB**
- ✗ **NINGUNA escritura a base de datos**
- ✗ Timestamp registra CUÁNDO se ejecutó, NO el análisis
- ✗ Campo `analysis` es **ephemeral** (existe solo en respuesta HTTP)

---

## Zona 2: Prueba Definitiva de No-Persistencia

### Búsqueda de Patrones de Escritura en app.py

**Búsqueda realizada:** `_write_api|write_api\(\)|Point\(`

**Resultado en endpoint /api/analyze_report:**
```
✗ NO hay _write_api.write()
✗ NO hay write_api() llamado
✗ NO hay Point() creado
✗ NO hay influx_client.write_api() inicializado
✗ NO hay write(bucket=..., record=...) invocado
```

**Contraste con inicialización global (Línea 23):**
```python
_metrics_q = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG).query_api()
```

**Observación crítica:** 
- ✓ Se inicializa SOLO `query_api()` (LECTURA)
- ✗ Nunca se inicializa `write_api()` (ESCRITURA)
- ✗ Orchestrator es servicio de **análisis/lectura**, no de persistencia

---

### Comparación: Cómo se VERÍA si persistiera

**Patrón de escritura a InfluxDB (No presente en analyze_report):**

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Inicializar write_api
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_type=SYNCHRONOUS)

# Crear punto con análisis
point = Point("analysis_results") \
    .tag("series_id", id) \
    .field("ensemble_mae", ensemble_mae) \
    .field("ensemble_mape", ensemble_mape) \
    .field("analysis_text", analysis)  # Guardar análisis \
    .time(datetime.utcnow())

# Escribir a InfluxDB
write_api.write(bucket=INFLUX_BUCKET, record=point)  # ← NO ESTÁ EN analyze_report()
```

**Verificación en código:** Esta línea NO existe en `/api/analyze_report/{id}`.

---

## Zona 3: Segundo Endpoint de Análisis (MISMO PATRÓN)

### POST /api/analyze_report_advanced/{id}
**Archivo:** `/services/orchestrator/app.py`  
**Rango:** Líneas 1721-1920

### Flujo Idéntico (Sin Persistencia)

#### Línea 1883-1896: Llamada a Groq
```python
# ===== Llamar a Groq API =====
client = Groq(api_key=api_key)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {
            "role": "system",
            "content": "You are an expert data scientist in time series forecasting..."
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
```

**Observación:** Idéntico a primer endpoint - Groq sin persistencia.

---

#### Línea 1899-1908: Retorno (SIN Persistencia)
```python
return {
    "success": True,
    "analysis": analysis,                        # ← SOLO retornado, NO persistido
    "series_id": id,
    "analysis_type": "advanced",
    "pipeline_points": len(points),
    "export_file": export_filename if export_report_csv else None,
    "timestamp": datetime.utcnow().isoformat()
}
```

**Crítico:**
- ✓ Respuesta JSON retornada al cliente
- ✗ **Campo `analysis` es ephemeral**
- ✗ **NO se guarda en base de datos**
- ✗ Próxima llamada regenerará análisis (Groq API llamado de nuevo)

---

## Zona 4: Implicaciones de No-Persistencia

### Tabla de Consecuencias

| Aspecto | Consecuencia |
|---|---|
| **Cada petición** | Regenera análisis (costo Groq repetido) |
| **Sin caché** | Primera llamada = Segunda llamada en costo |
| **Sin auditoría** | No hay registro de análisis históricos |
| **Reproducibilidad** | Resultado puede variar (temperature=0.7) |
| **Escalabilidad** | Múltiples usuarios = Múltiples llamadas a Groq |
| **Costo financiero** | Groq API call por usuario por serie por sesión |

---

### Cálculo de Costo Groq

**Modelo:** llama-3.3-70b-versatile (endpoint `/api/analyze_report_advanced`)

**Token usage:**
- Input: ~4000 tokens (contexto completo)
- Output: ~4000 tokens (max_tokens=4000)
- **Total por call:** ~8000 tokens

**Precio Groq (aproximado):** $0.00027 / 1M input tokens

**Costo por análisis:** $0.002 (sin caché)

**Impacto:** 100 usuarios × 5 series × 2 sesiones = **1000 análisis = $2 por día**

---

## Zona 5: Evidencia de Falta de Persistencia en Handlers

### Estructura de try-except (Sin captura de escritura fallida)

```python
try:
    from groq import Groq
    import csv
    import os
    
    # ... procesamiento sin persistencia ...
    
    analysis = response.choices[0].message.content
    
    return {
        "success": True,
        "analysis": analysis,
        # ... otros campos ephemeral ...
    }
    
except FileNotFoundError:
    raise HTTPException(...)
except Exception as e:
    logger.error(f"Error in AI analysis: {e}")
    raise HTTPException(...)
```

**Observación:**
- ✗ No hay try-except para operación de escritura a BD
- ✗ No hay logger para operación de persistencia
- ✗ No hay validación de write_api().write()
- ✓ Solo hay try-except para lectura de CSV y Groq API

---

## Zona 6: Comparación con Otros Endpoints que SÍ Persisten

### Patrón en window_collector/main.py (SÍ persiste)

**Archivo:** `/services/window_collector/main.py`

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

write_api = client.write_api(write_type=SYNCHRONOUS)

# Crear puntos
point = Point("telemetry_models") \
    .tag("id", msg['id']) \
    .field("yhat_linear", predictions.get('linear', 0.0)) \
    .field("yhat_poly", predictions.get('poly', 0.0)) \
    .time(ts)

# ESCRIBIR a InfluxDB
write_api.write(bucket=INFLUX_BUCKET, record=point)  # ← Ejemplo de persistencia real
```

**Diferencia clave:**
- window_collector: Crea Point() → write_api.write() → Datos persisten en InfluxDB
- orchestrator /analyze_report: Calcula estadísticas → Groq API → Retorna JSON (NO persiste)

---

## Zona 7: Matriz de Endpoints (Persistencia vs No-Persistencia)

| Endpoint | Servicio | Lectura | Persistencia | Groq? | Ephemeral? |
|---|---|---|---|---|---|
| POST /api/upload_csv | orchestrator | ✓ CSV | ✓ InfluxDB (via agent) | ✗ | ✗ |
| POST /api/run_window | orchestrator | ✓ InfluxDB | ✓ Kafka | ✗ | ✗ |
| GET /api/series | orchestrator | ✓ InfluxDB | ✗ | ✗ | ✗ |
| **POST /api/analyze_report** | **orchestrator** | **✓ CSV** | **✗ NUNCA** | **✓** | **✓** |
| **POST /api/analyze_report_advanced** | **orchestrator** | **✓ InfluxDB+CSV** | **✗ NUNCA** | **✓** | **✓** |
| POST /api/reset_system | orchestrator | ✗ | ✓ Delete InfluxDB | ✗ | ✗ |

**Observación:** 2 de N endpoints (análisis) son **intencionalmente** sin persistencia.

---

## Zona 8: Diseño Intencional o Accidental?

### Evidencia de Diseño Intencional

1. **Descripción en docstring (línea 1475):**
   ```python
   """
   Analiza el reporte exportado usando IA (Groq) con acceso completo al CSV
   para proporcionar un análisis profundo y accionable.
   """
   ```
   Dice "analiza" (acción), no "persiste análisis" (intención ausente).

2. **Patrón de Groq API en respuesta:**
   ```python
   analysis = response.choices[0].message.content
   return {"analysis": analysis, ...}
   ```
   Devuelve análisis directamente sin intermediación de BD.

3. **Ausencia de write_api en todo app.py:**
   Orchestrator NUNCA inicializa write_api, solo query_api.

4. **Patrón en segundo endpoint (idéntico):**
   Ambos endpoints siguen mismo patrón → Consistencia intencional.

### Conclusión
**Diseño intencional:** Los análisis son servicios **stateless** de streaming, no almacenamiento de análisis.

---

## Síntesis para Tesis

### Arquitectura de No-Persistencia

**Endpoints analíticos:**
```
Frontend (POST /api/analyze_report/{id})
    ↓
Orchestrator (servicio stateless)
    ├─ Lee: CSV exportado (/app/data/) + InfluxDB (para advanced)
    ├─ Procesa: Estadísticas en memoria
    ├─ Llama: Groq API (generación de análisis)
    ├─ Retorna: JSON con análisis al cliente
    └─ Persiste: ❌ NUNCA (no hay write_api)
```

### Localización Exacta
| Zona | Archivo | Líneas | Problema |
|---|---|---|---|
| **Endpoint simple** | app.py | 1474-1720 | Sin persistencia |
| **Endpoint advanced** | app.py | 1721-1920 | Sin persistencia |
| **Inicialización InfluxDB** | app.py | línea 23 | Solo query_api() |
| **Búsqueda write_api** | app.py | Global | ✗ NO existe |

### Garantías de No-Persistencia

1. ✗ **NO hay Point() creado** con análisis
2. ✗ **NO hay write_api.write() invocado**
3. ✗ **NO hay logger.info("Analysis persisted...")** 
4. ✗ **NO hay try-except para persistencia fallida**
5. ✓ **SÍ hay return JSON directo** al cliente

### Consecuencias Documentadas
- **Ventaja:** Análisis en tiempo real sin latencia de BD
- **Desventaja:** Sin caché, sin auditoría, costo Groq por petición
- **Caso de uso:** Análisis ephemeral para exploración interactiva

---

## Referencias de Código

### Endpoints de Análisis (Sin Persistencia)
1. `POST /api/analyze_report/{id}` - Líneas 1474-1720
2. `POST /api/analyze_report_advanced/{id}` - Líneas 1721-1920

### Cliente InfluxDB (Solo lectura)
- Línea 23: `_metrics_q = InfluxDBClient(...).query_api()`

### Archivos Relacionados
- `/services/orchestrator/app.py` - Servicio orquestador (analítica)
- `/services/window_collector/main.py` - Persistencia real (referencia)
- `/frontend/src/components/AnalysisModal.jsx` - Frontend llamador

---

**Conclusión:** Endpoints de análisis implementan arquitectura **streaming ephemeral** con respuestas directas, sin persistencia en base de datos. Decisión arquitectónica intencional para servicio stateless de analítica en tiempo real.
