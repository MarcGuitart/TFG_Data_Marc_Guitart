#!/usr/bin/env python3
"""
BLOQUE 5: Generador de escenarios experimentales.

Crea 3 archivos CSV para demostración:
1. escenario_base.csv    - Datos originales sin cambios
2. escenario_cambio.csv  - Con cambio de régimen a mitad de la serie
3. escenario_ruido.csv   - Con ruido aleatorio añadido

Uso:
    python utils/generate_scenarios.py <source_csv> <output_dir>

Ejemplo:
    python utils/generate_scenarios.py data/dades_traffic.csv data/
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

def generate_base_scenario(df, output_path):
    """Escenario 1: Copia del original (sin cambios)"""
    df.to_csv(output_path, index=False)
    print(f"✅ Escenario BASE: {output_path} ({len(df)} filas)")

def generate_change_scenario(df, output_path, change_point_pct=0.5):
    """
    Escenario 2: Cambio de comportamiento a mitad de la serie.
    
    - Toma los primeros `change_point_pct` de la serie
    - Genera datos alterados para el resto (mayor ruido, escala diferente)
    """
    split_idx = int(len(df) * change_point_pct)
    df_first = df.iloc[:split_idx].copy()
    df_second = df.iloc[split_idx:].copy()
    
    # Modificar segunda mitad: aplicar cambio de escala + ruido
    if "count" in df_second.columns:
        # Aumentar media y añadir ruido
        mean_val = df_second["count"].mean()
        df_second["count"] = df_second["count"] * 1.3 + np.random.normal(0, mean_val * 0.15, len(df_second))
        df_second["count"] = df_second["count"].clip(lower=0)  # No negativos
    
    df_result = pd.concat([df_first, df_second], ignore_index=True)
    df_result.to_csv(output_path, index=False)
    print(f"✅ Escenario CAMBIO: {output_path} ({len(df_result)} filas, cambio en fila {split_idx})")

def generate_noise_scenario(df, output_path, noise_start_pct=0.5, noise_level=0.05):
    """
    Escenario 3: Ruido añadido.
    
    - Primera parte: sin cambios
    - Segunda parte: añadir ruido aleatorio Uniform(±noise_level * media)
    """
    split_idx = int(len(df) * noise_start_pct)
    df_first = df.iloc[:split_idx].copy()
    df_second = df.iloc[split_idx:].copy()
    
    # Añadir ruido a la segunda mitad
    if "count" in df_second.columns:
        mean_val = df_second["count"].mean()
        noise = np.random.uniform(-noise_level * mean_val, noise_level * mean_val, len(df_second))
        df_second["count"] = df_second["count"] + noise
        df_second["count"] = df_second["count"].clip(lower=0)
    
    df_result = pd.concat([df_first, df_second], ignore_index=True)
    df_result.to_csv(output_path, index=False)
    print(f"✅ Escenario RUIDO: {output_path} ({len(df_result)} filas, ruido desde fila {split_idx})")

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    source_csv = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(source_csv):
        print(f"❌ Archivo no encontrado: {source_csv}")
        sys.exit(1)
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📖 Leyendo {source_csv}...")
    df = pd.read_csv(source_csv)
    print(f"   {len(df)} filas, {len(df.columns)} columnas")
    
    # Generar 3 escenarios
    base_path = os.path.join(output_dir, "escenario_base.csv")
    change_path = os.path.join(output_dir, "escenario_cambio.csv")
    noise_path = os.path.join(output_dir, "escenario_ruido.csv")
    
    generate_base_scenario(df, base_path)
    generate_change_scenario(df, change_path, change_point_pct=0.6)
    generate_noise_scenario(df, noise_path, noise_start_pct=0.6, noise_level=0.08)
    
    print("\n✨ Generación completada. Archivos listos para ejecutar pipeline.")
    print(f"   1. Sube {base_path}")
    print(f"   2. Sube {change_path}")
    print(f"   3. Sube {noise_path}")

if __name__ == "__main__":
    main()
