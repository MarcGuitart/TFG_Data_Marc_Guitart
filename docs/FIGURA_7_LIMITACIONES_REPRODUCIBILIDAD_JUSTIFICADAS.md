# Limitaciones de Reproducibilidad: Evidencia Técnica Agregada

## Resumen Ejecutivo

Este documento justifica dos limitaciones clave de reproducibilidad en el sistema TFG:

1. **Frontend API Base URL Inconsistency** - Despliegue no-reproducible sin recompilación
2. **Analysis Streaming Without Persistence** - Análisis ephemeral sin caché/auditoría

---

## Hallazgo 1: Frontend URL Configuration Inconsistency

### Problema
Frontend implementa **dos estrategias incompatibles** para resolver URL base de API:
- **Patrón A (3 componentes):** Respetan `VITE_API_BASE` + fallback
- **Patrón B (4 componentes):** Hardcodean `http://localhost:8081` sin sobrescritura

### Localización

#### Componentes CON Flexibilidad (Env-Based) ✓
| Componente | Archivo | Línea | Implementación | #Endpoints |
|---|---|---|---|---|
| ControlHeader | ControlHeader.jsx | 22 | `import.meta.env.VITE_API_BASE \| "http://localhost:8081"` | 4 (líneas 50, 76, 130, 171) |
| AnalysisModal | AnalysisModal.jsx | 21 | `import.meta.env.VITE_API_BASE \| "http://localhost:8081"` | 2 (líneas 85, 158) |
| LivePredictionChart | LivePredictionChart.jsx | 16 | `import.meta.env.VITE_API_BASE \| "http://localhost:8081"` | 1 (línea 61) |

**Total:** 7 endpoints configurables mediante VITE_API_BASE

#### Componentes SIN Flexibilidad (Hardcoded) ✗
| Componente | Archivo | Línea | Implementación | #Endpoints |
|---|---|---|---|---|
| PredictionPanel | PredictionPanel.jsx | 22 | `"http://localhost:8081"` | 5 (líneas 88, 108, 169, 187, 201) |
| DataPipelineLiveViewer | DataPipelineLiveViewer.jsx | 9 | `"http://localhost:8081"` | 6 (líneas 93, 104, 142, 154, 181, 182) |
| AP3WeightsPanel | AP3WeightsPanel.jsx | 8 | `"http://localhost:8081"` | 3 (líneas 49, 50, 119) |
| KafkaOutPanel | KafkaOutPanel.jsx | 9 | `'http://localhost:8082/flush'` (inline) | 1 (línea 9) |

**Total:** 15 endpoints NO configurables (hardcoded, requieren recompilación)

### Impacto Documentado

#### Desarrollo Local ✓
```bash
npm run dev
# Funciona: Orchestrator en localhost:8081
# Resultado: 7/7 componentes funcionan
```

#### Producción con URL Diferente ❌
```bash
VITE_API_BASE=https://api.prod.com npm run build
# Resultado:
# ✓ ControlHeader, AnalysisModal, LivePredictionChart → https://api.prod.com
# ✗ PredictionPanel, DataPipelineLiveViewer, AP3WeightsPanel → http://localhost:8081 (ignoran env)
# ✗ KafkaOutPanel → http://localhost:8082 (hardcodeado)
```

#### Kubernetes / Cloud ❌
```yaml
env:
  - name: VITE_API_BASE
    value: "https://api.prod.k8s.internal"
# Resultado: Sistema parcialmente configurable → FALLA PARCIAL
```

### Raíz del Problema
1. **Sin estándar documentado** - 7 archivos, 2 patrones diferentes
2. **Sin enforce mecánico** - No hay ESLint rule rechazando hardcoded `localhost`
3. **Sin centralización** - Cada componente define su `API_BASE` por separado
4. **Documentación ausente** - No existe `.env.example` o guía de variables

### Evidencia de Inconsistencia

**Búsqueda en codebase:**
```
frontend/src/components/ → 7 componentes con definición de API_BASE
- 3 usan: import.meta.env.VITE_API_BASE || fallback
- 4 usan: "http://localhost:8081" hardcoded
- 1 usa: 'http://localhost:8082' inline (caso especial Kafka)
```

