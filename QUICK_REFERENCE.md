# 🚀 Quick Reference - AP1, AP2, AP3, AP4

**Última Actualización:** 26 Noviembre 2025  
**Status:** ✅ PRODUCCIÓN

---

## 📍 Ubicaciones Rápidas

### Frontend Components

| AP | Componente | Ubicación | Línea |
|----|-----------|-----------|-------|
| AP1 | Gráficos individuales | DataPipelineLiveViewer.jsx | 620-680 |
| AP2 | Tabla selector | DataPipelineLiveViewer.jsx | 430-490 |
| AP3 | Gráfico pesos | DataPipelineLiveViewer.jsx | 490-600 |
| AP4 | Tabla top-3 | MetricsPanel.jsx | 85-150 |

### Backend Endpoints

| Endpoint | Parámetros | Devuelve | APs |
|----------|-----------|----------|-----|
| `/api/series` | id, hours | observed, predicted, models, chosen, weights | AP1,AP2,AP3 |
| `/api/metrics/models` | id, start | mae, rmse, mape, **weight**, n | AP4 |
| `/api/metrics/combined` | id, start | mae, rmse, mape, daily | General |

### InfluxDB Measurements

| Medición | Tags | Fields | Propósito |
|----------|------|--------|-----------|
| telemetry | id | var, prediction | Datos observados + hybrid |
| telemetry_models | id, model | yhat | Predicciones por modelo (AP1) |
| chosen_model | id | model | Modelo elegido (AP2) |
| weights | id, model | weight | Pesos acumulativos (AP3) |

---

## 🔧 Código Clave (Copy-Paste Ready)

### AP2: Selector Logic (services/agent/main.py)
```python
# Elegir modelo con menor error
errors = {model: abs(obs - pred) for model, pred in predictions.items()}
best = min(errors, key=errors.get)
# Guardar en InfluxDB
```

### AP3: Update Weights (services/agent/hypermodel/hyper_model.py)
```python
def update_weights(self, y_true):
    # Penalizar todos
    for name in self.w:
        self.w[name] -= 1.0
    
    # Ranking por error
    ranked = sorted(errors.items(), key=lambda kv: kv[1])
    M = len(ranked)
    
    # Recompensar por posición
    for rank, (name, _) in enumerate(ranked):
        self.w[name] += M - rank
```

### AP4: Get Top-3 (frontend/src/components/MetricsPanel.jsx)
```javascript
const getTop3Models = (modelsOverall) => {
  const arr = Object.entries(modelsOverall)
    .map(([name, stats]) => ({name, ...stats}));
  arr.sort((a, b) => (b.weight ?? -Infinity) - (a.weight ?? -Infinity));
  return arr.slice(0, 3);
};
```

---

## 🧪 Quick Tests

### Test API devuelve weight
```bash
curl "http://localhost:8081/api/metrics/models?id=TestSeries" | jq '.overall | keys'
```

### Test Frontend renderiza tabla
```bash
http://localhost:5173 → Load metrics → Scroll a "🏆 Top-3 Models"
```

### Test InfluxDB tiene datos
```bash
docker exec influxdb influx query 'from(bucket:"pipeline") |> range(start:-1d) |> filter(fn:(r)=>r._measurement=="weights")'
```

---

## 📊 Datos de Ejemplo

### Request
```
GET /api/metrics/models?id=TestSeries&start=-3d
```

### Response Structure
```json
{
  "id": "TestSeries",
  "overall": {
    "model_name": {
      "mae": 0.456,
      "rmse": 0.567,
      "mape": 0.123,
      "weight": 45.2,
      "n": 100
    }
  },
  "daily": { ... }
}
```

---

## 🎨 CSS Classes Importantes

### Layouts
```css
.viewer-container   /* 100vh, flex column */
.viewer-grid        /* flex column, 100% height */
.section            /* 1rem padding, scroll */
.section:nth-child(1)  /* Kafka In: 120px max-height */
.section:nth-child(2)  /* Uploaded Data: flex:1 */
```

