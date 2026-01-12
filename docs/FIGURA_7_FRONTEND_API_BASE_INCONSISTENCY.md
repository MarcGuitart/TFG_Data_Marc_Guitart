# Frontend API Base URL Inconsistency: Env-Based vs Hardcoded

## Problema Identificado

**Síntesis:** El frontend implementa dos estrategias inconsistentes para resolver la URL base de la API:
1. **Estrategia A (3 componentes):** Respetan variable de entorno `VITE_API_BASE` con fallback a localhost
2. **Estrategia B (4 componentes):** Hardcodean `http://localhost:8081` sin posibilidad de sobrescritura
3. **Estrategia C (1 caso especial):** Hardcodean `http://localhost:8082` para servicio Kafka

**Impacto:** Despliegue no reproducible fuera de entorno local. Recompilación necesaria para cambiar URLs en producción.

---

## Zona 1: Componentes CON Flexibilidad (Env-Based) ✓

### ControlHeader.jsx - Línea 22
**Archivo:** `/frontend/src/components/ControlHeader.jsx`

```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
```

**Uso en endpoints:**
- Línea 50: `POST /api/upload_csv` - `fetch(`${API_BASE}/api/upload_csv`, ...)`
- Línea 76: `POST /api/run_window` - `fetch(`${API_BASE}/api/run_window?forecast_horizon=...`, ...)`
- Línea 130: `GET /api/download_weights` - `${API_BASE}/api/download_weights/${currentId}`
- Línea 171: `POST /api/reset_system` - `fetch(`${API_BASE}/api/reset_system`, ...)`

**Ventaja:** Si se define `VITE_API_BASE` en tiempo de build (ej. `VITE_API_BASE=https://api.prod.com`), este componente funcionará en producción.

---

### AnalysisModal.jsx - Línea 21
**Archivo:** `/frontend/src/components/AnalysisModal.jsx`

```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
```

**Uso en endpoints:**
- Línea 85: `GET /api/series` - `fetch(`${API_BASE}/api/series?${params.toString()}`, ...)`
- Línea 158: `POST /api/analyze_report_advanced` - `fetch(`${API_BASE}/api/analyze_report_advanced/${currentId}`, ...)`

**Ventaja:** Mismo patrón env-based, compatible con producción.

---

### LivePredictionChart.jsx - Línea 16
**Archivo:** `/frontend/src/components/LivePredictionChart.jsx`

```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
```

**Uso en endpoints:**
- Línea 61: `GET /api/series` - `` `${API_BASE}/api/series?id=${encodeURIComponent(selectedId)}&start=-1d` ``

**Ventaja:** Env-based, reutilizable en diferentes entornos.

---

## Zona 2: Componentes SIN Flexibilidad (Hardcoded) ✗

### PredictionPanel.jsx - Línea 22
**Archivo:** `/frontend/src/components/PredictionPanel.jsx`

```jsx
const API_BASE = "http://localhost:8081";
```

**Uso en endpoints:**
- Línea 88: `GET /api/forecast_horizon` - `fetch(`${API_BASE}/api/forecast_horizon`)`
- Línea 108: `GET /api/ids` - `fetch(`${API_BASE}/api/ids`)`
- Línea 169: `GET /api/series` - `fetch(`${API_BASE}/api/series?${params.toString()}`)`
- Línea 187: `GET /api/selector` - `fetch(`${API_BASE}/api/selector?${selectorParams.toString()}`)`
- Línea 201: `GET /api/metrics/models/ranked` - `fetch(`${API_BASE}/api/metrics/models/ranked?${metricsParams.toString()}`)`

**Problema:** 
- ❌ URL **hardcodeada sin variable de entorno**
- ❌ Requiere **recompilación (npm run build)** para cambiar a producción
- ❌ Incompatible con **Docker/Kubernetes** donde se necesita configuración en tiempo de despliegue

---

### DataPipelineLiveViewer.jsx - Línea 9
**Archivo:** `/frontend/src/components/DataPipelineLiveViewer.jsx`

