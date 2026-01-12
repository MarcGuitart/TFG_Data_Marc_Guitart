# Índice de Documentación: Limitaciones de Reproducibilidad

## 📋 Estructura de Documentos

### Documento Principal (LEER PRIMERO)
📄 **`FIGURA_7_LIMITACIONES_REPRODUCIBILIDAD_JUSTIFICADAS.md`**
- Resumen ejecutivo de ambas limitaciones
- Matriz comparativa
- Recomendaciones de corrección
- Conclusiones para tesis

---

### Documentos Detallados (Referencias)

#### 1️⃣ Frontend API Base URL Inconsistency
📄 **`FIGURA_7_FRONTEND_API_BASE_INCONSISTENCY.md`**

**Contenido:**
- Problema: 2 estrategias incompatibles en 7 componentes
- Zonas específicas: Componentes env-based (3) vs hardcodeados (4)
- Matriz de inconsistencia con líneas de código
- Impacto en despliegue (desarrollo, docker, producción, kubernetes)
- Demostración de fallo productivo
- Raíz del problema (falta de estándar/enforcement)
- Evidencia de duplicación

**Archivos Afectados:**
```
✓ ControlHeader.jsx (línea 22) - ENV-BASED
✓ AnalysisModal.jsx (línea 21) - ENV-BASED  
✓ LivePredictionChart.jsx (línea 16) - ENV-BASED
✗ PredictionPanel.jsx (línea 22) - HARDCODED
✗ DataPipelineLiveViewer.jsx (línea 9) - HARDCODED
✗ AP3WeightsPanel.jsx (línea 8) - HARDCODED
✗ KafkaOutPanel.jsx (línea 9) - HARDCODED INLINE
```

**Variables de Entorno Esperadas:**
- `VITE_API_BASE` - Base URL para API orchestrator (default: `http://localhost:8081`)
- `VITE_KAFKA_BASE` - Base URL para Kafka (not implemented, hardcoded `http://localhost:8082`)

**Líneas Clave en Código:**
```javascript
// ✓ CORRECTO (3 componentes)
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

// ✗ INCORRECTO (4 componentes)
const API_BASE = "http://localhost:8081";
const res = await fetch('http://localhost:8082/flush');
```

---

#### 2️⃣ Analysis Endpoints - No Persistence
📄 **`FIGURA_8_ANALYSIS_NO_PERSISTENCE.md`**

**Contenido:**
- Problema: Respuestas sin persistencia en BD (ephemeral)
- Flujo completo de ambos endpoints (líneas 1474-1920)
- Prueba definitiva: Ausencia de `_write_api.write()`
- Comparación: Cómo se VERÍA si persistiera
- Implicaciones: Costo Groq, escalabilidad, caché
- Evidencia de diseño intencional vs accidental
- Cálculo de costo (0.002 USD por análisis sin caché)

**Endpoints Afectados:**
```
POST /api/analyze_report/{id}              (líneas 1474-1720)
POST /api/analyze_report_advanced/{id}    (líneas 1721-1920)
```

**Garantías de No-Persistencia:**
- ✗ NO hay `Point()` creado con análisis
- ✗ NO hay `write_api.write()` invocado
- ✗ NO hay logger para persistencia fallida
- ✗ NO hay try-except para BD
- ✓ SÍ hay `return JSON directo` al cliente

**Líneas Clave:**
```python
# Línea 23 - Inicialización SIN write_api
_metrics_q = InfluxDBClient(...).query_api()  # Solo LECTURA, NO escritura

# Línea 1702-1709 - Retorno sin persistencia
return {
    "success": True,
    "analysis": analysis,    # ← Ephemeral (solo en respuesta HTTP)
    "series_id": id,
    ...
}
```

---

## 🔍 Navegación por Tipo de Limitación

### Si buscas: **URL Hardcoding en Frontend**
1. Lee: `FIGURA_7_LIMITACIONES_REPRODUCIBILIDAD_JUSTIFICADAS.md` (Sección "Hallazgo 1")
2. Profundiza: `FIGURA_7_FRONTEND_API_BASE_INCONSISTENCY.md` (Completo)
3. Código: `/frontend/src/components/{PredictionPanel,DataPipelineLiveViewer,AP3WeightsPanel,KafkaOutPanel}.jsx`

### Si buscas: **Análisis sin Persistencia**
1. Lee: `FIGURA_7_LIMITACIONES_REPRODUCIBILIDAD_JUSTIFICADAS.md` (Sección "Hallazgo 2")
2. Profundiza: `FIGURA_8_ANALYSIS_NO_PERSISTENCE.md` (Completo)
3. Código: `/services/orchestrator/app.py` (Líneas 1474-1920)

### Si buscas: **Comparación de Impactos**
1. Lee: `FIGURA_7_LIMITACIONES_REPRODUCIBILIDAD_JUSTIFICADAS.md` (Sección "Matriz Comparativa")
2. Referencias cruzadas a ambos documentos detallados

---

## 📊 Tabla de Resumen Rápido

