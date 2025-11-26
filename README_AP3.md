# 🎓 PROYECTO TFG - RESUMEN EJECUTIVO COMPLETO

## 📋 Estado General del Proyecto

### Action Points Implementados

| # | Descripción | Estado | Entrega |
|---|---|---|---|
| **AP1** | Per-model predictions (gráficos separados) | ✅ COMPLETADO | v1.0 |
| **AP2** | Adaptive selector (elige mejor modelo) | ✅ COMPLETADO | v2.0 |
| **AP3** | Weight evolution (sistema de ranking) | ✅ COMPLETADO | v3.0 |

---

## 🏛️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Vite)                  │
│  ├─ Panel de Predicción (carga CSVs)                         │
│  ├─ Gráficos Individuales (AP1 - una línea por modelo)      │
│  ├─ Selector Adaptativo (AP2 - tabla de modelos elegidos)   │
│  └─ Evolución de Pesos (AP3 - gráfico + tabla de pesos)     │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP
┌────────────────▼────────────────────────────────────────────┐
│              BACKEND (FastAPI - Orchestrator)                │
│  ├─ /api/series?id=X                                         │
│  │  └─ Devuelve: observed, predicted, models, chosen_models │
│  │             + NEW: weights evolution                      │
│  └─ Queries a InfluxDB para agregar datos                    │
└────────────────┬────────────────────────────────────────────┘
                 │ InfluxDB Queries
┌────────────────▼────────────────────────────────────────────┐
│              INFLUXDB 2.7 (Time Series DB)                   │
│  Measurements:                                               │
│  ├─ telemetry (var, prediction)                              │
│  ├─ telemetry_models (per-model yhat + model tag)           │
│  ├─ chosen_model (AP2 - best model per timestamp)            │
│  └─ weights (AP3 - cumulative weight evolution)              │
└────────────────┬────────────────────────────────────────────┘
                 ▲ Write
┌────────────────┴────────────────────────────────────────────┐
│          COLLECTOR (Python - window_collector)               │
│  Lee mensajes de Kafka y escribe en InfluxDB                 │
└────────────────▲────────────────────────────────────────────┘
                 │ Kafka: telemetry.agent.out
┌────────────────┴────────────────────────────────────────────┐
│              AGENT (Python - Main Processor)                 │
│  Core Logic:                                                 │
│  ├─ predict(buffer) → {combined_yhat, per_model_yhat}      │
│  ├─ update_weights(y_real):                                  │
│  │  └─ AP3: Ranking + Points                                │
│  │     1. weights -= 1.0 (penalización)                     │
│  │     2. ranked = sort by error                             │
│  │     3. assign points: M, M-1, ..., 1                     │
│  └─ Envía mensaje enriquecido con hyper_weights             │
└────────────────▲────────────────────────────────────────────┘
                 │ Kafka: telemetry.agent.in
┌────────────────┴────────────────────────────────────────────┐
│            DATA LOADER (window_loader)                       │
│  Lee CSVs y produce a Kafka telemetry.agent.in               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Componentes Principales

### 1. HyperModel (Núcleo de Predicción)

**Archivo**: `services/agent/hypermodel/hyper_model.py`

**Modelos Disponibles**:
- `linear_8` - Linear regression (window=8)
- `poly2_12` - Polynomial degree 2 (window=12)
- `ab_fast` - Alpha-Beta filter (α=0.9, β=0.01)

**Modos**:
- `weighted` - Promedio ponderado (no usado actualmente)
- `adaptive` - Selecciona mejor modelo per timestamp (AP2)

**AP3 Implementation**:
```python
def update_weights(self, y_true: float):
    # 1. Penalizar todos
    for name in self.w:
        self.w[name] -= 1.0
    
    # 2. Ranking
    ranked = sorted(errors.items(), key=lambda kv: kv[1])
    
    # 3. Puntos
    for rank, (name, _) in enumerate(ranked):
        reward = len(ranked) - rank
        self.w[name] += reward
```

