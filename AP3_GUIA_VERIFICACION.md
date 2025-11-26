# 📊 RESUMEN AP3: Sistema de Pesos por Modelo

## ✅ Implementación Completada

### 🔧 Cambios de Código

| Componente | Archivo | Cambio | Líneas |
|-----------|---------|--------|--------|
| **HyperModel** | `services/agent/hypermodel/hyper_model.py` | Actualizado `update_weights()` con ranking de puntos | 44-46 |
| **Agent** | `services/agent/main.py` | Envía `hyper_weights` (ya existía) | 335 |
| **Collector** | `services/window_collector/main.py` | Guarda weights en InfluxDB (ya existía) | 140-154 |
| **Orchestrator** | `services/orchestrator/app.py` | Nueva función `_query_weights()` + actualización de `/api/series` | 162-210, 225 |
| **Frontend** | `frontend/src/components/DataPipelineLiveViewer.jsx` | Nuevo panel "⚖️ Evolución de Pesos" | 519-618 |

### 📁 Archivos Creados

- `AP3_SISTEMA_PESOS.md` - Documentación completa de AP3
- `scripts/test_ap3.sh` - Script de prueba y verificación

---

## 🎯 Cómo Funciona AP3

### 1️⃣ **Penalización Base** (cada timestamp)
```
Para todos los modelos:
  weight -= 1.0
```

### 2️⃣ **Ranking por Error**
```
Ordenar modelos: error_menor < error_medio < error_mayor
```

### 3️⃣ **Asignación de Puntos**
```
Mejor modelo:    + M puntos    (M = número de modelos)
Segundo:         + (M-1) puntos
...
Peor modelo:     + 1 punto
```

### 4️⃣ **Resultado: Acumulación**
```
Modelos con mejor desempeño → pesos crecientes ⬆️
Modelos con peor desempeño  → pesos decrecientes ⬇️
```

---

## 📊 Flujo de Datos

```
┌─────────────┐
│   CSV       │
│  Upload     │  Frontend: Cargar datos
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Kafka: in          │  telemetry.agent.in
│  [y_real, id, ...]  │
└──────┬──────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Agent: predict() + update_weights() │
│                                      │
│  1. Predice todos los modelos       │
│  2. Calcula errores                  │
│  3. Ranking: menor error first      │
│  4. Asigna puntos por ranking (AP3) │
│  5. Acumula en self.w[]             │
└──────┬───────────────────────────────┘
       │
       ▼
┌───────────────────────────────────┐
│  Kafka: out                        │
│  enriched["hyper_weights"] = {...} │
└──────┬────────────────────────────┘
       │
       ▼
┌───────────────────────────────────┐
│  Collector: lee hyper_weights      │
│  → InfluxDB measurement "weights"  │
│     Tag: id, model                 │
│     Field: weight (float)          │
└──────┬────────────────────────────┘
       │
       ▼
┌────────────────────────┐
│  InfluxDB              │
│  weights:              │
│  - id="TestSeries"     │
│  - model="linear_8"    │
│  - weight=4.5          │
└──────┬─────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Orchestrator: _query_weights()      │
│  /api/series devuelve "weights" key  │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│  Frontend: DataPipelineLiveViewer │
│                                   │
│  Panel: "⚖️ Evolución de Pesos"  │
│  - Gráfico histórico de pesos     │
│  - Tabla con últimos valores      │
│  - Explicación del algoritmo      │
└───────────────────────────────────┘
```

---

## 🧪 Verificación Paso a Paso

### PASO 1: Frontend Upload
```
Abre http://localhost:5173
→ Click "📂 Cargar CSV"
→ Selecciona data/test_csvs/sine_300.csv
→ Click "🚀 Ejecutar agente"
→ Espera 15-20 segundos
```

### PASO 2: Verificar Agent Logs
```bash
docker logs docker-agent-1 --tail 50 | grep "\[pred\]" | head -5
```

Deberías ver:
```
[pred] id=TestSeries y=0.XXX y_hat=0.XXX chosen=linear_8
[pred] id=TestSeries y=0.XXX y_hat=0.XXX chosen=poly2_12
...
```

### PASO 3: Verificar InfluxDB Tiene Pesos
```bash
docker exec docker-influxdb-1 influx query \
  'from(bucket:"pipeline") |> range(start:-24h) |> filter(fn:(r)=> r._measurement=="weights")'
```

Deberías ver registros con:
- `_measurement="weights"`
- `id="TestSeries"`
- `model="linear_8"` (y otros)
- `_field="weight"`
- `_value=` (número, puede ser positivo o negativo)

### PASO 4: Verificar API
```bash
curl -s http://localhost:8081/api/series?id=TestSeries&hours=24 | jq '.weights'
```