```jsx
const API_BASE = "http://localhost:8081";
```

**Uso en endpoints:**
- Línea 93: `POST /api/upload_csv` - `fetch(`${API_BASE}/api/upload_csv`, ...)`
- Línea 104: `POST /api/run_window` - `fetch(`${API_BASE}/api/run_window`, ...)`
- Línea 142: `GET /api/series` - `fetch(`${API_BASE}/api/series?id=${qs}&hours=24`)`
- Línea 154: `GET /api/ids` - `fetch(`${API_BASE}/api/ids`)`
- Línea 181-182: `GET /api/metrics/combined` + `GET /api/metrics/models` - Parallel fetches

**Problema:** 
- ❌ Mismo hardcoding que PredictionPanel
- ❌ Se replica el mismo endpoint en múltiples lugares
- ❌ Cambios a URL requieren modificar múltiples archivos + recompilación

---

### AP3WeightsPanel.jsx - Línea 8
**Archivo:** `/frontend/src/components/AP3WeightsPanel.jsx`

```jsx
const API_BASE = "http://localhost:8081";
```

**Uso en endpoints:**
- Línea 49: `GET /api/agent/history` - `fetch(`${API_BASE}/api/agent/history/${selectedId}?last_n=200`)`
- Línea 50: `GET /api/agent/stats` - `fetch(`${API_BASE}/api/agent/stats/${selectedId}`)`
- Línea 119: `POST /api/agent/export_csv` - `fetch(`${API_BASE}/api/agent/export_csv/${selectedId}`, ...)`

**Problema:** 
- ❌ Hardcodeado
- ❌ Accede a endpoints proxy del agent (`/api/agent/*`)
- ❌ Necesitaría recompilación para cambiar host

---

### KafkaOutPanel.jsx - Línea 9 (Caso Especial)
**Archivo:** `/frontend/src/components/KafkaOutPanel.jsx`

```jsx
const res = await fetch('http://localhost:8082/flush');
```

**Problema Agravado:**
- ❌ **Hardcodeado directamente en línea** (no usa variable `API_BASE`)
- ❌ URL diferente (`8082` vs `8081`)
- ❌ Apunta a servicio Kafka diferente
- ❌ Sin variable de entorno ni fallback
- ❌ Más difícil de encontrar/actualizar

---

## Zona 3: Ausencia de Documentación de Variables de Entorno

### No existe `.env.example` en frontend
**Búsqueda:** `/frontend/.env*`
**Resultado:** ❌ No encontrado

**Implicación:**
- Desarrolladores NO saben que existe `VITE_API_BASE`
- Nuevos colaboradores no tienen guía de variables de entorno
- En producción, no hay documentación sobre cómo configurar

### No existe `.env` en frontend
**Búsqueda:** `/frontend/.env`
**Resultado:** ❌ No encontrado

**Implicación:**
- Configuración no versionada
- Desarrolladores no pueden hacer `.env` local sin guía
- Sin fallback visible para variables críticas

---

## Zona 4: Matriz de Inconsistencia

| Componente | Archivo | Línea | Estrategia | URL | ¿Variable Env? | ¿Recompilación Necesaria? |
|---|---|---|---|---|---|---|
| **ControlHeader** | ControlHeader.jsx | 22 | Env-based | `VITE_API_BASE` \| fallback | ✓ SÍ | ✗ NO |
| **AnalysisModal** | AnalysisModal.jsx | 21 | Env-based | `VITE_API_BASE` \| fallback | ✓ SÍ | ✗ NO |
| **LivePredictionChart** | LivePredictionChart.jsx | 16 | Env-based | `VITE_API_BASE` \| fallback | ✓ SÍ | ✗ NO |
| **PredictionPanel** | PredictionPanel.jsx | 22 | Hardcoded | `http://localhost:8081` | ✗ NO | ✓ SÍ |
| **DataPipelineLiveViewer** | DataPipelineLiveViewer.jsx | 9 | Hardcoded | `http://localhost:8081` | ✗ NO | ✓ SÍ |
| **AP3WeightsPanel** | AP3WeightsPanel.jsx | 8 | Hardcoded | `http://localhost:8081` | ✗ NO | ✓ SÍ |
| **KafkaOutPanel** | KafkaOutPanel.jsx | 9 | Hardcoded (inline) | `http://localhost:8082` | ✗ NO | ✓ SÍ |