### 2. Agent (Predictor Principal)

**Archivo**: `services/agent/main.py`

**Flujo**:
1. Lee datos de `telemetry.agent.in` (Kafka)
2. Mantiene buffer circular de últimas N observaciones
3. Para cada mensaje:
   - Agrega al buffer
   - Predice con HyperModel
   - Actualiza pesos (AP3)
   - Enriquece mensaje con telemetría
   - Publica a `telemetry.agent.out`

**Mensaje Enriquecido**:
```json
{
  "id": "TestSeries",
  "yhat": 5.234,
  "hyper_y_hat": 5.234,
  "hyper_models": {"linear_8": 5.1, "poly2_12": 5.3, "ab_fast": 5.2},
  "hyper_weights": {"linear_8": 45.2, "poly2_12": -12.5, "ab_fast": 15.8},
  "hyper_chosen": "linear_8",
  "hyper_errors": {"linear_8": 0.1, "poly2_12": 0.5, "ab_fast": 0.2}
}
```

### 3. Collector (Writer a BD)

**Archivo**: `services/window_collector/main.py`

**Escribe a InfluxDB**:
- `telemetry` (var, prediction)
- `telemetry_models` (per-model predictions)
- `chosen_model` (AP2)
- `weights` (AP3) ← NEW

### 4. Orchestrator (API)

**Archivo**: `services/orchestrator/app.py`

**Endpoint Principal**: `GET /api/series?id=X&hours=24`

**Respuesta**:
```json
{
  "id": "TestSeries",
  "observed": [...],
  "predicted": [...],
  "models": {
    "linear_8": [...],
    "poly2_12": [...],
    "ab_fast": [...]
  },
  "chosen_models": [
    {"t": "2025-11-26T18:30:00Z", "model": "linear_8"},
    ...
  ],
  "weights": {
    "linear_8": [
      {"time": "2025-11-26T18:30:00Z", "weight": 2.0},
      ...
    ],
    ...
  },
  "points": [...]
}
```

### 5. Frontend (UI)

**Archivo**: `frontend/src/components/DataPipelineLiveViewer.jsx`

**Paneles**:

1. **📊 Gráfico Combinado** (AP1)
   - Línea observada (negro)
   - Línea predicha (azul)
   - Background con datos

2. **📈 Vista Individual por Modelo** (AP1)
   - Un gráfico por modelo
   - Colores diferenciados
   - Comparación observado vs predicción

3. **🎯 Selector Adaptativo** (AP2)
   - Tabla con timestamps
   - Modelo elegido en cada instante
   - Últimos 20 puntos

4. **⚖️ Evolución de Pesos** (AP3) ← NEW
   - Gráfico con línea por modelo
   - Tabla con últimos pesos
   - Explicación del algoritmo

---

## 📊 AP3 En Detalle

### ¿Qué Es AP3?

Sistema de **ranking acumulativo** que asigna puntos a modelos basado en desempeño relativo.

### Algoritmo Paso a Paso

**Cada timestamp (t)**:

```
1. Input: y_real(t), predictions = {linear_8: yh1, poly2_12: yh2, ab_fast: yh3}

2. Calcular errores:
   errors = {
     linear_8: |y_real - yh1|,
     poly2_12: |y_real - yh2|,
     ab_fast: |y_real - yh3|
   }

3. Penalizar a todos:
   for model in models:
     weights[model] -= 1.0

4. Ranking (ordenar por error ascendente):
   ranked = [ab_fast(0.0), linear_8(0.1), poly2_12(0.5)]

5. Asignar puntos:
   ab_fast:   weights[ab_fast] += 3   (mejor)
   linear_8:  weights[linear_8] += 2  (medio)
   poly2_12:  weights[poly2_12] += 1  (peor)

6. Resultado acumulado:
   weights = {
     linear_8: 45.2,    (crece)
     poly2_12: -12.5,   (decrece)
     ab_fast: 15.8      (estable)
   }
```

