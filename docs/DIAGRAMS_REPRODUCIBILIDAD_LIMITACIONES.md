# Diagramas de Limitaciones de Reproducibilidad

## Diagrama 1: Frontend API Base URL Resolution

```
┌─────────────────────────────────────────────────────────────────┐
│         Frontend Component Startup                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────┐
        │  Check import.meta.env.VITE_API_BASE│
        └─────────────┬───────────────────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
    ┌─ DEFINED ──┐         ┌─ UNDEFINED ──┐
    │  (Prod)    │         │   (Local)    │
    └────┬───────┘         └───────┬──────┘
         │                         │
         ▼                         ▼
    ┌──────────────┐         ┌──────────────────┐
    │ Use VITE_    │         │ Use Fallback     │
    │ API_BASE     │         │ http://localhost │
    │ value        │         │      :8081       │
    └──────┬───────┘         └────────┬─────────┘
           │                          │
           └──────────────┬───────────┘
                          │
                          ▼
                    ┌───────────┐
                    │  API_BASE │
                    │ is set    │
                    └───────────┘


IMPLEMENTACIÓN POR COMPONENTE:

┌─────────────────────────────────────────────────────────────┐
│                    7 Frontend Components                     │
└─────────────────────────────────────────────────────────────┘
    │
    ├─ ✓ ControlHeader.jsx (línea 22)
    │   const API_BASE = import.meta.env.VITE_API_BASE || "..."
    │   → Flexible, respeta variable de entorno
    │
    ├─ ✓ AnalysisModal.jsx (línea 21)
    │   const API_BASE = import.meta.env.VITE_API_BASE || "..."
    │   → Flexible, respeta variable de entorno
    │
    ├─ ✓ LivePredictionChart.jsx (línea 16)
    │   const API_BASE = import.meta.env.VITE_API_BASE || "..."
    │   → Flexible, respeta variable de entorno
    │
    ├─ ✗ PredictionPanel.jsx (línea 22)
    │   const API_BASE = "http://localhost:8081";
    │   → Hardcodeado, ignora VITE_API_BASE
    │
    ├─ ✗ DataPipelineLiveViewer.jsx (línea 9)
    │   const API_BASE = "http://localhost:8081";
    │   → Hardcodeado, ignora VITE_API_BASE
    │
    ├─ ✗ AP3WeightsPanel.jsx (línea 8)
    │   const API_BASE = "http://localhost:8081";
    │   → Hardcodeado, ignora VITE_API_BASE
    │
    └─ ✗ KafkaOutPanel.jsx (línea 9)
        fetch('http://localhost:8082/flush')
        → Hardcodeado inline, sin variable, puerto diferente
```

---

## Diagrama 2: Escenarios de Despliegue

### Escenario A: Desarrollo Local (FUNCIONA)
```
npm run dev
   │
   ├─ Vite dev server → localhost:5173
   ├─ Orchestrator → localhost:8081
   └─ Kafka → localhost:8082
   
   ┌──────────────────────────────────┐
   │ Resultado: 7/7 componentes OK    │
   │ - ENV-based usan fallback        │
   │ - Hardcoded coinciden con puerto │
   └──────────────────────────────────┘
```

### Escenario B: Docker Local (FUNCIONA)
```
docker-compose up
   │
   ├─ Frontend → http://localhost:5173
   ├─ Orchestrator → http://localhost:8081
   └─ Kafka → http://localhost:8082
   
   ┌──────────────────────────────────┐
   │ Resultado: 7/7 componentes OK    │
   │ - Coincidencia por suerte        │
   │ - No prueba portabilidad real    │
   └──────────────────────────────────┘
```

### Escenario C: Producción (FALLA PARCIAL) ❌
```
Production URL: https://api.prod.example.com
   │
   ├─ Build:
   │  VITE_API_BASE=https://api.prod.example.com npm run build
   │
   └─ Resultado en runtime:
      ┌────────────────────────────────────────────────┐
      │ ✓ ControlHeader, AnalysisModal, LivePrediction │
      │   → Llaman a https://api.prod.example.com      │
      │   → OK                                         │
      ├────────────────────────────────────────────────┤
      │ ✗ PredictionPanel, DataPipelineLiveViewer,     │
      │   AP3WeightsPanel                              │
      │   → Intentan localhost:8081 (hardcodeado)      │
      │   → FALLA (conexión rechazada)                │
      ├────────────────────────────────────────────────┤
      │ ✗ KafkaOutPanel                                │
      │   → Intenta localhost:8082 (hardcodeado)       │
      │   → FALLA (servicio no existe)                │
      └────────────────────────────────────────────────┘
```