**Patrón correcto existe pero se ignora:**
```jsx
// 3 componentes: Patrón CORRECTO
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

// 4 componentes: Patrón INCORRECTO (mismo código pero sin variable)
const API_BASE = "http://localhost:8081";
```

---

## Hallazgo 2: Analysis Endpoints - Streaming Without Persistence

### Problema
Endpoints de análisis con IA (`/api/analyze_report*`) retornan respuestas directamente al cliente **sin persistencia en base de datos**. El análisis es **ephemeral** (existe solo en respuesta HTTP).

### Localización

#### Endpoint 1: POST /api/analyze_report/{id}
**Archivo:** `/services/orchestrator/app.py`  
**Rango:** Líneas 1474-1720

#### Endpoint 2: POST /api/analyze_report_advanced/{id}
**Archivo:** `/services/orchestrator/app.py`  
**Rango:** Líneas 1721-1920

### Flujo sin Persistencia

```
1. Frontend POST /api/analyze_report/{id}
   ↓
2. Orchestrator read CSV + InfluxDB (entrada)
   ↓
3. Procesamient estadístico en memoria (Python dicts/lists)
   ↓
4. Llamada a Groq API (llama-3.3-70b-versatile)
   ↓
5. Obtener análisis: analysis = response.choices[0].message.content
   ↓
6. Return JSON con análisis al cliente
   ↓
7. ✗ NO hay write_api.write() a InfluxDB
   ✗ NO hay Point() creado
   ✗ NO hay persistencia de análisis
```

### Prueba de No-Persistencia

#### Búsqueda en /services/orchestrator/app.py
```
grep: _write_api
grep: write_api()
grep: Point(
grep: InfluxDBClient.write_api()
grep: write(bucket=..., record=...)

Resultado: ✗ NINGÚN MATCH en endpoint /api/analyze_report
```

#### Inicialización InfluxDB (Línea 23)
```python
_metrics_q = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG).query_api()
```

**Crítico:** 
- ✓ Se inicializa `query_api()` (LECTURA)
- ✗ NUNCA se inicializa `write_api()` (ESCRITURA)

#### Estructura try-except (Sin captura de persistencia)
```python
try:
    # ... procesamiento ...
    analysis = response.choices[0].message.content
    
    return {"success": True, "analysis": analysis, ...}
    
except FileNotFoundError:
    raise HTTPException(...)  # Excepción de lectura
except Exception as e:
    logger.error(f"Error in AI analysis: {e}")
    raise HTTPException(...)
```

**Observación:**
- ✗ No hay try-except para operación de persistencia
- ✗ No hay `logger.info("Analysis persisted to InfluxDB")`
- ✗ No hay validación de write_api().write()
- ✓ Solo hay try-except para lectura de CSV/Groq

### Comparación: Cómo se Vería si Persistiera

**Patrón de persistencia (NO PRESENTE en analyze_report):**
```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_type=SYNCHRONOUS)

# Crear punto con análisis
point = Point("analysis_results") \
    .tag("series_id", id) \
    .field("ensemble_mae", ensemble_mae) \
    .field("analysis_text", analysis) \
    .time(datetime.utcnow())

# Escribir a InfluxDB
write_api.write(bucket=INFLUX_BUCKET, record=point)  # ← NO EXISTE EN CÓDIGO
```

**Verificación:** Esta línea NO aparece en `/api/analyze_report/{id}`.

### Impacto: Costo y Escalabilidad

**Groq API (llama-3.3-70b-versatile):**
- Token input: ~4000 tokens (contexto)
- Token output: ~4000 tokens (análisis)
- Total: ~8000 tokens por petición

**Costo Groq (aproximado):** $0.00027 / 1M input tokens = **$0.002 por análisis sin caché**

**Escala:**
```
100 usuarios × 5 series × 2 sesiones/día = 1000 análisis/día
1000 análisis × $0.002 = $2 USD/día = $60 USD/mes
```

**Sin caché:** Mismo análisis = Mismo costo Groq (N veces)

### Evidencia de Diseño Intencional

1. **Docstring (línea 1475):** Describe "analiza" (acción), no "persiste" (intención ausente)
2. **Patrón dual:** Dos endpoints siguen idéntico flujo sin persistencia → Consistencia intencional
3. **Arquitectura:** Orchestrator es `query_api()` only → Servicio de lectura/análisis, no escritura
4. **Respuesta directa:** `return {"analysis": analysis, ...}` → Streaming, no almacenamiento