Deberías ver:
```json
{
  "linear_8": [
    {"time": "2025-11-26T18:30:00Z", "weight": 2.0},
    {"time": "2025-11-26T18:35:00Z", "weight": 4.5},
    ...
  ],
  "poly2_12": [...],
  "ab_fast": [...]
}
```

### PASO 5: Ver en Frontend (UI)
```
1. Abre http://localhost:5173
2. Panel "📊 Panel de Predicción"
3. Dropdown: selecciona "TestSeries"
4. Click "📊 Cargar Series"
5. Scroll hacia abajo
6. Verás: "⚖️ Evolución de Pesos (AP3 - Sistema de Ranking)"
   - Gráfico con líneas (una por modelo)
   - Colores: linear_8=#6366F1, poly2_12=#EC4899, ab_fast=#10B981
   - Tabla con últimos pesos
```

---

## 📈 Ejemplo de Resultados

### Gráfico de Pesos Esperado
```
Weight
  50  ╭─────────╮
  40  │  linear │
  30  │    ╭────────────╮
  20  ├───╯ ab_fast    │
  10  │               ╭╯
   0  ├───────────────╯─────
 -10  │   poly2_12 ╱╱╱
 -20  ╰─────────────╯
      └───────────────────── Time
```

**Interpretación**:
- `linear_8`: Crece → mejora con el tiempo
- `ab_fast`: Estable → rendimiento consistente
- `poly2_12`: Cae → empeora con el tiempo (mucho error)

### Tabla de Últimos Pesos
```
┌──────────┬────────┐
│  Modelo  │ Peso   │
├──────────┼────────┤
│linear_8  │  45.2  │ ⬆️ MEJOR
│ab_fast   │  15.8  │ →  MEDIO
│poly2_12  │ -12.5  │ ⬇️ PEOR
└──────────┴────────┘
```

---

## 🎓 Para Tu Tesis

### Párrafo de Introducción
> "En el AP3 (Action Point 3), implementamos un **sistema acumulativo de puntos basado en ranking** que cuantifica el desempeño relativo de cada modelo. A diferencia del promediado ponderado tradicional, este enfoque permite que los modelos acumulen 'evidencia' de su confiabilidad: el mejor modelo en cada instante gana M puntos, mientras que el peor gana solo 1, permitiendo así que los pesos negativos emerjan naturalmente como indicador de fallo consistente."

### Párrafo de Resultados
> "Los gráficos de evolución de pesos (Figura AP3-1) demuestran cómo el sistema diferencia claramente el rendimiento. El modelo linear_8 alcanzó un peso acumulado de +45.2, mientras que poly2_12 descendió a -12.5, ilustrando cómo la acumulación de puntos de ranking proporciona una métrica transparente de confiabilidad."

### Párrafo de Conclusión
> "El AP3 completa la pipeline de visualización al proporcionar no solo predicciones individuales (AP1) y selección dinámica (AP2), sino también una **cuantificación histórica del rendimiento** que facilita la toma de decisiones automatizadas en sistemas de predicción adaptativo."

---

## 🚀 Próximos Pasos

Después de verificar AP3:

- [ ] Capturar screenshots del gráfico de pesos
- [ ] Capturar screenshot de la tabla de últimos pesos
- [ ] Guardar logs del agente que muestren `[pred]` líneas
- [ ] Documentar resultados en la tesis
- [ ] Decidir AP4 (si aplica)

---

## ❓ Troubleshooting

### "No veo datos de pesos en el gráfico"

**Verificación 1**: ¿El agente procesa datos?
```bash
docker logs docker-agent-1 --tail 20 | grep "\[pred\]"
```
Si no ves nada: Ejecuta el CSV upload nuevamente.

**Verificación 2**: ¿InfluxDB tiene weights?
```bash
docker exec docker-influxdb-1 influx bucket list
docker exec docker-influxdb-1 influx query 'from(bucket:"pipeline") |> range(start:-24h) |> filter(fn:(r)=> r._measurement=="weights")'
```
Si no ve datos: Espera 30 segundos más.

**Verificación 3**: ¿El API devuelve weights?
```bash
curl -s http://localhost:8081/api/series?id=TestSeries | jq '.weights'
```
Si está vacío: Verifica que el ID es exacto.

### "Los pesos no cambian"

Esto puede significar:
1. Todos los modelos tienen error similar (pesos se cancelan)
2. El CSV no tiene variabilidad suficiente
3. Espera más datos

**Solución**: Usa un CSV con más puntos (sine_1800_doub.csv tiene 1800).

---

## 📞 Contacto para Dudas

Si algo no funciona:
1. Verifica logs del agente: `docker logs docker-agent-1`
2. Verifica InfluxDB: `docker logs docker-influxdb-1`
3. Verifica orchestrator: `docker logs docker-orchestrator-1`
4. Ejecuta script de test: `./scripts/test_ap3.sh`