### Escenario D: Kubernetes / Cloud (FALLA PARCIAL) ❌
```
k8s Deployment:
  env:
    - name: VITE_API_BASE
      value: "https://api.prod.k8s.internal"

   │
   ├─ Build tiempo: No pasa VITE_API_BASE
   │  (build.yaml no lo pasa durante npm run build)
   │
   └─ Runtime:
      ┌──────────────────────────────────────────────┐
      │ ✗ Incluso si env variable estuviera         │
      │   disponible en navegador, solo 3 de 7      │
      │   componentes la usarían                    │
      │ → Sistema parcialmente configurable = FALLA │
      └──────────────────────────────────────────────┘
```

---

## Diagrama 3: Analysis Endpoint Flow (No Persistence)

```
┌─────────────────────────────────────────────────────────────┐
│         Frontend: POST /api/analyze_report/{id}             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator: analyze_report(id)                           │
│  Archivo: /services/orchestrator/app.py (línea 1474)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ READ CSV File   │
                    │ /app/data/      │
                    │ weights_history │
                    │ _{id}.csv       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ PROCESS DATA    │
                    │ - model_stats   │
                    │ - ensemble_mae  │
                    │ - weight_trends │
                    │ (en memoria)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  CALL GROQ API  │
                    │  llama-3.3-70b  │
                    │  max_tokens=4000│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ GET ANALYSIS    │
                    │ analysis =      │
                    │ response[0].    │
                    │ message.content │
                    └────────┬────────┘
                             │
         ╔═══════════════════╩═══════════════════╗
         ║                                       ║
         ▼                                       ▼
    ┌─────────────┐                    ┌────────────────┐
    │ RETURN JSON │                    │ ✗ NO escribir  │
    │ al cliente  │                    │   a InfluxDB   │
    │ (ephemeral) │                    │ ✗ NO persistir │
    │             │                    │   análisis     │
    │ {           │                    │ ✗ NO crear     │
    │  "success"  │                    │   Point()      │
    │  "analysis" │                    │ ✗ NO invocar   │
    │  ...        │                    │   write_api()  │
    │ }           │                    └────────────────┘
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Frontend    │
    │ recibe      │
    │ JSON        │
    │ (response   │
    │  en cliente)│
    │             │
    │ ✗ NO está   │
    │   en BD     │
    │ ✗ NO caché  │
    │ ✗ SIN audit │
    └─────────────┘
```

---

## Diagrama 4: Write API Pattern Comparison

### Patrón A: Con Persistencia (window_collector.main.py)
```
┌──────────────────────────────────────┐
│ Data Processing                      │
├──────────────────────────────────────┤
│ - Lee Kafka                          │
│ - Calcula métricas                   │
│ - Crea Point() con datos             │
│                                      │
│ point = Point("telemetry_models")    │
│   .tag("id", id)                     │
│   .field("value", x)                 │
│   .time(ts)                          │
│                                      │
│ ✓ write_api.write(...)               │
│   bucket=INFLUX_BUCKET               │
│   record=point                       │
│                                      │
│ Resultado: Datos en InfluxDB ✓       │
│           Auditoría completa ✓       │
│           Caché disponible ✓         │
└──────────────────────────────────────┘
```

### Patrón B: Sin Persistencia (orchestrator analyze_report)
```
┌──────────────────────────────────────┐
│ Analysis Processing                  │
├──────────────────────────────────────┤
│ - Lee CSV / InfluxDB                 │
│ - Calcula estadísticas               │
│ - Llama Groq API                     │
│ - Obtiene análisis                   │
│                                      │
│ analysis = response[0].message       │
│                                      │
│ ✗ NO hay write_api.write(...)        │
│ ✗ NO hay Point() creado              │
│ ✗ NO hay persistencia                │
│                                      │
│ Resultado: JSON al cliente ✓         │
│           Sin caché ✗                │
│           Costo Groq repetido ✗      │
│           Sin auditoría ✗            │
└──────────────────────────────────────┘
```

---

## Diagrama 5: InfluxDB Client Initialization

```
┌─────────────────────────────────────────────────────────────┐
│  /services/orchestrator/app.py (línea 23)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  _metrics_q = InfluxDBClient(                              │
│      url=INFLUX_URL,                                       │
│      token=INFLUX_TOKEN,                                   │
│      org=INFLUX_ORG                                        │
│  ).query_api()          ← SOLO LECTURA                     │
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │ ✓ Inicializa: query_api()           │                   │
│  │   - Función: SELECT / InfluxQL      │                   │
│  │   - Acceso: Lectura de datos        │                   │
│  │   - Usado en: GET /api/metrics/*    │                   │
│  │             GET /api/series         │                   │
│  │             GET /api/forecast_*    │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │ ✗ Nunca inicializa: write_api()     │                   │
│  │   - Función: INSERT / WRITE         │                   │
│  │   - Acceso: Escritura de datos      │                   │
│  │   - Implicación: No hay endpoint    │                   │
│  │     de persistencia en orchestrator │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
│  Conclusión: Orchestrator = Servicio de LECTURA            │
│              Solo análisis, NO persistencia                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Diagrama 6: Costo Groq Sin Caché

```
Usuario A solicita análisis para serie X
   │
   ├─ Call 1 a Groq API
   │  - Input: ~4000 tokens
   │  - Output: ~4000 tokens
   │  - Costo: $0.002
   │  - Resultado: Análisis retornado ✓
   │  - ¿Guardado? NO ✗
   │
   ├─ Usuario A solicita NUEVAMENTE análisis para serie X
   │  │
   │  ├─ Call 2 a Groq API (REPETIDO)
   │  │  - Input: ~4000 tokens (idéntico)
   │  │  - Output: ~4000 tokens (similar)
   │  │  - Costo: $0.002 (REPETIDO)
   │  │  - Resultado: Análisis retornado ✓
   │  │
   │  └─ Costo acumulado: $0.004 por 2 llamadas idénticas
   │
   └─ Escala a 100 usuarios × 5 series × 2 sesiones
      = 1000 llamadas/día
      = $2 USD/día
      = $60 USD/mes
      (SIN caché, MISMO análisis N veces)