---

## Matriz Comparativa de Limitaciones

| Limitación | Componentes Afectados | Gravedad | Contexto |
|---|---|---|---|
| **URL Hardcoding** | 4 componentes frontend | ALTA | Impide despliegue reproducible en producción |
| **URL No-Documentada** | 3 componentes env-based | MEDIA | Variable `VITE_API_BASE` existe pero no está documentada |
| **Analysis No-Persistence** | 2 endpoints (analyze_report*) | MEDIA | Intencional (ephemeral streaming), pero costoso sin caché |
| **Servicio Sin Write-API** | orchestrator global | BAJA | Diseño correcto (separación de concerns), no es error |

---

## Zonas de Código para Apéndice Técnico

### Zona A: Frontend URL Inconsistency
- **Archivo base:** `/frontend/src/components/*.jsx`
- **Documentos de evidencia:**
  - `FIGURA_7_FRONTEND_API_BASE_INCONSISTENCY.md` (este repo)
  - Líneas específicas: 22, 21, 16, 9, 8, 9 (ver matriz anterior)

### Zona B: Analysis No-Persistence
- **Archivo base:** `/services/orchestrator/app.py`
- **Documentos de evidencia:**
  - `FIGURA_8_ANALYSIS_NO_PERSISTENCE.md` (este repo)
  - Rango específico: 1474-1920 (dos endpoints)
  - Punto clave: Línea 23 (`query_api()` sin `write_api()`)

---

## Recomendaciones para Corrección (No Implementadas)

### Para URL Inconsistency

**Opción 1: Centralizar en archivo config**
```javascript
// src/config/api.js
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
export const KAFKA_BASE = import.meta.env.VITE_KAFKA_BASE || "http://localhost:8082";
```

**Opción 2: ESLint rule**
```javascript
// .eslintrc.json
{
  "rules": {
    "no-restricted-syntax": [
      "error",
      {
        "selector": "Literal[value=/localhost:808/]",
        "message": "Use import.meta.env.VITE_API_BASE instead of hardcoded localhost"
      }
    ]
  }
}
```

**Opción 3: Documentar variables**
```bash
# frontend/.env.example
VITE_API_BASE=http://localhost:8081
VITE_KAFKA_BASE=http://localhost:8082
```

### Para Analysis No-Persistence

**Opción 1: Implementar caché en InfluxDB**
```python
# Escribir análisis después de generarlo
write_api.write(bucket=INFLUX_BUCKET, record=Point("analysis_results")...)
```

**Opción 2: Implementar caché en aplicación** (Redis, memcached)
```python
# Antes de llamar a Groq
cache_key = f"analysis:{id}"
cached = redis_client.get(cache_key)
if cached:
    return json.loads(cached)

# ... Groq call ...
redis_client.setex(cache_key, 3600, json.dumps(response))  # 1h TTL
```

**Opción 3: Aceptar como diseño** (si es intencional ephemeral)
Documentar en docstring que es streaming intentional.

---

## Conclusión para Tesis

### Limitaciones Documentadas
1. ✗ **Frontend no es reproducible en producción** sin intervención manual
2. ✗ **Análisis no tiene caché** → costo Groq por petición repetida
3. ✓ **Diseño intencionado en análisis** (ephemeral streaming válido)
4. ✗ **Inconsistencia en frontend** NO es intencional (copypaste sin estándar)

### Impacto Combinado
Sistema con **reproducibilidad limitada** en componentes específicos:
- Frontend: 4/7 componentes sin configuración por entorno
- Backend: Análisis sin persistencia (intencional pero costoso)

### Archivos de Referencia
- `/docs/FIGURA_7_FRONTEND_API_BASE_INCONSISTENCY.md` - Inconsistencia de URLs
- `/docs/FIGURA_8_ANALYSIS_NO_PERSISTENCE.md` - No-persistencia de análisis
- `/services/orchestrator/app.py` - Línea 23 (query_api sin write_api)
- `/frontend/src/components/*.jsx` - 7 componentes, 2 patrones

---

**Generado:** Enero 2026  
**Para:** Apéndice Técnico - TFG Sistema Adaptativo de Predicción Telemétrica
