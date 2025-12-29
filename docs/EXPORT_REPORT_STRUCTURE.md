# Export Report Structure (Updated)

## Overview
El **Export Report** ahora tiene una estructura de columnas reorganizada y lógica para facilitar el análisis de la evolución del sistema de predicción ensemble adaptativo.

## Estructura de Columnas

### 1. **TEMPORAL** (2 columnas)
- `step`: Número secuencial del paso (1, 2, 3, ...)
- `ts`: Timestamp ISO-8601 del data point

### 2. **REAL** (1 columna)
- `y_real`: Valor real de la variable observada

### 3. **PREDICCIONES** (N columnas, 1 por modelo)
- `y_linear`: Predicción del modelo Linear
- `y_poly`: Predicción del modelo Polynomial
- `y_alphabeta`: Predicción del modelo Alpha-Beta
- `y_kalman`: Predicción del modelo Kalman
- `y_base`: Predicción del modelo Base (naive)

### 4. **ERRORES ABSOLUTOS** (N columnas, 1 por modelo)
- `err_linear`: Error absoluto |y_real - y_linear|
- `err_poly`: Error absoluto |y_real - y_poly|
- `err_alphabeta`: Error absoluto |y_real - y_alphabeta|
- `err_kalman`: Error absoluto |y_real - y_kalman|
- `err_base`: Error absoluto |y_real - y_base|

### 5. **ERRORES RELATIVOS (%)** (N columnas, 1 por modelo)
- `err_rel_linear`: Error relativo (%) = (err_linear / y_real) * 100
- `err_rel_poly`: Error relativo (%)
- `err_rel_alphabeta`: Error relativo (%)
- `err_rel_kalman`: Error relativo (%)
- `err_rel_base`: Error relativo (%)

### 6. **WEIGHTS ACTUALES** (N columnas, 1 por modelo)
**Pesos DESPUÉS del update en ese step**
- `w_linear`: Weight del modelo Linear
- `w_poly`: Weight del modelo Polynomial
- `w_alphabeta`: Weight del modelo Alpha-Beta
- `w_kalman`: Weight del modelo Kalman
- `w_base`: Weight del modelo Base

> 💡 **Nota**: Estos pesos evolucionan según el sistema de recompensas. El peso más alto indica mejor desempeño acumulado.

### 7. **RANKING** (N columnas, 1 por modelo)
**Ranking en ese instant de tiempo (1 = mejor, N = peor)**
- `rank_linear`: Ranking del modelo Linear (1 si mejor error, 5 si peor)
- `rank_poly`: Ranking del modelo Polynomial
- `rank_alphabeta`: Ranking del modelo Alpha-Beta
- `rank_kalman`: Ranking del modelo Kalman
- `rank_base`: Ranking del modelo Base

### 8. **DECISIÓN** (1 columna)
- `chosen_by_error`: **Modelo elegido en este step** basado en el error mínimo
  - Valor: nombre del modelo seleccionado (ej: "linear", "poly", "kalman", etc.)

### 9. **CAMPOS OPCIONALES** (adicionales si existen)
- `total_reward`: Suma de rewards asignados en este step (siempre = 10)
- `choices_differ`: Boolean indicando si `chosen_by_error` ≠ `chosen_by_weight`
- `chosen_by_weight`: Modelo que tendría mayor weight si se eligiera por acumulación
- `decay_share`: Porcentaje de decay aplicado en sistema de pesos
- `w_pre_*`: Pesos ANTES del update (para análisis de evolución)
- `reward_*`: Rewards individuales asignados (por modelo, en este step)

## Ejemplo de una fila

```
step,ts,y_real,y_linear,y_poly,y_alphabeta,y_kalman,y_base,err_linear,err_poly,err_alphabeta,err_kalman,err_base,err_rel_linear,err_rel_poly,err_rel_alphabeta,err_rel_kalman,err_rel_base,w_linear,w_poly,w_alphabeta,w_kalman,w_base,rank_linear,rank_poly,rank_alphabeta,rank_kalman,rank_base,chosen_by_error,...

1,2025-03-10T00:30:00Z,0.106925,0.127089,0.127089,0.127089,0.127089,0.127089,0.020164,0.020164,0.020164,0.020164,0.020164,18.858,18.858,18.858,18.858,18.858,1.189781,0.094891,-0.270073,-0.452555,-0.562044,1,2,3,4,5,linear,...
```

## Flujo de Lectura (Left to Right)

Para analizar un paso específico, el orden lógico es:
1. Identificar el **momento temporal** (step, ts)
2. Ver el **valor real** (y_real)
3. Comparar **predicciones de cada modelo** (y_*)
4. Analizar **errores cometidos** (err_*, err_rel_*)
5. Observar **pesos del sistema** (w_*) - indicador de desempeño acumulado
6. Ver **rankings instantáneos** (rank_*) - quién fue mejor en ESE momento
7. Verificar **qué modelo fue elegido** (chosen_by_error) - la decisión tomada

## Casos de Uso

### 📊 Análisis de Desempeño
- Comparar predicciones vs real en un instante específico
- Analizar cómo evolucionan los errores a lo largo del tiempo
- Identificar períodos donde un modelo es especialmente bueno/malo

### 📈 Evolución de Pesos
- Ver cómo crece/decrece el weight de cada modelo
- Entender el impact de decisiones recientes en los pesos
- Detectar si hay "modelo favorito" que domine

### 🎯 Auditoría de Decisiones
- Verificar que `chosen_by_error` siempre corresponde al error mínimo
- Analizar si el algoritmo toma decisiones coherentes
- Comparar elecciones por error vs acumulación (memory effect)

### 🔄 Ranking vs Weights
- El **ranking** muestra el desempeño INSTANTÁNEO en cada paso
- Los **weights** muestran el desempeño ACUMULADO histórico
- Pueden divergir: un modelo puede tener ranking malo ahora pero weight alto por buen pasado

## Estadísticas Resumen (si se exportan)

Al final del documento o en análisis posterior:
- **Distribución de selecciones**: Cuántas veces fue elegido cada modelo
- **Evolución de pesos**: Inicial vs final para cada modelo
- **Performance relativo**: MAE, RMSE, MAPE por modelo
- **Consistency check**: % de aciertos en auditoría de selección

---

**Versión**: 2.0 (Actualizado Dec 2025)
**Descripción**: Estructura reorganizada para análisis ordenado y sistemático del ensemble adaptativo.
