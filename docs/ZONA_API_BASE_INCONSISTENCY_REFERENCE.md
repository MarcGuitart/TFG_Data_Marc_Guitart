# ZONA: Frontend API Base URL Inconsistency
## Referencia Rápida para Tesis

---

## 📍 Ubicación Exacta del Problema

### Patrón 1: ✅ Env-Based (3 componentes, 7 endpoints)
```jsx
// ControlHeader.jsx - Línea 22
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
// Usado en: POST /api/upload_csv (L50), POST /api/run_window (L76), 
//           GET /api/download_weights (L130), POST /api/reset_system (L171)

// AnalysisModal.jsx - Línea 21  
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
// Usado en: GET /api/series (L85), POST /api/analyze_report_advanced (L158)

// LivePredictionChart.jsx - Línea 16
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";
// Usado en: GET /api/series (L61)
```

### Patrón 2: ❌ Hardcoded (4 componentes, 15 endpoints)
```jsx
// PredictionPanel.jsx - Línea 22
const API_BASE = "http://localhost:8081";
// Usado en: 5 endpoints (L88, 108, 169, 187, 201)

// DataPipelineLiveViewer.jsx - Línea 9
const API_BASE = "http://localhost:8081";
// Usado en: 6 endpoints (L93, 104, 142, 154, 181, 182)

// AP3WeightsPanel.jsx - Línea 8
const API_BASE = "http://localhost:8081";
// Usado en: 3 endpoints (L49, 50, 119)

// KafkaOutPanel.jsx - Línea 9
const res = await fetch('http://localhost:8082/flush');  // ← DIRECTO SIN VARIABLE
// Usado en: 1 endpoint (L9)
```

---

## 🔍 Impacto por Escenario

### Desarrollo Local (localhost:8081)
```bash
npm run dev
# ✅ Ambos patrones funcionan
# ✓ ControlHeader → http://localhost:8081 (env fallback)
# ✓ PredictionPanel → http://localhost:8081 (hardcoded)
```

### Producción (URL diferente)
```bash
VITE_API_BASE=https://api.prod.com npm run build
# ✓ ControlHeader → https://api.prod.com (respeta env)
# ✗ PredictionPanel → http://localhost:8081 (ignora env)
# ✗ DataPipelineLiveViewer → http://localhost:8081 (ignora env)
# ✗ AP3WeightsPanel → http://localhost:8081 (ignora env)
# ✗ KafkaOutPanel → http://localhost:8082 (hardcoded)
```

### Despliegue Docker/K8s
```yaml
# Dockerfile.frontend
ENV VITE_API_BASE=https://orchestrator-service:8081

# RUN npm run build
# Resultado: 3/7 componentes usan https://orchestrator-service:8081
#           4/7 componentes aún usan http://localhost:8081
# Consecuencia: FALLA DE CONEXIÓN EN COMPONENTES HARDCODEADOS
```

---

## 📊 Tabla Resumen

| Aspecto | Env-Based (3 comp) | Hardcoded (4 comp) |
|---|---|---|
| **Componentes** | ControlHeader, AnalysisModal, LivePredictionChart | PredictionPanel, DataPipelineLiveViewer, AP3WeightsPanel, KafkaOutPanel |
| **Endpoints** | 7 | 15 |
| **Configurabilidad** | ✅ VITE_API_BASE | ❌ Requiere recompilación |
| **Reproducible** | ✅ Sí | ❌ No |
| **Docker-ready** | ✅ Sí | ❌ No |
| **Kubernetes** | ✅ Sí | ❌ No |

---

## 🔗 Referencias de Código

```
frontend/src/components/
├── ControlHeader.jsx (L22) ................ ✅ import.meta.env.VITE_API_BASE || fallback
├── AnalysisModal.jsx (L21) ............... ✅ import.meta.env.VITE_API_BASE || fallback
├── LivePredictionChart.jsx (L16) ......... ✅ import.meta.env.VITE_API_BASE || fallback
├── PredictionPanel.jsx (L22) ............. ❌ "http://localhost:8081"
├── DataPipelineLiveViewer.jsx (L9) ....... ❌ "http://localhost:8081"
├── AP3WeightsPanel.jsx (L8) .............. ❌ "http://localhost:8081"
└── KafkaOutPanel.jsx (L9) ................ ❌ 'http://localhost:8082/flush' (inline)
```

---

## 🚨 Señal de Inconsistencia

**Mismo código:**
```jsx
// Versión A (ControlHeader.jsx, AnalysisModal.jsx, LivePredictionChart.jsx)
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

// Versión B (PredictionPanel.jsx, DataPipelineLiveViewer.jsx, AP3WeightsPanel.jsx)
const API_BASE = "http://localhost:8081";  // ← Idéntico en resultado, pero sin env check
```

**Análisis:**
- Versión A: Intención explícita de soportar configuración
- Versión B: Copypaste de hardcoded, nunca refactorizado
- Inconsistencia: No es error, es deuda técnica

---

## ✅ Verificación Rápida

Para confirmar inconsistencia en tu fork:
```bash
cd frontend/src/components

# Buscar patrones env-based
grep -n 'import.meta.env.VITE_API_BASE' *.jsx
# Resultado: ControlHeader.jsx:22, AnalysisModal.jsx:21, LivePredictionChart.jsx:16

# Buscar hardcodes
grep -n '"http://localhost:80' *.jsx
# Resultado: PredictionPanel.jsx:22, DataPipelineLiveViewer.jsx:9, AP3WeightsPanel.jsx:8

# Buscar inline fetches
grep -n "fetch('http" *.jsx
# Resultado: KafkaOutPanel.jsx:9
```

---

## 📝 Para tu Tesis

**Sección recomendada:** Limitaciones de Reproducibilidad

**Párrafo:**
> El frontend implementa dos patrones conflictivos para la configuración de URLs base:
> - 3 componentes respetan la variable de entorno `VITE_API_BASE` con fallback a localhost
> - 4 componentes hardcodean `http://localhost:8081` sin posibilidad de sobrescritura
>
> Esta inconsistencia impide despliegue reproducible en entornos de producción. Mientras que 
> `ControlHeader` es configurable por variables de entorno, `PredictionPanel` y `DataPipelineLiveViewer` 
> (componentes principales del análisis) ignoran estas configuraciones, requiriendo recompilación 
> incluso cuando se definen variables de entorno como `VITE_API_BASE`.

**Evidencia:**
- `FIGURA_7_11_FRONTEND_API_BASE_INCONSISTENCY.md` - Análisis detallado
- `FIGURA_7_LIMITACIONES_REPRODUCIBILIDAD_JUSTIFICADAS.md` - Contexto general

---

**Fecha:** 10 Enero 2026  
**Clasificación:** Limitación de Reproducibilidad / Architectural Debt
