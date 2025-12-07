# 📚 GUÍA PARA PRESENTAR EN TU MEMORIA DEL TFG

**Cómo estructurar la explicación de AP1, AP2, AP3, AP4 en tu memoria**

---

## 📖 ESTRUCTURA RECOMENDADA PARA LA MEMORIA

### Capítulo: Implementación del Sistema Adaptativo

#### 4.1 Introducción
> "Este capítulo detalla la implementación de un sistema de selección de modelos adaptativo que evoluciona con el tiempo. Se presentan 4 Action Points (AP1-AP4) que progresivamente añaden complejidad y capacidad de análisis al sistema."

#### 4.2 AP1: Predicciones por Modelo
**Objetivo:** Visualizar y comparar predicciones individuales

**Implementación:**
```
┌────────────────┐
│  Datos brutos  │
└────────┬───────┘
         ↓
    ┌────────────────────┐
    │   HyperModel       │
    │ ┌────────────────┐ │
    │ │ Model 1        │ │ → y_hat_1
    │ │ Model 2        │ │ → y_hat_2
    │ │ Model 3        │ │ → y_hat_3
    │ │ ...            │ │ → y_hat_n
    │ └────────────────┘ │
    └────────┬───────────┘
             ↓
    Visualizar en Frontend
    (Gráficas individuales)
```

**Código Clave (Backend):**
```python
def predict(self, series: Sequence[float]) -> Tuple[float, Dict[str, float]]:
    preds = {m.name: float(m.predict(series)) for m in self.models}
    # preds contiene una predicción por cada modelo
    return y_hat_combined, preds
```

**Beneficios:**
- Visualizar desempeño individual de cada modelo
- Identificar qué modelo es más errático o más suave
- Base para decisiones posteriores

---

#### 4.3 AP2: Selector Adaptativo
**Objetivo:** Elegir automáticamente el mejor modelo en cada paso

**Implementación:**
```
┌──────────────────────────────────┐
│ Predicciones de todos los modelos│
│ {model_1: 0.5, model_2: 0.7}     │
└────────────────┬─────────────────┘
                 ↓
         ┌──────────────────┐
         │ Valor Real (t)   │
         │ y_real = 0.6     │
         └────────┬─────────┘
                  ↓
      ┌───────────────────────┐
      │ Calcular Errores      │
      │ err_1 = |0.5 - 0.6|   │
      │ err_2 = |0.7 - 0.6|   │
      └───────────┬───────────┘
                  ↓
      ┌───────────────────────┐
      │ Seleccionar Mejor     │
      │ model_1 (err_1 < err_2)
      │ chosen = model_1      │
      └───────────┬───────────┘
                  ↓
    Usar para próxima predicción
```

**Código Clave (Backend):**
```python
def update_selection(self, y_true: float):
    errors = {m: abs(self._last_preds[m] - y_true) 
              for m in self.model_names}
    best_model = min(errors.keys(), key=lambda m: errors[m])
    # best_model es el elegido
    return best_model, errors
```

**Beneficios:**
- Sistema adaptativo "real-time"
- Elige mejor modelo sin supervisión
- Ventaja sobre elegir siempre el mismo

**Ventaja sobre AP1:**
> AP1 solo visualiza. AP2 toma decisiones automáticas basadas en errores.

---

#### 4.4 AP3: Evolución de Pesos (Ranking con Memoria) ⭐
**Objetivo:** Sistema de pesos que "recuerda" performance histórica

**El Problema que Resuelve:**
> AP2 elige el mejor modelo en t-1 para predecir t. Pero ¿y si ese modelo fue pura suerte? ¿Y si otro modelo ha sido consistentemente mejor?

**La Solución: Sistema de Pesos con Memoria**

```
ALGORITMO (en cada timestep):

1) DECADENCIA (reparto equitativo)
   total_reward = N * (N+1) / 2        # p.ej. 3 modelos → 6 puntos
   decay_per_model = total_reward / N  # 2 puntos por modelo
   para cada modelo:
       w[modelo] -= decay_per_model

2) RANKING POR ERROR
   ranked = sorted(modelos, key=error)  # menor error primero
   # Ejemplo: [modelo_A (0.01), modelo_B (0.05), modelo_C (0.10)]

3) RECOMPENSA
   w[modelo_A] += 3  (mejor)
   w[modelo_B] += 2  (segundo)
   w[modelo_C] += 1  (tercero)

4) SELECCIÓN PARA PRÓXIMA PREDICCIÓN
   chosen = argmax(w)  # El de mayor peso
```

**Visualización de Evolución:**

```
Tiempo →
Peso ↑
 10 |     ╭─╮
    |    ╭─╯ ╰─╮
  5 |───╯       ╰──╮
    |              ╰─
  0 |────────────────
    |
-5  |════════════════ (modelo C)
    └─────────────────
    
Modelo A: consistentemente alto
Modelo B: variaciones normales
Modelo C: hundido (historial pobre)
```

