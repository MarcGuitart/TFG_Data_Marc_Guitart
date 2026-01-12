# Figura 7.11-A: Frontend API Base URL Inconsistency

**Título completo:** Frontend API Base URL Inconsistency: Environment-based vs Hardcoded Localhost

**Tema:** Limitaciones de despliegue reproducible fuera de entorno local (localhost:8081)

---

## Problema Identificado

El frontend implementa **dos estrategias incompatibles** para configurar la URL base de la API:

1. **Componentes con soporte de variables de entorno** (ENV-based)
2. **Componentes con URLs hardcodeadas** (Hardcoded)

Esta inconsistencia impide despliegues reproducibles en entornos de producción, Docker, o Kubernetes sin recompilación manual.

---

## Evidencia A: Componentes ENV-based (Correctos)

### ControlHeader.jsx (Línea 22)

**Archivo:** `frontend/src/components/ControlHeader.jsx`

```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

export default function ControlHeader({ onIdsUpdate, analyticsData = {} }) {
  // ...
  
  // Usado en línea 50:
  const res = await fetch(`${API_BASE}/api/upload_csv`, {
    method: "POST",
    body: formData,
  });
  
  // Usado en línea 76:
  const res = await fetch(`${API_BASE}/api/run_window?forecast_horizon=${forecastHorizon}`, {
    method: "POST",
  });
  
  // Usado en línea 130:
  const downloadUrl = `${API_BASE}/api/download_weights/${currentId}`;
  
  // Usado en línea 171:
  const res = await fetch(`${API_BASE}/api/reset_system`, {
    method: "POST",
  });
}
```

**Patrón:** `import.meta.env.VITE_API_BASE || "http://localhost:8081"`

**Característica:** Permite sobrescribir vía variable de entorno `VITE_API_BASE` en tiempo de build/deploy.

---

### AnalysisModal.jsx (Línea 21)

**Archivo:** `frontend/src/components/AnalysisModal.jsx`

```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

export default function AnalysisModal({ /* ... */ }) {
  // ...
  
  // Usado en línea 85:
  const res = await fetch(`${API_BASE}/api/series?${params.toString()}`);
  
  // Usado en línea 158:
  const res = await fetch(`${API_BASE}/api/analyze_report_advanced/${currentId}`, {
    method: "POST",
  });
}
```

**Patrón:** Mismo que ControlHeader.jsx

---

### LivePredictionChart.jsx (Línea 16)

**Archivo:** `frontend/src/components/LivePredictionChart.jsx`

```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

export default function LivePredictionChart() {
  // ...
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/series?id=${encodeURIComponent(selectedId)}&start=-1d`
        );
        // ...
      }
    }
  }, [selectedId])
}
```

**Patrón:** Mismo que ControlHeader.jsx

---

## Evidencia B: Componentes Hardcoded (Problemáticos)

### PredictionPanel.jsx (Línea 22)

**Archivo:** `frontend/src/components/PredictionPanel.jsx`

```jsx
const API_BASE = "http://localhost:8081";
const DEFAULT_HOURS = 24;
const FULL_HOURS = 999;

const PredictionPanel = forwardRef((props, ref) => {
  // ...
  
  // Usado en línea 88:
  const res = await fetch(`${API_BASE}/api/forecast_horizon`);
  
  // Usado en línea 108:
  const res = await fetch(`${API_BASE}/api/ids`);
  
  // Usado en línea 169:
  const r = await fetch(`${API_BASE}/api/series?${params.toString()}`);
  
  // Usado en línea 187:
  const rSelector = await fetch(`${API_BASE}/api/selector?${selectorParams.toString()}`);
  
  // Usado en línea 201:
  const rMetrics = await fetch(`${API_BASE}/api/metrics/models/ranked?${metricsParams.toString()}`);
});
```

**Patrón:** `"http://localhost:8081"` - Hardcodeado, sin variables de entorno

**Problema:** 
- No respeta `VITE_API_BASE`
- Requiere recompilación para cambiar URL
- Incompatible con Docker/K8s

---

### DataPipelineLiveViewer.jsx (Línea 9)

**Archivo:** `frontend/src/components/DataPipelineLiveViewer.jsx`

```jsx
const API_BASE = "http://localhost:8081";
const endpoints = null; 

