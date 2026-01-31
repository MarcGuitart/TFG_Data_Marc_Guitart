#!/usr/bin/env python3
"""
Visual example of the new Export Report structure.
This script demonstrates the reorganized columns for analysis.
"""

import pandas as pd
from io import StringIO

# Ejemplo de datos con la estructura NUEVA (reorganizada)
csv_data = """step,ts,y_real,y_linear,y_poly,y_alphabeta,y_kalman,y_base,err_linear,err_poly,err_alphabeta,err_kalman,err_base,err_rel_linear,err_rel_poly,err_rel_alphabeta,err_rel_kalman,err_rel_base,w_linear,w_poly,w_alphabeta,w_kalman,w_base,rank_linear,rank_poly,rank_alphabeta,rank_kalman,rank_base,chosen_by_error
1,2025-03-10 00:30:00,0.106925,0.127089,0.127089,0.127089,0.127089,0.127089,0.020164,0.020164,0.020164,0.020164,0.020164,18.858436,18.858436,18.858436,18.858436,18.858436,1.189781,0.094891,-0.270073,-0.452555,-0.562044,1,2,3,4,5,linear
2,2025-03-10 01:00:00,0.08927,0.08676,0.106925,0.108739,0.088115,0.106925,0.00251,0.017655,0.019469,0.001155,0.017655,-2.811264,19.776759,21.809681,-1.293528,19.776759,1.094891,0.729927,0.437956,2.189781,0.547445,2,3,5,1,4,kalman
3,2025-03-10 01:30:00,0.074658,0.069942,0.074125,0.090821,0.070469,0.08927,0.004715,0.000533,0.016163,0.004189,0.014612,-6.316147,-0.713654,21.649356,-5.610719,19.572395,1.014599,1.014599,-1.394161,0.832117,-1.467153,3,1,5,2,4,poly"""

df = pd.read_csv(StringIO(csv_data))

print("=" * 120)
print("📊 EXPORT REPORT - NUEVA ESTRUCTURA (REORGANIZADA)")
print("=" * 120)
print()

print("📋 COLUMNAS POR SECCIÓN:\n")

# Sección 1: TEMPORAL
temporal_cols = ['step', 'ts']
print(f"1️⃣  TEMPORAL ({len(temporal_cols)} cols):")
print(f"    {temporal_cols}")
print()

# Sección 2: REAL
real_cols = ['y_real']
print(f"2️⃣  REAL ({len(real_cols)} col):")
print(f"    {real_cols}")
print()

# Sección 3: PREDICCIONES
pred_cols = [c for c in df.columns if c.startswith('y_') and c != 'y_real']
print(f"3️⃣  PREDICCIONES ({len(pred_cols)} cols):")
print(f"    {pred_cols}")
print()

# Sección 4: ERRORES ABSOLUTOS
err_cols = [c for c in df.columns if c.startswith('err_') and not c.startswith('err_rel_')]
print(f"4️⃣  ERRORES ABSOLUTOS ({len(err_cols)} cols):")
print(f"    {err_cols}")
print()

# Sección 5: ERRORES RELATIVOS
err_rel_cols = [c for c in df.columns if c.startswith('err_rel_')]
print(f"5️⃣  ERRORES RELATIVOS % ({len(err_rel_cols)} cols):")
print(f"    {err_rel_cols}")
print()

# Sección 6: WEIGHTS
w_cols = [c for c in df.columns if c.startswith('w_') and not c.startswith('w_pre_')]
print(f"6️⃣  WEIGHTS ACTUALES ({len(w_cols)} cols):")
print(f"    {w_cols}")
print()

# Sección 7: RANKING
rank_cols = [c for c in df.columns if c.startswith('rank_')]
print(f"7️⃣  RANKINGS ({len(rank_cols)} cols):")
print(f"    {rank_cols}")
print()

# Sección 8: DECISIÓN
decision_cols = [c for c in df.columns if c in ['chosen_by_error', 'chosen_by_weight']]
print(f"8️⃣  DECISIÓN ({len(decision_cols)} col):")
print(f"    {decision_cols}")
print()

print("=" * 120)
print("\n📊 DATOS MUESTRALES:\n")
print(df.to_string(index=False))
print()

print("=" * 120)
print("\n🔍 ANÁLISIS POR FILA (ejemplo: Row 1):\n")

row1 = df.iloc[0]
print(f"⏱️  TIEMPO:")
print(f"   Step: {row1['step']}")
print(f"   Timestamp: {row1['ts']}")
print()

print(f"📈 VALOR REAL:")
print(f"   y_real: {row1['y_real']:.6f}")
print()

print(f"🎯 PREDICCIONES:")
for col in pred_cols:
    print(f"   {col:12s}: {row1[col]:.6f}")
print()

print(f"❌ ERRORES COMETIDOS:")
for col in err_cols:
    print(f"   {col:12s}: {row1[col]:.6f}")
print()

print(f"📊 ERRORES RELATIVOS (%):")
for col in err_rel_cols:
    print(f"   {col:18s}: {row1[col]:7.2f}%")
print()

print(f"⚖️  WEIGHTS ACTUALES (después del update):")
for col in w_cols:
    print(f"   {col:12s}: {row1[col]:8.6f}")
print()

print(f"🏆 RANKINGS (1=mejor, 5=peor):")
for col in rank_cols:
    model = col.replace('rank_', '')
    rank = row1[col]
    medal = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else '📌'
    print(f"   {model:12s}: {int(rank)} {medal}")
print()

print(f"✅ MODELO ELEGIDO:")
print(f"   chosen_by_error: {row1['chosen_by_error']}")
print()

print("=" * 120)
print("\n💡 NOTAS IMPORTANTES:\n")
print("""
1. ORDEN DE COLUMNAS: Temporal → Real → Predicciones → Errores → Weights → Rankings → Decisión
   
2. WEIGHTS vs RANKINGS:
   - Ranking: muestra desempeño INSTANTÁNEO en ese step (basado en error)
   - Weight: muestra desempeño ACUMULADO (memoria del sistema)
   
3. chosen_by_error:
   - Siempre es el modelo con MENOR error absoluto en ese step
   - Es lo que se elige para la predicción final en modo "adaptive"
   
4. ANÁLISIS RECOMENDADO:
   ✓ Filtrar por chosen_by_error para ver cuándo ganó cada modelo
   ✓ Gráficas de evolución de weights para ver tendencias
   ✓ Scatter de ranking vs weight para entender desempeño
   ✓ Auditoría: verificar que chosen_by_error = modelo con err_* mínimo
""")
print("=" * 120)
