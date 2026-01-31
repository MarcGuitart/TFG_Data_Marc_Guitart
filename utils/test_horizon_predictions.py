#!/usr/bin/env python3
"""
TEST: Verificar que los modelos generan predicciones DIFERENTES para T+1 vs T+M

Este script prueba directamente los modelos para confirmar que:
1. Con horizon=1, obtenemos un valor
2. Con horizon=5, obtenemos un valor DIFERENTE

Si los valores son iguales, hay un bug.
"""
import sys
sys.path.insert(0, '/Users/marcg/Desktop/projectes/TFG_Agente_Data/services/agent')

from hypermodel.linear_model import LinearModel
from hypermodel.poly_model import PolyModel
from hypermodel.kalman_model import KalmanModel
from hypermodel.alphabeta import AlphaBetaModel
from hypermodel.naive_model import NaiveModel

# Serie de prueba (valores simulando tráfico creciente)
test_series = [100.0, 102.0, 105.0, 103.0, 107.0, 110.0, 108.0, 112.0, 115.0, 118.0]

print("=" * 70)
print("TEST: Verificando predicciones para diferentes horizontes")
print("=" * 70)
print(f"\nSerie de entrada: {test_series}")
print(f"Longitud: {len(test_series)} puntos")
print()

# Inicializar modelos
models = [
    ("Linear", LinearModel("linear", window=8)),
    ("Poly", PolyModel("poly", degree=2, window=8)),
    ("Kalman", KalmanModel("kalman", dt=1.0, q_pos=0.001, q_vel=0.001, r=0.01)),
    ("AlphaBeta", AlphaBetaModel("alphabeta", alpha=0.85, beta=0.01, dt=1.0)),
    ("Naive", NaiveModel("naive")),
]

# Horizontes a probar
horizons = [1, 2, 5, 10]

print("Predicciones por modelo y horizonte:")
print("-" * 70)

for model_name, model in models:
    preds = []
    for h in horizons:
        pred = model.predict(test_series, horizon=h)
        preds.append(pred)
    
    # Verificar si todos son iguales (sería un bug para modelos que no sean naive)
    all_same = len(set(round(p, 4) for p in preds)) == 1
    status = "⚠️ TODOS IGUALES" if all_same else "✅ DIFERENTES"
    
    # Para Naive es esperado que sean iguales
    if model_name == "Naive":
        status = "✅ OK (Naive siempre repite último valor)"
    
    print(f"\n{model_name} {status}:")
    for h, p in zip(horizons, preds):
        print(f"  T+{h}: {p:.4f}")

print("\n" + "=" * 70)
print("RESUMEN:")
print("=" * 70)
print("""
Si ves "TODOS IGUALES" en modelos que NO son Naive, hay un bug.
Los modelos Linear, Poly, Kalman y AlphaBeta DEBEN dar valores diferentes
para diferentes horizontes, porque extrapolan más lejos en el tiempo.
""")

# Test adicional: verificar diferencias numéricas
print("\nDiferencia entre T+1 y T+5:")
for model_name, model in models:
    pred_1 = model.predict(test_series, horizon=1)
    pred_5 = model.predict(test_series, horizon=5)
    diff = pred_5 - pred_1
    print(f"  {model_name}: T+1={pred_1:.4f}, T+5={pred_5:.4f}, diff={diff:.4f}")