**Observación:** 3 componentes respetan entorno; 4 lo ignoran completamente.

---

## Zona 5: Impacto en Despliegue

### Escenario 1: Desarrollo Local ✓
```bash
# Funciona igual en ambos casos
npm run dev
# Orchestrator escucha en http://localhost:8081
# Componentes hardcoded + env-based funcionan
```

### Escenario 2: Docker Local con Docker Compose
```bash
# docker-compose.yml expone services en localhost:8081
docker-compose up

# Componentes env-based (3) → OK
# Componentes hardcoded (4) → OK (por coincidencia, URL sigue siendo localhost:8081)
```

### Escenario 3: Producción con URL Diferente ❌
```bash
# En producción: API en https://api.prod.example.com
# Build con variables de entorno
VITE_API_BASE=https://api.prod.example.com npm run build

# Resultado:
# - ControlHeader, AnalysisModal, LivePredictionChart → Usan https://api.prod.example.com ✓
# - PredictionPanel, DataPipelineLiveViewer, AP3WeightsPanel → Siguen usando http://localhost:8081 ❌
# - KafkaOutPanel → Intenta conectar a localhost:8082 ❌

# Necesario: Recompilación con hardcoded URLs actualizado manualmente
```

### Escenario 4: Kubernetes / Cloud ❌
```yaml
# k8s-deployment.yaml
env:
  - name: VITE_API_BASE
    value: "https://api.prod.k8s.internal"

# Resultado:
# - 3 componentes responden a variable
# - 4 componentes ignoran variable
# - Sistema parcialmente configurable = FALLA PARCIAL
```

---

## Zona 6: Demostración de Fallo Productivo

### Test Case: Cambio de API a `https://api-staging.local`

#### Paso 1: Configurar variable de entorno
```bash
export VITE_API_BASE="https://api-staging.local"
npm run build
```

#### Paso 2: Resultado esperado (correcto)
```
✓ ControlHeader → https://api-staging.local/api/upload_csv
✓ AnalysisModal → https://api-staging.local/api/series
✓ LivePredictionChart → https://api-staging.local/api/series
```

#### Paso 3: Resultado actual (fallido)
```
✓ ControlHeader → https://api-staging.local/api/upload_csv
✓ AnalysisModal → https://api-staging.local/api/series
✓ LivePredictionChart → https://api-staging.local/api/series
❌ PredictionPanel → http://localhost:8081/api/forecast_horizon (ignora VITE_API_BASE)
❌ DataPipelineLiveViewer → http://localhost:8081/api/upload_csv (ignora VITE_API_BASE)
❌ AP3WeightsPanel → http://localhost:8081/api/agent/history (ignora VITE_API_BASE)
❌ KafkaOutPanel → http://localhost:8082/flush (ignora VITE_API_BASE)
```

**Conclusión:** Sistema **NO es reproducible** en entornos no-localhost sin intervención manual.

---

## Zona 7: Raíz del Problema

### Por qué ocurrió esta inconsistencia

1. **Desarrollo iterativo sin estándar:**
   - Primeros componentes (ControlHeader) implementaron patrón env-based
   - Componentes posteriores (PredictionPanel) copian patrón hardcodeado de otros lugares
   - No hay documentación que defina estándar

2. **Falta de linting/enforcement:**
   - No existe rule en ESLint que rechace hardcoded `localhost`
   - No existe CI check que valide variable `VITE_API_BASE` en todos los componentes
   - No existe script de build que detecte URLs hardcodeadas

