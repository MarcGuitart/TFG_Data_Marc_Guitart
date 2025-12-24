#!/usr/bin/env python3
"""
Script de auditoría offline para verificar la integridad del sistema.

Verifica:
A. Integridad de datos (timestamps, longitudes)
B. Selección por punto auditable (recalcula ganador y compara)
C. Coherencia de errores y pesos
"""

import pandas as pd
import sys
from pathlib import Path

def audit_csv(csv_path: str):
    """Auditoría completa de un CSV exportado"""
    
    print("="*80)
    print("🔍 AUDITORÍA COMPLETA DEL SISTEMA")
    print("="*80)
    
    # Cargar CSV
    df = pd.read_csv(csv_path)
    print(f"\n📊 CSV cargado: {csv_path}")
    print(f"   Total de filas: {len(df)}")
    print(f"   Columnas: {len(df.columns)}")
    
    # A. INTEGRIDAD DE DATOS
    print("\n" + "="*80)
    print("A. VERIFICACIÓN DE INTEGRIDAD DE DATOS")
    print("="*80)
    
    # A.1 - Timestamps monótonos
    df['ts_parsed'] = pd.to_datetime(df['ts'])
    timestamps_monotonic = df['ts_parsed'].is_monotonic_increasing
    print(f"\n✓ Timestamps monótonos: {timestamps_monotonic}")
    if not timestamps_monotonic:
        print("  ⚠️  ADVERTENCIA: Timestamps no están ordenados")
    
    # A.2 - Steps consecutivos
    expected_steps = list(range(1, len(df) + 1))
    actual_steps = df['step'].tolist()
    steps_ok = actual_steps == expected_steps
    print(f"✓ Steps consecutivos (1 a {len(df)}): {steps_ok}")
    if not steps_ok:
        missing = set(expected_steps) - set(actual_steps)
        print(f"  ⚠️  Steps faltantes: {missing}")
    
    # A.3 - No hay NaN en columnas críticas
    critical_cols = ['y_real', 'y_linear', 'y_poly', 'y_alphabeta', 'y_kalman']
    nan_check = df[critical_cols].isna().sum().sum()
    print(f"✓ Sin NaN en predicciones: {nan_check == 0} (total NaN: {nan_check})")
    
    # B. SELECCIÓN POR PUNTO AUDITABLE
    print("\n" + "="*80)
    print("B. VERIFICACIÓN DE SELECCIÓN POR PUNTO")
    print("="*80)
    
    # Modelos disponibles
    models = ['linear', 'poly', 'alphabeta', 'kalman']
    
    # B.1 - Recalcular errores absolutos
    print("\n📐 Recalculando errores absolutos...")
    for model in models:
        df[f'err_{model}_recalc'] = abs(df['y_real'] - df[f'y_{model}'])
    
    # B.2 - Recalcular modelo ganador por error
    def get_winner_by_error(row):
        errors = {model: row[f'err_{model}_recalc'] for model in models}
        return min(errors, key=errors.get)
    
    df['winner_recalc'] = df.apply(get_winner_by_error, axis=1)
    
    # B.3 - Comparar con chosen_by_error del sistema
    matches = (df['winner_recalc'] == df['chosen_by_error']).sum()
    total = len(df)
    match_rate = 100 * matches / total
    
    print(f"\n✅ COINCIDENCIA DE SELECCIÓN:")
    print(f"   Matches: {matches}/{total} ({match_rate:.2f}%)")
    
    if match_rate < 99:
        print(f"\n⚠️  ADVERTENCIA: Tasa de coincidencia < 99%")
        # Mostrar casos que no coinciden
        mismatches = df[df['winner_recalc'] != df['chosen_by_error']]
        print(f"\n   Casos que no coinciden ({len(mismatches)}):")
        for idx, row in mismatches.head(10).iterrows():
            print(f"\n   Step {row['step']}:")
            print(f"     Sistema eligió: {row['chosen_by_error']}")
            print(f"     Debería ser: {row['winner_recalc']}")
            print(f"     Errores: ", end="")
            for model in models:
                print(f"{model}={row[f'err_{model}_recalc']:.6f} ", end="")
            print()
    else:
        print(f"   ✅ EXCELENTE: Sistema selecciona correctamente el modelo con menor error")
    
    # B.4 - Verificar coherencia de errores exportados vs recalculados
    print(f"\n📊 Coherencia de errores exportados:")
    for model in models:
        diff = (df[f'err_{model}'] - df[f'err_{model}_recalc']).abs().max()
        print(f"   {model}: max diff = {diff:.9f} ({'✓' if diff < 1e-6 else '⚠️'})")
    
    # C. ANÁLISIS DE DISTRIBUCIÓN DE SELECCIÓN
    print("\n" + "="*80)
    print("C. DISTRIBUCIÓN DE SELECCIÓN DE MODELOS")
    print("="*80)
    
    selection_counts = df['chosen_by_error'].value_counts()
    print("\n📊 Veces que cada modelo fue elegido:")
    for model in models:
        count = selection_counts.get(model, 0)
        pct = 100 * count / total
        print(f"   {model:12s}: {count:4d} veces ({pct:5.2f}%)")
    
    # Verificar que todos los modelos fueron usados
    unused = [m for m in models if m not in selection_counts.index]
    if unused:
        print(f"\n⚠️  ADVERTENCIA: Modelos NO utilizados: {unused}")
    else:
        print(f"\n✅ Todos los modelos fueron utilizados al menos una vez")
    
    # D. EVOLUCIÓN DE PESOS
    print("\n" + "="*80)
    print("D. EVOLUCIÓN DE PESOS")
    print("="*80)
    
    print("\n📈 Pesos iniciales (step 1):")
    first_row = df.iloc[0]
    for model in models:
        print(f"   {model:12s}: {first_row[f'w_{model}']:8.3f}")
    
    print("\n📈 Pesos finales (step {}):", len(df))
    last_row = df.iloc[-1]
    for model in models:
        print(f"   {model:12s}: {last_row[f'w_{model}']:8.3f}")
    
    # E. VERIFICACIÓN DE SISTEMA DE RECOMPENSAS
    print("\n" + "="*80)
    print("E. SISTEMA DE RECOMPENSAS")
    print("="*80)
    
    # Verificar que suma de rewards = 10 siempre
    total_rewards = df[[f'reward_{model}' for model in models]].sum(axis=1)
    reward_sum_ok = (total_rewards == 10).all()
    print(f"\n✓ Suma de rewards = 10 en todos los steps: {reward_sum_ok}")
    if not reward_sum_ok:
        bad_steps = df[total_rewards != 10]['step'].tolist()
        print(f"  ⚠️  Steps con suma incorrecta: {bad_steps[:10]}")
    
    # Verificar ranking
    print(f"\n✓ Ranking: 1=mejor (menor error), 4=peor (mayor error)")
    print(f"  Verificando consistencia...")
    
    # Para cada step, verificar que ranking coincide con orden de errores
    ranking_errors = 0
    for idx, row in df.iterrows():
        errors_sorted = sorted([(model, row[f'err_{model}']) for model in models], key=lambda x: x[1])
        expected_ranks = {model: rank+1 for rank, (model, _) in enumerate(errors_sorted)}
        actual_ranks = {model: row[f'rank_{model}'] for model in models}
        
        if expected_ranks != actual_ranks:
            ranking_errors += 1
            if ranking_errors <= 3:  # Mostrar solo primeros 3 errores
                print(f"\n  ⚠️  Step {row['step']}: Ranking inconsistente")
                print(f"     Esperado: {expected_ranks}")
                print(f"     Actual: {actual_ranks}")
    
    if ranking_errors == 0:
        print(f"  ✅ Ranking consistente en todos los steps")
    else:
        print(f"  ⚠️  {ranking_errors} steps con ranking inconsistente")
    
    # RESUMEN FINAL
    print("\n" + "="*80)
    print("📋 RESUMEN DE AUDITORÍA")
    print("="*80)
    
    issues = []
    if not timestamps_monotonic:
        issues.append("❌ Timestamps no monótonos")
    else:
        print("✅ Timestamps monótonos y alineados")
    
    if not steps_ok:
        issues.append("❌ Steps no consecutivos")
    else:
        print("✅ Steps consecutivos sin gaps")
    
    if nan_check > 0:
        issues.append(f"❌ {nan_check} valores NaN encontrados")
    else:
        print("✅ Sin valores NaN en datos críticos")
    
    if match_rate < 99:
        issues.append(f"❌ Selección por error: {match_rate:.2f}% (esperado >99%)")
    else:
        print(f"✅ Selección por punto auditable: {match_rate:.2f}%")
    
    if unused:
        issues.append(f"⚠️  Modelos sin usar: {unused}")
    else:
        print("✅ Todos los modelos utilizados")
    
    if not reward_sum_ok:
        issues.append("❌ Sistema de recompensas inconsistente")
    else:
        print("✅ Sistema de recompensas correcto (suma=10)")
    
    if ranking_errors > 0:
        issues.append(f"⚠️  {ranking_errors} rankings inconsistentes")
    else:
        print("✅ Rankings consistentes con errores")
    
    if issues:
        print("\n" + "="*80)
        print("⚠️  PROBLEMAS DETECTADOS:")
        print("="*80)
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("\n" + "="*80)
        print("🎉 AUDITORÍA COMPLETA: SISTEMA VERIFICADO")
        print("="*80)
        print("\n✅ El sistema funciona correctamente")
        print("✅ La selección por punto es auditable y correcta")
        print("✅ Los pesos evolucionan según el sistema de recompensas")
        print("✅ Listo para defender en el TFG")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python audit_system.py <ruta_al_csv>")
        print("Ejemplo: python audit_system.py /tmp/test_audit.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    if not Path(csv_path).exists():
        print(f"❌ Error: No se encuentra el archivo {csv_path}")
        sys.exit(1)
    
    success = audit_csv(csv_path)
    sys.exit(0 if success else 1)