| Limitación | Archivo Primario | Archivo Detallado | Severidad | Intencional? |
|---|---|---|---|---|
| URL Hardcoding (4 componentes) | `FIGURA_7_LIMITACIONES...` | `FIGURA_7_FRONTEND_API...` | ALTA | ✗ NO (copypaste) |
| URL No-Documentada (3 componentes) | `FIGURA_7_LIMITACIONES...` | `FIGURA_7_FRONTEND_API...` | MEDIA | ✗ NO (oversight) |
| Analysis No-Persistencia | `FIGURA_7_LIMITACIONES...` | `FIGURA_8_ANALYSIS...` | MEDIA | ✓ SÍ (diseño) |
| Costo Groq sin Caché | `FIGURA_7_LIMITACIONES...` | `FIGURA_8_ANALYSIS...` (Zona 4) | MEDIA | ✓ SÍ (trade-off) |

---

## 🎯 Para el Apéndice de Tesis

### Estructura Recomendada

```
Apéndice C: Limitaciones de Reproducibilidad

C.1 Frontend API Base URL Inconsistency (páginas X-Y)
    - Problema (2 párrafos)
    - Evidencia de código (4 bloques de código)
    - Matriz de componentes (tabla)
    - Impacto en despliegue (4 escenarios)
    - Recomendación de corrección

C.2 Analysis Endpoints - Streaming Without Persistence (páginas Y-Z)
    - Problema (2 párrafos)
    - Flujo de ejecución (diagrama ASCII)
    - Prueba de no-persistencia (búsqueda de write_api)
    - Cálculo de costo (tabla)
    - Justificación de diseño intencional

C.3 Conclusiones (página Z)
    - Sistemas afectados
    - Impacto combinado
    - Recomendaciones futuras
```

---

## 📝 Citas para Tesis

### Limitación 1: Frontend URL Configuration
> "El frontend implementa dos estrategias inconsistentes para la resolución de la URL base de API: 3 componentes respetan la variable de entorno VITE_API_BASE mientras que 4 componentes hardcodean http://localhost:8081 sin posibilidad de sobrescritura. Esta inconsistencia impide despliegues reproducibles en entornos no-localhost sin recompilación manual." 
— FIGURA_7_FRONTEND_API_BASE_INCONSISTENCY.md

### Limitación 2: Analysis Streaming
> "Los endpoints de análisis con IA (/api/analyze_report*) implementan una arquitectura streaming ephemeral donde las respuestas se retornan directamente al cliente sin persistencia en base de datos. Si bien esto permite análisis en tiempo real, resulta en costo repetido de API Groq (~$0.002 por análisis sin caché) y ausencia de auditoría histórica."
— FIGURA_8_ANALYSIS_NO_PERSISTENCE.md

---

## 🔗 Referencias Cruzadas

### Limitaciones Relacionadas
- Frontend: 7 componentes, 2 patrones inconsistentes
- Backend: 2 endpoints, 1 patrón (intencional ephemeral)
- Sistema: Parcialmente configurable por entorno

### Documentos Relacionados en el Repo
- `/docs/ENDPOINT_analyze_report_advanced.py` - Ejemplo del endpoint
- `/services/orchestrator/app.py` - Código fuente (líneas 1474-1920)
- `/frontend/src/components/*.jsx` - Componentes frontend

---

## ✅ Checklist para Validación

- [ ] Lei `FIGURA_7_LIMITACIONES_REPRODUCIBILIDAD_JUSTIFICADAS.md` (resumen)
- [ ] Lei `FIGURA_7_FRONTEND_API_BASE_INCONSISTENCY.md` (URL hardcoding)
- [ ] Lei `FIGURA_8_ANALYSIS_NO_PERSISTENCE.md` (análisis ephemeral)
- [ ] Validé líneas de código en archivos fuente
- [ ] Entendí matriz de componentes y endpoints
- [ ] Revisé recomendaciones de corrección
- [ ] Preparé citas para apéndice de tesis

---

## 📞 Preguntas Frecuentes

**P: ¿Por qué existe esta inconsistencia en URL?**  
R: Desarrollo iterativo sin estándar. Primeros componentes (ControlHeader) implementaron env-based, posteriores copiaron hardcodeado de otros lugares. Ver FIGURA_7_LIMITACIONES... Zona 7.

**P: ¿Es crítico el hardcoding de URLs?**  
R: SÍ en producción. Sistema funciona en localhost por coincidencia, pero fallaría en cloud/kubernetes. Ver FIGURA_7_LIMITACIONES... Zona 5.

**P: ¿Se pueden tener análisis persistidos?**  
R: SÍ, pero requiere inicializar `write_api()` en orchestrator y crear Point() con análisis. Ver FIGURA_8_ANALYSIS... Zona 6.

**P: ¿Cuál es el costo de no persistir análisis?**  
R: ~$0.002 USD por análisis sin caché = $60 USD/mes para 100 usuarios. Ver FIGURA_8_ANALYSIS... Zona 4.

**P: ¿Es intencional la no-persistencia?**  
R: SÍ, aparentemente. Ambos endpoints siguen patrón idéntico, orchestrator nunca inicializa write_api. Ver FIGURA_8_ANALYSIS... Zona 8.

---

**Última actualización:** Enero 2026  
**Para:** Apéndice Técnico - TFG Predictor Adaptativo de Telemetría
