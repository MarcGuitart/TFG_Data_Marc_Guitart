#!/usr/bin/env python3
"""
BLOQUE 6: Análisis de Escenarios Experimentales

Compara performance del HyperModel en los 3 escenarios.

Uso:
    python utils/analyze_escenarios.py \
        data/dades_traffic_escenari0.csv \
        data/dades_traffic_escenari1.csv \
        data/dades_traffic_escenari2.csv
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

def load_scenario(csv_path):
    """Carga un CSV de escenario y retorna DataFrame"""
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        print(f"❌ Error cargando {csv_path}: {e}")
        return None

def analyze_scenario(name, df, expected_pattern=None):
    """
    Analiza estadísticas básicas de un escenario
    
    Args:
        name: Nombre del escenario (ej: "Escenario 0: Baseline")
        df: DataFrame con columnas [timestamp, id, value]
        expected_pattern: Descripción del patrón esperado
    """
    print(f"\n{'='*70}")
    print(f"📊 {name}")
    print(f"{'='*70}")
    
    if df is None or df.empty:
        print("   ❌ DataFrame vacío")
        return None
    
    # Estadísticas básicas
    print(f"\n📈 Dimensiones:")
    print(f"   - Puntos: {len(df)}")
    print(f"   - Duración: {len(df) * 0.5:.1f} horas ({len(df) * 0.5 / 24:.1f} días)")
    print(f"   - Intervalo: 30 minutos")
    
    # Valores
    values = df['value'].values
    print(f"\n📊 Estadísticas de Valores:")
    print(f"   - Media:     {values.mean():.6f}")
    print(f"   - Std Dev:   {values.std():.6f}")
    print(f"   - Mínimo:    {values.min():.6f}")
    print(f"   - Máximo:    {values.max():.6f}")
    print(f"   - Rango:     {values.max() - values.min():.6f}")
    
    # Detectar cambios bruscos (Escenario 1)
    diffs = np.diff(values)
    max_change = np.max(np.abs(diffs))
    max_change_idx = np.argmax(np.abs(diffs))
    
    print(f"\n⚡ Cambios:")
    print(f"   - Cambio máximo: {diffs[max_change_idx]:.6f} en punto {max_change_idx}")
    print(f"   - % Cambio:      {(diffs[max_change_idx] / values[max_change_idx]) * 100:.2f}%")
    
    # Detectar ruido (varianza)
    rolling_std = pd.Series(values).rolling(window=12, center=True).std()
    print(f"\n🔊 Ruido/Variabilidad:")
    print(f"   - Std Dev rolling (12pt): min={rolling_std.min():.6f}, max={rolling_std.max():.6f}")
    print(f"   - Aumento de ruido: {(rolling_std.max() - rolling_std.min()):.6f}")
    
    if expected_pattern:
        print(f"\n💡 Patrón Esperado:")
        print(f"   {expected_pattern}")
    
    return {
        'name': name,
        'n_points': len(df),
        'mean': values.mean(),
        'std': values.std(),
        'min': values.min(),
        'max': values.max(),
        'max_change': diffs[max_change_idx],
        'max_change_idx': max_change_idx,
        'rolling_std_max': rolling_std.max(),
    }

def compare_scenarios(results):
    """Crea tabla comparativa de escenarios"""
    print(f"\n\n{'='*70}")
    print("📋 TABLA COMPARATIVA DE ESCENARIOS")
    print(f"{'='*70}\n")
    
    print(f"{'Métrica':<25} {'Escenario 0':<18} {'Escenario 1':<18} {'Escenario 2':<18}")
    print("-" * 80)
    
    # Puntos
    print(f"{'Puntos':<25} {results[0]['n_points']:<18} {results[1]['n_points']:<18} {results[2]['n_points']:<18}")
    
    # Media
    print(f"{'Media':<25} {results[0]['mean']:<18.6f} {results[1]['mean']:<18.6f} {results[2]['mean']:<18.6f}")
    
    # Desv Est
    print(f"{'Std Dev':<25} {results[0]['std']:<18.6f} {results[1]['std']:<18.6f} {results[2]['std']:<18.6f}")
    
    # Cambio máximo
    print(f"{'Cambio Máximo':<25} {results[0]['max_change']:<18.6f} {results[1]['max_change']:<18.6f} {results[2]['max_change']:<18.6f}")
    
    # Punto del cambio
    print(f"{'Punto Cambio Máx':<25} {results[0]['max_change_idx']:<18} {results[1]['max_change_idx']:<18} {results[2]['max_change_idx']:<18}")
    
    print("\n")

def predict_behavior(results):
    """Predice comportamiento esperado en el HyperModel"""
    print(f"\n{'='*70}")
    print("🎯 PREDICCIONES DE COMPORTAMIENTO DEL HYPERMODEL")
    print(f"{'='*70}\n")
    
    print("ESCENARIO 0 (Baseline):")
    print("  ✅ Error esperado: < 5%")
    print("  ✅ Modelo dominante: Lineal o Kalman")
    print("  ✅ Pesos AP3: Estables")
    print("  💡 Propósito: Establecer línea base de precisión")
    
    print("\nESCENARIO 1 (Cambio Brusco):")
    print(f"  ⚡ Cambio brusco detectado en punto {results[1]['max_change_idx']}")
    print(f"  ⚡ Magnitud: {results[1]['max_change']:.6f} ({(results[1]['max_change'] / results[1]['mean']) * 100:.1f}% de la media)")
    print("  ❓ Error esperado: Pico >20% en cambio, luego recuperación a <5%")
    print("  ❓ Modelo esperado: Cambio de modelo (Lineal → Kalman probablemente)")
    print("  ❓ AP3 esperado: Ajuste rápido de pesos")
    print("  💡 Propósito: Validar ADAPTABILIDAD ante cambio de régimen")
    
    print("\nESCENARIO 2 (Ruido Creciente):")
    if results[2]['rolling_std_max'] > results[2]['rolling_std_max'] * 0.1:
        print(f"  🔊 Ruido detectado: std aumenta {results[2]['rolling_std_max']:.6f}")
    print("  ❓ Error esperado: 5% → 10-15% (gradual)")
    print("  ❓ Modelo esperado: Kalman dominante (suavizado)")
    print("  ❓ AP3 esperado: Ajuste gradual hacia modelos robustos")
    print("  💡 Propósito: Validar ROBUSTEZ ante variabilidad")
    
    print("\n")

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        print("\nUso:")
        print("  python utils/analyze_escenarios.py \\")
        print("    data/dades_traffic_escenari0.csv \\")
        print("    data/dades_traffic_escenari1.csv \\")
        print("    data/dades_traffic_escenari2.csv")
        sys.exit(1)
    
    # Cargar escenarios
    print("🔄 Cargando escenarios...\n")
    
    df0 = load_scenario(sys.argv[1])
    df1 = load_scenario(sys.argv[2])
    df2 = load_scenario(sys.argv[3])
    
    if not all([df0 is not None, df1 is not None, df2 is not None]):
        print("❌ Error cargando uno o más archivos")
        sys.exit(1)
    
    # Analizar cada escenario
    results = []
    
    results.append(analyze_scenario(
        "ESCENARIO 0: Baseline (Comportamiento Normal)",
        df0,
        "Datos limpios con patrón sinusoidal típico de tráfico. Sin cambios ni ruido."
    ))
    
    results.append(analyze_scenario(
        "ESCENARIO 1: Cambio Brusco (Robustez ante Cambio de Régimen)",
        df1,
        "Datos normales hasta mitad de la serie, luego cambio de régimen abrupto. Prueba ADAPTABILIDAD."
    ))
    
    results.append(analyze_scenario(
        "ESCENARIO 2: Ruido Creciente (Robustez ante Degradación)",
        df2,
        "Datos clean inicialmente, luego ruido aleatorio ±8% agregado. Prueba ROBUSTEZ."
    ))
    
    # Tabla comparativa
    compare_scenarios(results)
    
    # Predicciones
    predict_behavior(results)
    
    # Conclusión
    print(f"{'='*70}")
    print("✨ ANÁLISIS COMPLETO")
    print(f"{'='*70}")
    print("""
Pasos siguientes para la Memoria:

1. EJECUTAR LOS ESCENARIOS en el pipeline:
   - Subir cada CSV al frontend (KafkaInUploader)
   - Esperar 10-15 minutos por escenario
   - Observar dashboards AP1, AP2, AP3, AP4

2. RECOLECTAR MÉTRICAS:
   - Error absoluto por escenario
   - Error relativo por escenario
   - Distribución de modelos seleccionados (AP2)
   - Evolución de pesos AP3

3. COMPARAR CON PREDICCIONES:
   - ¿AP3 detectó el cambio en Escenario 1?
   - ¿Recuperó el error rápidamente?
   - ¿En Escenario 2, favoreció modelos más robustos?

4. DOCUMENTAR RESULTADOS:
   - Tablas de precisión por escenario
   - Gráficas de evolución AP3
   - Conclusión: "Adaptabilidad validada"
""")

if __name__ == "__main__":
    main()
