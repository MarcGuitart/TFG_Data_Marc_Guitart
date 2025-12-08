#!/usr/bin/env python3
"""
AP1: Verificador de consistencia de modelo adaptativo.

Comprueba que en cada timestamp, la predicción adaptativa EXACTAMENTE 
coincide con una de las predicciones de los modelos base.

Uso:
    python utils/verify_ap1_consistency.py <csv_history_file> [tolerance]

Ejemplo:
    python utils/verify_ap1_consistency.py data/weights_history_unit1.csv 1e-4
"""

import sys
import csv
import math

def verify_consistency(csv_path, tolerance=1e-4):
    """
    Lee un CSV de historial y verifica AP1 consistency.
    
    Args:
        csv_path: Ruta del CSV con columnas y_{model} y chosen_by_weight
        tolerance: Tolerancia numérica (default 1e-4)
    
    Returns:
        (total_steps, failures, failure_details)
    """
    failures = []
    total_steps = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # start=2 porque row 1 es header
                total_steps += 1
                
                # Obtener predicción adaptativa
                try:
                    y_adaptive = float(row.get('y_pred', row.get('hyper_y_hat', 'nan')))
                except (ValueError, TypeError):
                    failures.append({
                        "row": row_num,
                        "reason": "y_adaptive not found or not numeric"
                    })
                    continue
                
                if math.isnan(y_adaptive):
                    continue
                
                # Obtener modelo elegido
                chosen_model = row.get('chosen_by_weight') or row.get('chosen_model')
                if not chosen_model:
                    failures.append({
                        "row": row_num,
                        "reason": "No chosen model info"
                    })
                    continue
                
                # Buscar predicción del modelo elegido
                key_pattern = f"y_{chosen_model}"
                y_model = None
                
                for col_name, col_val in row.items():
                    if col_name == key_pattern:
                        try:
                            y_model = float(col_val)
                            break
                        except (ValueError, TypeError):
                            pass
                
                if y_model is None:
                    failures.append({
                        "row": row_num,
                        "reason": f"No prediction for model '{chosen_model}'"
                    })
                    continue
                
                # VERIFICACIÓN: ¿Coinciden?
                diff = abs(y_adaptive - y_model)
                if diff > tolerance:
                    failures.append({
                        "row": row_num,
                        "model": chosen_model,
                        "y_adaptive": y_adaptive,
                        "y_model": y_model,
                        "diff": diff,
                        "reason": f"y_adaptive({y_adaptive:.6f}) != y_{chosen_model}({y_model:.6f}), diff={diff:.6e}"
                    })
    
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        sys.exit(1)
    
    return total_steps, failures

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    csv_path = sys.argv[1]
    tolerance = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-4
    
    print(f"🔍 Verificando consistencia AP1 en {csv_path}")
    print(f"   Tolerancia numérica: {tolerance:.2e}\n")
    
    total_steps, failures = verify_consistency(csv_path, tolerance)
    
    print(f"Total steps: {total_steps}")
    print(f"Failures: {len(failures)}")
    
    if failures:
        print("\n❌ PROBLEMAS DETECTADOS:")
        for i, fail in enumerate(failures[:20], 1):  # Mostrar máximo 20
            print(f"\n   [{i}] Row {fail['row']}: {fail['reason']}")
            if 'y_adaptive' in fail:
                print(f"       y_adaptive = {fail['y_adaptive']:.6f}")
                print(f"       y_model = {fail['y_model']:.6f}")
                print(f"       diff = {fail['diff']:.6e}")
        
        if len(failures) > 20:
            print(f"\n   ... y {len(failures) - 20} más")
    else:
        print("\n✅ VERIFICACIÓN OK: Todas las predicciones adaptativas coinciden con sus modelos base.")
    
    # Resumen
    success_pct = ((total_steps - len(failures)) / total_steps * 100) if total_steps > 0 else 0
    print(f"\n📊 Resumen: {success_pct:.1f}% de consistencia ({total_steps - len(failures)}/{total_steps})")

if __name__ == "__main__":
    main()