export default function DataPipelineLiveViewer() {
  // ...
  
  // Usado en línea 93:
  const up = await fetch(`${API_BASE}/api/upload_csv`, {
    method: "POST",
    body: formData,
  });
  
  // Usado en línea 104:
  const res = await fetch(`${API_BASE}/api/run_window`, { method: "POST" });
  
  // Usado en línea 142:
  const res = await fetch(`${API_BASE}/api/series?id=${qs}&hours=24`);
  
  // Usado en línea 154:
  const res = await fetch(`${API_BASE}/api/ids`);
  
  // Usado en línea 181-182:
  fetch(`${API_BASE}/api/metrics/combined?id=${qs}&start=-3d`),
  fetch(`${API_BASE}/api/metrics/models?id=${qs}&start=-3d`)
}
```

**Patrón:** `"http://localhost:8081"` - Hardcodeado

**Problema:** Mismo que PredictionPanel.jsx

---

### AP3WeightsPanel.jsx (Línea 8)

**Archivo:** `frontend/src/components/AP3WeightsPanel.jsx`

```jsx
const API_BASE = "http://localhost:8081";

export default function AP3WeightsPanel({ selectedId }) {
  // ...
  
  // Usado en línea 49-50:
  const [histRes, statsRes] = await Promise.all([
    fetch(`${API_BASE}/api/agent/history/${selectedId}?last_n=200`),
    fetch(`${API_BASE}/api/agent/stats/${selectedId}`)
  ]);
  
  // Usado en línea 119:
  const res = await fetch(`${API_BASE}/api/agent/export_csv/${selectedId}`, {
    method: "POST",
  });
}
```

**Patrón:** `"http://localhost:8081"` - Hardcodeado

**Problema:** Mismo que PredictionPanel.jsx

---

### KafkaOutPanel.jsx (Línea 9)

**Archivo:** `frontend/src/components/KafkaOutPanel.jsx`

```jsx
export default function KafkaOutPanel() {
  useEffect(() => {
    const fetchProcessed = async () => {
      try {
        const res = await fetch('http://localhost:8082/flush');  // ← Hardcodeado
        const json = await res.json();
        setRows(json.data || []);
      } catch (error) {
        console.error('Error fetching processed data:', error);
      }
    };

    fetchProcessed();
    const interval = setInterval(fetchProcessed, 3000);
    return () => clearInterval(interval);
  }, []);
}
```

**Patrón:** `'http://localhost:8082/flush'` - Hardcodeado directo en URL, sin variable

**Problema:** 
- Puerto 8082 completamente fijo
- Ni siquiera usa variable API_BASE
- Más grave: no hay forma de configurar en tiempo de deploy

---

## Resumen Comparativo

| Componente | Archivo | Línea | Estrategia | ¿Configurable? | Impacto |
|---|---|---|---|---|---|
| **ControlHeader** | ControlHeader.jsx | 22 | ENV-based | ✅ Sí | Soporta despliegue flexible |
| **AnalysisModal** | AnalysisModal.jsx | 21 | ENV-based | ✅ Sí | Soporta despliegue flexible |
| **LivePredictionChart** | LivePredictionChart.jsx | 16 | ENV-based | ✅ Sí | Soporta despliegue flexible |
| **PredictionPanel** | PredictionPanel.jsx | 22 | Hardcoded | ❌ No | Requiere recompilación |
| **DataPipelineLiveViewer** | DataPipelineLiveViewer.jsx | 9 | Hardcoded | ❌ No | Requiere recompilación |
| **AP3WeightsPanel** | AP3WeightsPanel.jsx | 8 | Hardcoded | ❌ No | Requiere recompilación |
| **KafkaOutPanel** | KafkaOutPanel.jsx | 9 | Hardcoded (directo) | ❌ No | Requiere recompilación |

---

## Impacto en Ciclo de Vida

### Desarrollo Local
- ✅ **Funciona:** Ambas estrategias funcionan porque el backend está en `localhost:8081`

### Testing en Docker
```bash
docker-compose up
# KafkaOutPanel intenta conectar a http://localhost:8082 DESDE EL CONTENEDOR
# → Falla: no existe localhost dentro del contenedor
```

### Producción con URL diferente
```bash
# Intenta deploying en https://api.example.com:8443
# Componentes con ENV-based: ✅ Funcionan si se pasa VITE_API_BASE=https://api.example.com:8443
# Componentes hardcoded: ❌ Intenta http://localhost:8081 → Falla
```

### Kubernetes con multi-entorno
```yaml
# ConfigMap para desarrollo
VITE_API_BASE: "http://orchestrator-dev:8081"