**Código Clave (Backend):**
```python
def update_weights(self, y_true: float):
    # 1. Decadencia
    total_reward = len(self.models) * (len(self.models) + 1) // 2
    decay_share = total_reward / len(self.models)
    for m in self.models:
        self.w[m] -= decay_share
    
    # 2. Ranking
    ranked = sorted(self.models, key=lambda m: self.errors[m])
    
    # 3. Recompensa
    for idx, model in enumerate(ranked):
        reward = len(self.models) - idx
        self.w[model] += reward
    
    # 4. Guardar en historial
    self._history.append({
        'timestamp': now,
        'weights': dict(self.w),
        'errors': dict(self.errors),
        'chosen_by_weight': argmax(self.w)
    })
```

**Beneficios:**
- **Memoria:** Los pesos reflejan desempeño histórico, no solo puntual
- **Robustez:** Evita elegir modelos por suerte ocasional
- **Análisis:** Puedes ver qué modelo fue mejor "en promedio"
- **Justificación TFG:** "Implementé un sistema de ranking acumulativo..."

**CSV Generado (para análisis offline):**
```csv
timestamp,y_real,y_model_a,y_model_b,y_model_c,...,
          err_a,err_b,err_c,...,
          w_a,w_b,w_c,...,
          chosen_by_error,chosen_by_weight
2024-01-01T00:00,1.5,1.48,1.52,1.45,...,0.02,0.02,0.05,...,
                  8.5,6.2,2.1,...,model_a,model_a
2024-01-01T01:00,1.6,1.58,1.62,1.65,...,0.02,0.02,0.05,...,
                  7.3,5.1,1.2,...,model_a,model_a
```

---

#### 4.5 AP4: Tabla de Métricas Top-3 con Ranking
**Objetivo:** Resumen visual del mejor ranking + justificación cuantitativa

**Lo que muestra:**

```
🏆 MODEL RANKING (AP4 - by Weight)

┌─────┬──────────┬────────┬──────────┬──────────┬─────────┬────┐
│ Rank│ Model    │ Weight │ MAE      │ RMSE     │ MAPE(%) │ n  │
├─────┼──────────┼────────┼──────────┼──────────┼─────────┼────┤
│ 🥇  │ Model_A  │ 45.20  │ 0.012345 │ 0.018765 │ 3.45    │ 500│
├─────┼──────────┼────────┼──────────┼──────────┼─────────┼────┤
│ 🥈  │ Model_B  │ 8.10   │ 0.023456 │ 0.035678 │ 5.67    │ 500│
├─────┼──────────┼────────┼──────────┼──────────┼─────────┼────┤
│ 🥉  │ Model_C  │-12.30  │ 0.045678 │ 0.067890 │ 8.90    │ 500│
└─────┴──────────┴────────┴──────────┴──────────┴─────────┴────┘

Top-3: 🥇 Model_A • 🥈 Model_B • 🥉 Model_C
```

**Lectura de Resultados:**

| Aspecto | Observación | Interpretación |
|---------|-------------|-----------------|
| **Weight** | Model_A tiene 45.20, otros mucho menores | Model_A fue consistently mejor |
| **MAE** | Model_A: 0.012345 (menor) | Confirma que errores fueron bajos |
| **RMSE** | Model_A tiene el RMSE más bajo | Varianza de errores menor |
| **MAPE** | Model_A: 3.45% (mínimo) | Error relativo bajo |
| **Coherencia** | Weight corrobora métricas | Sistema de pesos funciona bien |

**Narrativa para TFG:**

> "El sistema de ranking AP3 (weights) ordena los modelos de forma coherente con las métricas clásicas (MAE, RMSE, MAPE). 
> 
> El modelo con mayor weight acumulado (Model_A, 45.20) tiene el error absoluto más bajo (MAE 0.012345), el error cuadrático más bajo (RMSE 0.018765) y el error relativo más bajo (MAPE 3.45%).
> 
> Esto demuestra que el sistema de pesos refleja correctamente el desempeño histórico y es una métrica válida para ranking de modelos."

---

## 🎨 DIAGRAMAS RECOMENDADOS PARA MEMORIA

### Arquitectura General

```
┌──────────────────────────────────────────────────────────┐
│                       FRONTEND (React)                   │
│  ┌──────────────┬──────────────┬──────────────────────┐  │
│  │ AP1: Gráficas│ AP2: Selector│ AP3: Evolución Pesos │  │
│  │ Individuales │  Adaptativo  │  (Historia + Stats)  │  │
│  │              │              │                      │  │
│  │  Líneas de   │ Tabla de     │ Gráfica de pesos +   │  │
│  │  predicción  │ modelos      │ Panel de exportar    │  │
│  │  por modelo  │ elegidos     │                      │  │
│  └──────────────┴──────────────┴──────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ AP4: Tabla de Ranking (Top-3 + Weights)           │  │
│  │ 🥇 Model A | Weight: 45.2 | MAE: 0.012           │  │
│  │ 🥈 Model B | Weight: 8.1  | MAE: 0.023           │  │
│  │ 🥉 Model C | Weight: -12.3| MAE: 0.045           │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
           ↓ API Calls ↓
┌──────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                    │
│                                                          │
│  /api/series → Predicciones + selección (AP1, AP2)      │
│  /api/agent/history → Historial de pesos (AP3)          │
│  /api/agent/stats → Estadísticas de weights (AP3)       │
│  /api/metrics/models → Ranking + métricas (AP4)         │
│                                                          │
└──────────────────────────────────────────────────────────┘
           ↓ Queries ↓
┌──────────────────────────────────────────────────────────┐
│              DATA LAYER (InfluxDB)                       │
│                                                          │
│  telemetry: observed, telemetry_models: predictions     │
│  weights: weight evolution (AP3)                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Flujo de Decisión

```
TIEMPO t:

Datos históricos [y_1, y_2, ..., y_t-1]
          ↓
    ┌─────────────────────┐
    │  Generador de       │ Predicciones: {m1: y_hat_1, m2: y_hat_2, ...}
    │  Predicciones (AP1) │
    └─────────┬───────────┘
              ↓
    ┌─────────────────────┐
    │  Se revela y_t      │
    │  (valor real)       │
    └─────────┬───────────┘
              ↓
    ┌─────────────────────────────────────────┐
    │  Calcular Errores (AP2)                 │
    │  - Error m1: |y_hat_1 - y_t|            │
    │  - Error m2: |y_hat_2 - y_t|            │
    │  Elegir: best = argmin(errores)         │
    └─────────┬───────────────────────────────┘
              ↓
    ┌─────────────────────────────────────────┐
    │  Actualizar Pesos (AP3)                 │
    │  1. Restar decadencia a todos           │
    │  2. Ordenar por error                   │
    │  3. Dar recompensas (3,2,1,...)         │
    │  4. Guardar en historial                │
    └─────────┬───────────────────────────────┘
              ↓
    ┌─────────────────────────────────────────┐
    │  Generar Ranking (AP4)                  │
    │  chosen = argmax(w)  ← para próxima!   │
    │  Mostrar tabla: Weight | MAE | RMSE    │
    └────────────────────────────────────────┘

TIEMPO t+1:
Usar modelo elegido (argmax(w)) para predicción siguiente
```

---

## 📊 TABLA COMPARATIVA PARA MEMORIA

| Aspecto | AP1 | AP2 | AP3 | AP4 |
|---------|-----|-----|-----|-----|
| **Visualiza predicciones** | ✅ | ✅ | ✅ | ✅ |
| **Elige automáticamente** | ❌ | ✅ | ✅ | ✅ |
| **Con memoria** | ❌ | ❌ | ✅ | ✅ |
| **Ranking justificado** | ❌ | ❌ | ✅ | ✅ |
| **Tabla de métricas** | ❌ | ❌ | ❌ | ✅ |
| **Exporta CSV** | ❌ | ❌ | ✅ | ✅ |

---

## 💬 FRASES RECOMENDADAS PARA MEMORIA

### Para Introducción
> "Se implementó un sistema de selección de modelos que evoluciona en el tiempo, progresivamente incorporando complejidad desde la visualización simple (AP1) hasta ranking justificado (AP4)."

### Para AP1
> "Permitiendo visualizar el comportamiento de cada modelo de forma independiente, se puede observar cuál es más conservador, cuál oscila más, y cuáles son patrones emergentes."

### Para AP2
> "A diferencia de un sistema que elige un único modelo fijo, el selector adaptativo permite que el mejor modelo cambie en función de la calidad de sus predicciones recientes."

### Para AP3
> "El sistema de pesos implementa una estrategia de 'memory' que no castiga permanentemente un error aislado. En su lugar, calcula un ranking acumulativo que refleja el desempeño histórico."

### Para AP4
> "La coherencia entre el ranking de pesos (AP3) y las métricas clásicas (MAE, RMSE, MAPE) valida que el sistema de pesos es una métrica significativa que refleja el verdadero desempeño de los modelos."

---

## 🎯 RESULTADOS ESPERADOS EN MEMORIA

### Figura 1: Gráfica de AP1
Mostrar serie con múltiples líneas de predicción

### Figura 2: Tabla de AP2
Mostrar tabla de modelos elegidos y errores

### Figura 3: Gráfica de AP3
Mostrar evolución de pesos en el tiempo

### Figura 4: Tabla de AP4
Mostrar ranking con Top-3 y métricas

---

## 📄 EJEMPLO DE TEXTO PARA RESULTADOS

> **4.6 Resultados y Validación**
>
> Se ejecutó el sistema con un dataset de 500 puntos. Los resultados muestran:
>
> 1. **AP1-AP2 Funcionamiento:** El sistema eligió el mejor modelo en el 87% de los timesteps coincidiendo con el modelo de menor error puntual.
>
> 2. **AP3 Memoria:** El modelo con mayor peso final (45.2) fue seleccionado 78 veces en los últimos 100 timesteps, vs. 12 veces para el modelo con menor peso (-12.3).
>
> 3. **AP4 Coherencia:** La correlación entre weight y MAE fue de 0.92, demostrando que el sistema de pesos refleja correctamente el desempeño.
>
> **Conclusión:** El sistema de ranking adaptativo es efectivo y proporciona un ordering coherente de modelos basado en su desempeño histórico.

---

¡Espero que esto te ayude a estructurar la memoria del TFG! 🎓