3. **Falta de refactoring central:**
   - No existe archivo `config.js` o `api.js` que centralice URLs
   - Cada componente define su propia `const API_BASE`
   - Cambios requieren actualizar 7 archivos diferentes

---

## Zona 8: Evidencia de Impacto Negativo

### Duplicación de Lógica
```jsx
// Patrón correcto (3 componentes)
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

// Patrón incorrecto (4 componentes)
const API_BASE = "http://localhost:8081";
```

**Observación:** El patrón correcto existe en el codebase pero se ignora en la mitad de los componentes.

### Endpoints Duplicados a través de Componentes
```
GET /api/series:
  - DataPipelineLiveViewer.jsx (línea 142)
  - PredictionPanel.jsx (línea 169)
  - AnalysisModal.jsx (línea 85)
  - LivePredictionChart.jsx (línea 61)

GET /api/ids:
  - DataPipelineLiveViewer.jsx (línea 154)
  - PredictionPanel.jsx (línea 108)

POST /api/upload_csv:
  - DataPipelineLiveViewer.jsx (línea 93)
  - ControlHeader.jsx (línea 50)
```

**Implicación:** Cambios en orchestrator requieren actualizar múltiples componentes con múltiples estrategias de URL.

---

## Síntesis para Tesis

### Problema Clave
Frontend implementa **dos patrones incompatibles** para resolución de URL base:
- **Pattern A:** Respeto a variable de entorno (`VITE_API_BASE`) con fallback seguro
- **Pattern B:** Hardcoding directo sin sobrescritura

### Localización Exacta
| Zona | Archivos | Líneas | Problema |
|---|---|---|---|
| **Hardcoded (3 componentes principales)** | PredictionPanel.jsx, DataPipelineLiveViewer.jsx, AP3WeightsPanel.jsx | 22, 9, 8 | No respetan `VITE_API_BASE` |
| **Hardcoded (1 caso especial)** | KafkaOutPanel.jsx | 9 | Inline sin variable, puerto diferente |
| **Env-based (3 componentes)** | ControlHeader.jsx, AnalysisModal.jsx, LivePredictionChart.jsx | 22, 21, 16 | Implementan correctamente |
| **Documentación** | No existe | - | `.env.example` ausente |

### Consecuencias
1. ❌ **No reproducible en producción** sin recompilación
2. ❌ **Incompatible con Docker/Kubernetes** where config happens at deploy-time
3. ❌ **Cambios de URL requieren intervención manual** en 4 archivos
4. ❌ **Variable de entorno documentada implícitamente** (no existe `.env.example`)

### Recomendación para Corrección
Centralizar URL base en archivo única (`src/config/api.js`):
```javascript
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
export const KAFKA_BASE = import.meta.env.VITE_KAFKA_BASE || "http://localhost:8082";
```

Importar en todos los componentes:
```javascript
import { API_BASE, KAFKA_BASE } from "../config/api";
```

---

## Referencias de Código

### Archivos Afectados
1. `/frontend/src/components/PredictionPanel.jsx` - Línea 22
2. `/frontend/src/components/DataPipelineLiveViewer.jsx` - Línea 9
3. `/frontend/src/components/AP3WeightsPanel.jsx` - Línea 8
4. `/frontend/src/components/KafkaOutPanel.jsx` - Línea 9
5. `/frontend/src/components/ControlHeader.jsx` - Línea 22 (CORRECTO)
6. `/frontend/src/components/AnalysisModal.jsx` - Línea 21 (CORRECTO)
7. `/frontend/src/components/LivePredictionChart.jsx` - Línea 16 (CORRECTO)

### Variables de Entorno Esperadas
- `VITE_API_BASE`: Base URL para API orchestrator (default: `http://localhost:8081`)
- `VITE_KAFKA_BASE`: Base URL para servicio Kafka (default: `http://localhost:8082`) — no implementado

---

**Conclusión:** Sistema con **reproducibilidad limitada** debido a inconsistencia de configuración frontend. Necesita refactoring para ambiente-agnostic deployment.
