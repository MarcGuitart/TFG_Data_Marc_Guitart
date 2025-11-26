# 🧪 Guía de Verificación - AP4 (Tabla de Métricas con Weights)

**Fecha:** 26 Noviembre 2025  
**Status:** ✅ LISTO PARA PRUEBAS

---

## 📋 Checklist de Verificación

### 1. Backend - `/api/metrics/models` devuelve weight

**URL:**
```
GET http://localhost:8081/api/metrics/models?id=TestSeries&start=-3d
```

**Verificación en Terminal:**
```bash
curl -s "http://localhost:8081/api/metrics/models?id=TestSeries&start=-3d" | jq '.overall | keys'
```

**Resultado esperado:**
```json
{
  "ab_fast": {
    "mae": 0.456,
    "rmse": 0.567,
    "mape": 0.123,
    "weight": 45.2,
    "n": 100
  },
  "poly2_12": {
    "mae": 0.489,
    "rmse": 0.598,
    "mape": 0.134,
    "weight": 8.1,
    "n": 100
  },
  "linear_8": {
    "mae": 0.512,
    "rmse": 0.634,
    "mape": 0.156,
    "weight": -12.3,
    "n": 100
  }
}
```

**Validación:**
- ✅ Campo `weight` presente en cada modelo
- ✅ Valores numéricos (positivos, negativos o null)
- ✅ Otros campos (mae, rmse, mape, n) presentes

---

### 2. Frontend - MetricsPanel renderiza tabla AP4

**Pasos:**
1. Abre http://localhost:5173
2. Carga CSV: `data/test_csvs/sine_300.csv`
3. Click: "🚀 Ejecutar agente"
4. Espera 20 segundos
5. Selecciona ID: "TestSeries"
6. Click: "Load metrics"

**Verificación Visual:**
```
Deberías ver:

🏆 Top-3 Models (AP4 - Ranked by Weight)
💡 Ordenados por weight descendente...

┌──────┬──────────┬───────┬──────────┬──────────┐
│ Rank │ Model    │ Weight│ MAE      │ RMSE     │
├──────┼──────────┼───────┼──────────┼──────────┤
│ 🥇   │ ab_fast  │ 45.20 │ 0.456000 │ 0.567000 │
│ 🥈   │ poly2_12 │  8.10 │ 0.489000 │ 0.598000 │
│ 🥉   │ linear_8 │-12.30 │ 0.512000 │ 0.634000 │
└──────┴──────────┴───────┴──────────┴──────────┘
```

**Validación:**
- ✅ Tabla visible con título "🏆 Top-3 Models"
- ✅ Columnas: Rank, Model, Weight, MAE, RMSE, (MAPE, n)
- ✅ Medallas: 🥇, 🥈, 🥉 en orden correcto
- ✅ Modelos ordenados por weight descendente
- ✅ Fondo amarillo para fila 🥇

---

### 3. Ordenamiento Correcto

**Verificación de Lógica:**

El archivo `MetricsPanel.jsx` contiene:
```javascript
const getTop3Models = (modelsOverall) => {
  const modelArray = Object.entries(modelsOverall).map(([name, stats]) => ({
    name,
    ...stats
  }));
  
  // Ordenar por weight descendente
  modelArray.sort((a, b) => {
    const weightA = a.weight ?? -Infinity;
    const weightB = b.weight ?? -Infinity;
    return weightB - weightA;
  });
  
  return modelArray.slice(0, 3);
};
```

**Test:**
```javascript
// Simular con datos
const models = {
  "ab_fast": { weight: 45.2, mae: 0.456 },
  "linear_8": { weight: -12.3, mae: 0.512 },
  "poly2_12": { weight: 8.1, mae: 0.489 }
};

// Resultado esperado de getTop3Models(models):
// [
//   { name: "ab_fast", weight: 45.2, ... },
//   { name: "poly2_12", weight: 8.1, ... },
//   { name: "linear_8", weight: -12.3, ... }
// ]
```

---

### 4. Tabla "All Models" (si hay > 3)

**Verificación:**
Si existen más de 3 modelos en la respuesta, debería haber:

```
📊 All Models
(tabla con todos los modelos, también ordenados por weight desc)

┌──────────────┬───────┬──────────┬──────────┐
│ Model        │ Weight│ MAE      │ RMSE     │
├──────────────┼───────┼──────────┼──────────┤
│ ab_fast      │ 45.20 │ 0.456000 │ 0.567000 │
│ poly2_12     │  8.10 │ 0.489000 │ 0.598000 │
│ linear_8     │-12.30 │ 0.512000 │ 0.634000 │
│ kalman       │ -5.50 │ 0.478000 │ 0.605000 │
│ alphabeta    │ -0.30 │ 0.495000 │ 0.612000 │
└──────────────┴───────┴──────────┴──────────┘
```

---

### 5. CSS Estilos AP4

**Verificación en Inspector (F12):**

Abre DevTools → Elementos → Busca tabla AP4 → Verifica estilos:

```css
/* Tabla principal top-3 */
.metrics-table--ap4 {
  ✅ margin-top: 8px;
}

.metrics-table--ap4 thead {
  ✅ background-color: #f0f4f8;
}

.metrics-table--ap4 th {
  ✅ background-color: #e8f1ff;
  ✅ color: #1e40af;
  ✅ font-weight: 700;
}

/* Fila ganadora */
.metrics-row--best {
  ✅ background-color: #fef3c7;
}

/* Columna Weight */
.metrics-weight {
  ✅ color: #00a3ff;
  ✅ font-weight: 700;
  ✅ text-align: right;
}
```

---