### Metrics Panel AP4
```css
.metrics-table--ap4      /* tabla principal */
.metrics-row--best       /* fondo #fef3c7 amarillo */
.metrics-weight          /* color #00a3ff azul */
.metrics-rank            /* emoji centrado */
```

---

## 🔗 Flujos Principales

### Upload → Prediction → Visualization
```
1. Upload CSV → /api/upload_csv
2. Agent reads → processes → stores (telemetry + weights)
3. Frontend requests → /api/series + /api/metrics/models
4. Display: AP1 + AP2 + AP3 + AP4
```

### Metrics Loading Flow
```
1. User clicks "Load metrics"
2. handleLoadMetrics() fetches:
   - /api/metrics/combined
   - /api/metrics/models
3. MetricsPanel receives data
4. getTop3Models() sorts by weight
5. Render tabla AP4
```

---

## 🛠️ Troubleshooting Rápido

| Problema | Solución |
|----------|----------|
| Weight es NULL | Verificar AP3 ejecutándose: `docker logs docker-agent-1 \| grep update_weights` |
| Tabla AP4 no aparece | Hard refresh navegador: Cmd+Shift+R |
| Orden incorrecto | Check: `modelArray.sort((a,b) => (b.weight ?? -Infinity) - (a.weight ?? -Infinity))` |
| No devuelve metrics | Verificar: `/api/metrics/models?id=X` retorna JSON |
| Estilos no aplican | Verificar: CSS file guardado, cache limpio |

---

## 📚 Documentos de Referencia

### Técnicos
- `AP4_METRICAS_WEIGHTS.md` - Detalles AP4
- `AP1_AP2_AP3_AP4_INTEGRAL.md` - Arquitectura completa
- `LAYOUT_FULLSCREEN.md` - Layout changes

### Testing
- `AP4_VERIFICACION.md` - Guía de pruebas
- `SESION_FINAL_RESUMEN.md` - Esta sesión

---

## ✅ Pre-Flight Checklist

Antes de presentar:
- [ ] Docker: `docker ps` muestra 5 servicios ✓
- [ ] Frontend: `http://localhost:5173` accesible ✓
- [ ] Backend: `curl http://localhost:8081/api/series?id=X` responde ✓
- [ ] Load data: CSV sube sin errores ✓
- [ ] Agent: Completa ejecución en ~20s ✓
- [ ] Metrics: "Load metrics" funciona ✓
- [ ] AP4: Tabla visible con top-3 ✓
- [ ] Estilos: Medallas 🥇 y color azul weight ✓

---

## 🎓 Para Tesis

### Sección: Implementación
```
AP4: Tabla de Métricas con Pesos

El sistema proporciona ranking de modelos mediante:
- Weights acumulativos (AP3)
- Ordenamiento automático por performance
- Visualización top-3 con medallas

Código: MetricsPanel.jsx getTop3Models()
```

### Sección: Resultados
```
Mostrar captura de tabla AP4 con:
- Top-3 modelos
- Pesos (column azul)
- Métricas (MAE, RMSE, MAPE)
- Medallas visuales
```

---

## 🔐 Production Checklist

- [x] No breaking changes
- [x] Backward compatible
- [x] Error handling en place
- [x] Documentado completamente
- [x] CSS sin conflicts
- [x] API response tested
- [x] Frontend rendering verified
- [x] Listo para deployment

---

## 🎯 Next Steps

1. **Testing**: Ejecutar tests end-to-end
2. **Screenshots**: Capturar pantallas para tesis
3. **Demo**: Preparar presentación
4. **Docs**: Revisar documentación final
5. **Deploy**: Listo para presentar

---

**Status:** ✅ READY TO GO  
**Última Revisión:** 26 Noviembre 2025  
**Version:** 1.0