### Visualización AP3

**Gráfico de Evolución**:
- Eje X: Tiempo
- Eje Y: Peso acumulado
- Tres líneas (una por modelo)
- Colores: linear_8=#6366F1, poly2_12=#EC4899, ab_fast=#10B981

**Tabla de Pesos**:
```
┌──────────┬────────┬───────────┐
│ Modelo   │ Peso   │ Tendencia │
├──────────┼────────┼───────────┤
│linear_8  │ +45.2  │    ⬆️      │
│ab_fast   │ +15.8  │    →      │
│poly2_12  │ -12.5  │    ⬇️      │
└──────────┴────────┴───────────┘
```

### Interpretación

- **Peso ALTO** (>20): Modelo confiable
- **Peso POSITIVO** (>0): Funciona mejor que promedio
- **Peso CERO** (≈0): Rendimiento promedio
- **Peso NEGATIVO** (<0): Falla consistentemente
- **Diferencia AMPLIA** (50-(-10)): Clustering claro

---

## 🧪 Cómo Probar (Guía Rápida)

### PASO 1: Preparar Datos
```bash
# Frontend: http://localhost:5173
# → Click "📂 Cargar CSV"
# → Selecciona: data/test_csvs/sine_300.csv
```

### PASO 2: Ejecutar Agente
```bash
# → Click "🚀 Ejecutar agente"
# → Espera 15-20 segundos
```

### PASO 3: Verificar Logs
```bash
docker logs docker-agent-1 --tail 30 | grep "\[pred\]"
# Deberías ver: [pred] id=TestSeries y=... y_hat=... chosen=linear_8
```

### PASO 4: Cargar en Frontend
```bash
# → En panel "📊 Predicción"
# → Dropdown: TestSeries
# → Click "📊 Cargar Series"
```

### PASO 5: Ver Resultados
```bash
# Scroll down, verás:
# ✅ Gráfico combinado (AP1)
# ✅ Gráficos individuales (AP1)
# ✅ Tabla selector adaptativo (AP2)
# ✅ Gráfico evolución pesos (AP3)
# ✅ Tabla últimos pesos (AP3)
```

---

## 📁 Archivos Clave del Proyecto

```
TFG_Agente_Data/
├── services/
│   ├── agent/
│   │   ├── main.py                    ← Predictor principal
│   │   ├── hypermodel/
│   │   │   ├── hyper_model.py         ← update_weights() con AP3
│   │   │   ├── linear_model.py
│   │   │   ├── poly_model.py
│   │   │   ├── alphabeta.py
│   │   │   └── model_config.json
│   │   └── requirements.txt
│   ├── window_collector/
│   │   ├── main.py                    ← Guarda en InfluxDB
│   │   └── requirements.txt
│   ├── orchestrator/
│   │   ├── app.py                     ← API + _query_weights()
│   │   └── requirements.txt
│   └── common/
│       └── trace.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DataPipelineLiveViewer.jsx   ← Panel AP1/AP2/AP3
│   │   │   ├── CsvChart.jsx
│   │   │   └── ...
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.agent
│   ├── Dockerfile.orchestrator
│   ├── Dockerfile.window_collector
│   └── Dockerfile.window_loader
│
├── data/
│   ├── test_csvs/
│   │   ├── sine_300.csv               ← Pequeño (pruebas rápidas)
│   │   ├── sine_900.csv               ← Mediano
│   │   └── sine_1800_doub.csv         ← Grande (pruebas completas)
│   └── ...
│
├── scripts/
│   ├── test_ap2.sh                    ← Verificar AP2
│   └── test_ap3.sh                    ← Verificar AP3
│
├── AP1_VISUALIZACION_MODELOS.md       ← Documentación AP1
├── AP2_SELECTOR_ADAPTATIVO.md         ← Documentación AP2
├── AP3_SISTEMA_PESOS.md               ← Documentación AP3
├── AP3_GUIA_VERIFICACION.md           ← Guía prueba AP3
├── AP3_SUMMARY.md                     ← Resumen AP3
└── README.md                          ← Este archivo
```

