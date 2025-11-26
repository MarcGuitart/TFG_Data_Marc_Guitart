# 🎯 AP3 SUMMARY - Sistema de Pesos por Modelo

## Quick Overview

**AP3** implementa un sistema de **ranking acumulativo** que asigna puntos a los modelos basado en su desempeño relativo en cada timestamp. Los pesos se acumulan con el tiempo, permitiendo visualizar cuál modelo es más confiable.

---

## El Algoritmo en 4 Pasos

```python
# Cada vez que llega y_real:
1. Restar 1 a todos los pesos          # Penalización base
   weights[all] -= 1.0

2. Ordenar modelos por error           # Ranking
   ranked = sorted(errors, key=error)

3. Asignar puntos por ranking          # Recompensa
   best:   +3 puntos
   mid:    +2 puntos
   worst:  +1 punto

4. Los pesos se acumulan               # Historial
   Buen desempeño → pesos +
   Mal desempeño  → pesos -
```

---

## Cambios de Código

### 1. HyperModel (`hyper_model.py`)
```python
def update_weights(self, y_true: float):
    # 1) Restar 1 a todos
    for name in self.w:
        self.w[name] -= 1.0
    
    # 2) Ranking
    ranked = sorted(errors.items(), key=lambda kv: kv[1])
    M = len(ranked)
    
    # 3) Asignar puntos
    for rank, (name, _) in enumerate(ranked):
        reward = M - rank
        self.w[name] += reward
```

### 2. Orchestrator (`app.py`)
```python
def _query_weights(id_: str, start: str = "-7d"):
    """Nueva función: consulta evolución de pesos desde InfluxDB"""
    # Devuelve: {"linear_8": [...], "poly2_12": [...], "ab_fast": [...]}

# En /api/series:
weights_by_model = _query_weights(id, start)
payload["weights"] = weights_by_model
```

### 3. Frontend (`DataPipelineLiveViewer.jsx`)
```jsx
{/* Nuevo panel con gráfico + tabla */}
<div>⚖️ Evolución de Pesos (AP3)
  <CsvChart data={weightsData} />  {/* Gráfico temporal */}
  <Table>{/* Últimos pesos */}</Table>
</div>
```

---

## Flujo de Datos Completo

```
CSV → Kafka → Agent → update_weights() → enriched["hyper_weights"]
                                              ↓
                     Collector → InfluxDB("weights")
                                      ↓
                     Orchestrator._query_weights()
                                      ↓
                     Frontend: Panel "⚖️ Evolución"
```

---

## Resultado Visual en Frontend

### Gráfico de Pesos
```
50 ┤     ╱╱╱ linear_8 (confiable)
40 ┤    ╱
30 ┤   ╱    ab_fast (estable)
20 ┤  ╱╱╱╱╱╱
10 ┤╱╱
 0 ┼────────────────────
-10┤            poly2_12 (falla)
```

### Tabla de Pesos
| Modelo   | Peso  |
|----------|-------|
| linear_8 | +45.2 |
| ab_fast  | +15.8 |
| poly2_12 | -12.5 |

---

## ¿Por Qué AP3 Es Importante?

1. **Transparencia**: Ves cuál modelo funciona mejor (históricamente)
2. **Contraste Real**: Los pesos negativos son evidencia de fallo
3. **Aprendizaje Histórico**: Los pesos acumulan información
4. **Base para Decisiones**: Puedes usar pesos en AP4+ para automatizar selección

---

## Verificación en 5 Minutos

```bash
# 1. Frontend: Cargar CSV y ejecutar agente
# (http://localhost:5173)

# 2. Verificar logs
docker logs docker-agent-1 --tail 30 | grep "\[pred\]"

# 3. Verificar API
curl http://localhost:8081/api/series?id=TestSeries | jq '.weights'

# 4. Ir a frontend
# Cargar series → Scroll down → Ver "⚖️ Evolución de Pesos"

# 5. ¡Listo!
```

---

## Archivos Documentación

- `AP3_SISTEMA_PESOS.md` - Documentación técnica completa
- `AP3_GUIA_VERIFICACION.md` - Guía detallada de prueba
- `scripts/test_ap3.sh` - Script de verificación automatizado

---

## Estado del Proyecto

| AP | Descripción | Estado |
|----|----|---|
| AP1 | Per-model predictions (separate charts) | ✅ DONE |
| AP2 | Adaptive selector (choose best model) | ✅ DONE |
| AP3 | Weight evolution (ranking system) | ✅ DONE |
| AP4+ | TBD (optional: weight-based selection?) | 📋 TODO |

---

## Notas Importantes

- Los pesos pueden ser negativos (¡esto es correcto!)
- La acumulación es continua (cada nuevo dato afecta pesos)
- El sistema funciona con cualquier número de modelos
- Puedes usar los pesos para AP4 (weighted decision-making)

---

## Código Status

✅ Agent: update_weights() con ranking de puntos
✅ Collector: guarda weights en InfluxDB
✅ Orchestrator: _query_weights() y /api/series actualizado
✅ Frontend: Panel con gráfico y tabla de pesos
✅ Docker: Imágenes reconstruidas y servicios reiniciados
✅ Documentación: AP3_SISTEMA_PESOS.md + AP3_GUIA_VERIFICACION.md

**Ready to test! 🚀**