# ConfigMap para producción
VITE_API_BASE: "https://api.prod.example.com"

# Resultado:
# - ControlHeader, AnalysisModal, LivePredictionChart: Respetan ConfigMap ✅
# - PredictionPanel, DataPipelineLiveViewer, AP3WeightsPanel, KafkaOutPanel: Ignoran ConfigMap ❌
```

---

## Raíz del Problema

### 1. Falta de Documentación
**No existe archivo `.env.example` o `.env`** en `frontend/` que documente:
```bash
# ❌ No existe
frontend/.env
frontend/.env.example

# Desarrolladores desconocen que VITE_API_BASE existe
```

### 2. Inconsistencia de Implementación
Algunos desarrolladores usaron:
```jsx
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
```

Otros usaron directamente:
```jsx
const API_BASE = "http://localhost:8081";
```

Sin coordinación central.

### 3. Falta de Aplicación en Vite Config
**`frontend/vite.config.js`** no documenta variables de entorno:

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  server: {
    host: true,
    strictPort: true,
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      clientPort: 5173,
    },
  },
});
// ❌ Sin .env loading o procesamiento de VITE_API_BASE
```

---

## Impacto para Reproducibilidad

| Métrica | Evaluación |
|---|---|
| **Reproducibilidad Local** | ✅ Funciona sin cambios |
| **Reproducibilidad en Docker** | ⚠️ Parcial (algunos componentes fallan) |
| **Reproducibilidad en K8s** | ❌ Requiere recompilación para ciertos componentes |
| **Multi-ambiente (dev/staging/prod)** | ❌ No totalmente automatizable |
| **Despliegue sin modificación de código** | ❌ 4 de 7 componentes lo impiden |

---

## Conclusión

El sistema implementa **configuración parcial de URLs**:
- **3 componentes (43%)** respetan variables de entorno
- **4 componentes (57%)** requieren recompilación para cambiar URLs

Esto **limita significativamente la reproducibilidad** de despliegues fuera del entorno local y contradice principios de **containerización y automatización** esperados en sistemas cloud-native.

**Impacto en tesis:** Documentar como limitación arquitectónica que requiere refactoring centralizado de configuración (por ej., crear archivo `frontend/src/config/api.js` con lógica única).

---

## Referencias en Código

```
frontend/src/components/
├── ControlHeader.jsx          (Línea 22)    → ENV-based ✅
├── AnalysisModal.jsx          (Línea 21)    → ENV-based ✅
├── LivePredictionChart.jsx    (Línea 16)    → ENV-based ✅
├── PredictionPanel.jsx        (Línea 22)    → Hardcoded ❌
├── DataPipelineLiveViewer.jsx (Línea 9)     → Hardcoded ❌
├── AP3WeightsPanel.jsx        (Línea 8)     → Hardcoded ❌
└── KafkaOutPanel.jsx          (Línea 9)     → Hardcoded directo ❌
```