## 🔧 Pruebas Detalladas

### Test 1: Weight es dinámico

**Procedure:**
1. Ejecuta agente con TestSeries (primeras 100 muestras)
2. Carga métricas → anota weight de ab_fast (ej: 45.2)
3. Ejecuta agente 100 muestras más
4. Carga métricas nuevamente
5. Weight debería ser diferente (ej: 52.3)

**Validación:**
```
Primera ejecución: ab_fast weight = 45.2
Segunda ejecución: ab_fast weight = 52.3 ✅ (cambió)
```

---

### Test 2: Modelo mejor tiene mayor weight

**Procedure:**
1. Carga TestSeries con 300 muestras
2. Ejecuta agente completo
3. Carga métricas
4. Verifica: El modelo con menor MAE tiene mayor weight

**Validación:**
```
Esperado:
  Menor MAE (0.456) = Mayor Weight (45.2) ✅

Si NO:
  ⚠️ Verificar que AP3 se ejecute correctamente
```

---

### Test 3: Valores Null/Undefined manejados

**Procedure:**
Si un modelo no tiene weight en la BD:

**Esperado:**
- Cell debe mostrar "-" o "N/A"
- Ordenamiento debe poner al final
- No debe romper la tabla

---

### Test 4: Responsive Design

**Verificación:**
- [ ] Desktop (1920x1080): Tabla completa visible
- [ ] Tablet (768x1024): Tabla con scroll horizontal
- [ ] Mobile (375x667): Tabla colapsible o scroll

---

## 📊 Ejemplos de Datos Esperados

### Escenario 1: 3 modelos, weights positivos
```json
{
  "ab_fast": { "mae": 0.45, "rmse": 0.56, "weight": 50.0 },
  "linear_8": { "mae": 0.52, "rmse": 0.64, "weight": 10.0 },
  "poly2_12": { "mae": 0.49, "rmse": 0.60, "weight": 20.0 }
}

Orden esperado:
1. 🥇 ab_fast (50.0)
2. 🥈 poly2_12 (20.0)
3. 🥉 linear_8 (10.0)
```

### Escenario 2: Weights negativos
```json
{
  "ab_fast": { "mae": 0.45, "weight": 45.2 },
  "linear_8": { "mae": 0.52, "weight": -12.3 },
  "poly2_12": { "mae": 0.49, "weight": 8.1 }
}

Orden esperado:
1. 🥇 ab_fast (45.2)
2. 🥈 poly2_12 (8.1)
3. 🥉 linear_8 (-12.3)  ← puede ser negativo
```

### Escenario 3: Múltiples modelos
```json
{
  "ab_fast": { "weight": 50.0 },
  "poly2_12": { "weight": 20.0 },
  "linear_8": { "weight": 10.0 },
  "kalman": { "weight": 5.0 },
  "alphabeta": { "weight": -10.0 }
}

Tabla Top-3:
1. 🥇 ab_fast (50.0)
2. 🥈 poly2_12 (20.0)
3. 🥉 linear_8 (10.0)

Tabla All Models (5 modelos):
1. ab_fast (50.0)
2. poly2_12 (20.0)
3. linear_8 (10.0)
4. kalman (5.0)
5. alphabeta (-10.0)
```

---

## 🐛 Troubleshooting

### Problema: Weight siempre NULL
```
Solución:
1. Verifica que AP3 está guardando en InfluxDB
2. Ejecuta: docker logs docker-agent-1 | tail -20
3. Busca "update_weights"
4. Verifica measurement "weights" existe
```

### Problema: Tabla no aparece
```
Solución:
1. Abre DevTools (F12)
2. Console → errors?
3. Network → /api/metrics/models responde?
4. Verifica estado de metricsLoading
```

### Problema: Orden incorrecto
```
Solución:
1. Abre DevTools → Console
2. Ejecuta:
   const getTop3Models = (m) => {
     const arr = Object.entries(m).map(([n, s]) => ({n, ...s}));
     arr.sort((a, b) => (b.weight ?? -Infinity) - (a.weight ?? -Infinity));
     return arr.slice(0, 3);
   };
   getTop3Models(models.overall);
3. Verifica orden en consola
```

---

## ✅ Checklist Final

- [ ] Backend devuelve weight en `/api/metrics/models`
- [ ] Frontend renderiza tabla "🏆 Top-3 Models"
- [ ] Tabla tiene columnas: Rank, Model, Weight, MAE, RMSE
- [ ] Modelos ordenados por weight descendente
- [ ] Medallas 🥇🥈🥉 en orden correcto
- [ ] Fondo amarillo para ganador
- [ ] Tabla "All Models" mostrada si hay > 3
- [ ] CSS estilos aplicados correctamente
- [ ] Valores NULL manejados gracefully
- [ ] Documentación AP4_METRICAS_WEIGHTS.md creada

---

## 📝 Reportar Resultados

Una vez completadas las pruebas, reporta:

```
STATUS: ✅ COMPLETADO / ⚠️ PARCIAL / ❌ ERROR

Resultados:
- Backend weight incluido: ✅/⚠️/❌
- Frontend tabla AP4: ✅/⚠️/❌
- Ordenamiento correcto: ✅/⚠️/❌
- Estilos CSS: ✅/⚠️/❌
- Tabla All Models: ✅/⚠️/❌ (N/A si ≤3 modelos)

Observaciones:
[Descripción de cualquier comportamiento anómalo]

Screenshots:
[Attach si hay errores]
```

---

**Fecha:** 26 Noviembre 2025  
**Archivo:** AP4_VERIFICACION.md  
**Status:** ✅ LISTO PARA TESTING