---

## 🚀 Próximos Pasos Recomendados

### Corto Plazo (Esta semana)
- [ ] Ejecutar pruebas completas de AP1, AP2, AP3
- [ ] Capturar screenshots de cada panel
- [ ] Verificar datos en InfluxDB
- [ ] Documentar resultados

### Mediano Plazo (Próxima semana)
- [ ] Escribir sección "Resultados" de tesis con screenshots
- [ ] Decidir si implementar AP4 (opcional)
- [ ] Preparar presentación para tutor

### Largo Plazo (Antes del 8 de diciembre)
- [ ] Presentar a tutor
- [ ] Incorporar feedback
- [ ] Versión final de documentación
- [ ] Entrega de tesis

---

## 📚 Para Tu Tesis

### Estructura Recomendada

**Sección: Implementación**
```
4.1 Action Point 1: Visualización Per-Modelo (AP1)
    4.1.1 Motivación: Necesidad de ver cada modelo
    4.1.2 Implementación: Backend + Frontend
    4.1.3 Resultados: Screenshots de gráficos

4.2 Action Point 2: Selector Adaptativo (AP2)
    4.2.1 Motivación: Elegir mejor modelo por timestamp
    4.2.2 Implementación: Algoritmo de selección
    4.2.3 Resultados: Screenshots de tabla adaptativa

4.3 Action Point 3: Sistema de Pesos (AP3)
    4.3.1 Motivación: Cuantificar desempeño histórico
    4.3.2 Implementación: Ranking acumulativo
    4.3.3 Resultados: Screenshots de evolución de pesos
    4.3.4 Análisis: Interpretación de pesos
```

### Párrafos de Ejemplo

**Para AP3**:
> "El Action Point 3 implementa un sistema acumulativo de puntos basado en ranking que proporciona una métrica cuantitativa del desempeño histórico de cada modelo. En cada timestamp, los modelos se ordenan según su error, asignándose puntos de forma que el mejor recibe M puntos y el peor recibe 1, permitiendo que los pesos negativos emerjan naturalmente como indicador de fallo consistente. Este sistema crea un historial transparente que facilita la evaluación de confiabilidad."

---

## 🎯 Checklist Final

- [x] AP1: Gráficos separados por modelo
- [x] AP2: Selector adaptativo (tabla de modelos elegidos)
- [x] AP3: Evolución de pesos con ranking
- [x] Backend: Orchestrator con /api/series extendido
- [x] InfluxDB: Measurements para chosen_model y weights
- [x] Frontend: Paneles visualización AP1, AP2, AP3
- [x] Docker: Imágenes reconstruidas y servicios activos
- [x] Documentación: 4 archivos MD + esta guía
- [x] Scripts: test_ap2.sh, test_ap3.sh

---

## 📞 Troubleshooting Rápido

| Problema | Solución |
|----------|----------|
| No veo datos en el frontend | Ejecuta: `docker logs docker-agent-1 \| grep "[pred]"` |
| Pesos no cambian | Verifica que hay nuevo CSV procesándose |
| InfluxDB vacío | Espera 30 segundos + refresh browser |
| API devuelve error | Verifica que el ID exacto existe |
| Contenedores no inician | `docker-compose down && docker-compose up -d` |

---

## 📖 Documentación

- **AP3_SISTEMA_PESOS.md**: Documentación técnica detallada
- **AP3_GUIA_VERIFICACION.md**: Guía paso-a-paso para pruebas
- **AP3_SUMMARY.md**: Resumen ejecutivo
- **README.md**: Este archivo

---

**Estado**: ✅ LISTO PARA PRUEBAS

**Última actualización**: 2025-11-26

**Autor**: Sistema Automático