CON CACHÉ (No implementado):
═════════════════════════════════════

Primera llamada: $0.002
Segunda llamada: $0 (caché hit)
Tercera llamada: $0 (caché hit)

Escala: 1000 llamadas/día
        - Solo ~10-20 nuevas ≠ cached
        - Costo: $0.02-$0.04 USD/día
        - Ahorro: $2 → $0.03 = 98% reduction
```

---

## Diagrama 7: Matriz de Impacto

```
┌─────────────────────────────────────────────────────────────┐
│         Limitación de Reproducibilidad                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┬─────────────┬──────────────────────────┐
│ Limitación      │ Afecta a    │ Impacto                  │
├─────────────────┼─────────────┼──────────────────────────┤
│ URL Hardcoding  │ 4 componentes│ ❌ No reproducible en    │
│ (frontend)      │ frontend    │    producción            │
│                 │             │ ❌ Recompilación         │
│                 │             │    necesaria             │
│                 │             │ ❌ Incompatible con      │
│                 │             │    k8s/docker            │
├─────────────────┼─────────────┼──────────────────────────┤
│ URL No-Documented│ 3 componentes│ ⚠️  Developers no saben │
│ (VITE_API_BASE) │ frontend    │    variable existe       │
│                 │             │ ⚠️  Sin .env.example     │
├─────────────────┼─────────────┼──────────────────────────┤
│ Analysis        │ 2 endpoints │ ⚠️  Sin caché            │
│ No-Persistence  │ backend     │ ⚠️  Costo Groq repetido  │
│                 │             │ ⚠️  Sin auditoría        │
│                 │             │ ℹ️  Intencional (design) │
├─────────────────┼─────────────┼──────────────────────────┤
│ Write-API       │ orchestrator │ ℹ️  Separación de        │
│ No Initialized  │ global      │    concerns (correcto)   │
│                 │             │ ℹ️  No es error          │
└─────────────────┴─────────────┴──────────────────────────┘
```

---

## Diagrama 8: Flujo de Solución Recomendada (URL Hardcoding)

```
Problema Actual:
┌─────────────────────────────────────────────────────────────┐
│ 7 componentes → 2 patrones → inconsistencia                │
└─────────────────────────────────────────────────────────────┘

Solución Opción 1: Centralizar en archivo config
┌─────────────────────────────────────────────────────────────┐
│ src/config/api.js                                          │
├─────────────────────────────────────────────────────────────┤
│ export const API_BASE =                                    │
│   import.meta.env.VITE_API_BASE || "localhost:8081"       │
│                                                            │
│ export const KAFKA_BASE =                                  │
│   import.meta.env.VITE_KAFKA_BASE || "localhost:8082"    │
└─────────────────────────────────────────────────────────────┘
         ▲
         │
         └─ Importar en todos los componentes
            import { API_BASE } from "../config/api"
            
Resultado: 1 patrón, 7 componentes, consistencia ✓

Solución Opción 2: ESLint + CI/CD
┌─────────────────────────────────────────────────────────────┐
│ .eslintrc.json                                             │
│ rule: "no-restricted-syntax"                              │
│   - Error: Literal[value=/localhost:808/]                 │
│   - Mensaje: "Use import.meta.env.VITE_* instead"         │
├─────────────────────────────────────────────────────────────┤
│ Resultado: Compile error si se hardcodea localhost        │
│           Previene regresión automáticamente              │
└─────────────────────────────────────────────────────────────┘

Solución Opción 3: Documentación
┌─────────────────────────────────────────────────────────────┐
│ frontend/.env.example                                      │
├─────────────────────────────────────────────────────────────┤
│ VITE_API_BASE=http://localhost:8081                        │
│ VITE_KAFKA_BASE=http://localhost:8082                      │
│                                                            │
│ Resultado: Developers saben variables existen             │
│           New contributors tienen guía                    │
└─────────────────────────────────────────────────────────────┘
```

---

**Diagramas generados:** Enero 2026  
**Para:** Visualización de limitaciones de reproducibilidad
