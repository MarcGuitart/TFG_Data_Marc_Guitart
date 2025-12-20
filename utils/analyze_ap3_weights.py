#!/usr/bin/env python3
"""
AP3: Analizador del sistema de pesos con memoria.

Compara:
- Selector simple (mejor modelo por error en t)
- Selector con pesos (mejor modelo por acumulación de peso)

Genera estadísticas y gráficas para la memoria del TFG.

Uso:
    python utils/analyze_ap3_weights.py <csv_history_file> [output_dir]

Ejemplo:
    python utils/analyze_ap3_weights.py data/weights_history_unit1.csv data/
"""

import sys
import os
import csv
import json
from collections import defaultdict

def analyze_weights(csv_path):
    """
    Analiza el historial de pesos y genera estadísticas.
    
    Returns:
        {
            "total_steps": int,
            "model_stats": { model: {...} },
            "differences": int,  # veces que difieren simple vs weighted
            "timeline": [...]    # datos para graficar
        }
    """
    model_stats = defaultdict(lambda: {
        "times_chosen_simple": 0,
        "times_chosen_weighted": 0,
        "total_weight_gained": 0.0,
        "times_rank_1": 0,
        "avg_error": 0.0,
        "error_count": 0,
    })
    
    differences = 0
    total_steps = 0
    timeline = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total_steps += 1
                
                chosen_simple = row.get('chosen_by_error', '')
                chosen_weighted = row.get('chosen_by_weight', '')
                
                # Contar elecciones
                if chosen_simple:
                    model_stats[chosen_simple]["times_chosen_simple"] += 1
                
                if chosen_weighted:
                    model_stats[chosen_weighted]["times_chosen_weighted"] += 1
                
                # Detectar diferencias
                if chosen_simple and chosen_weighted and chosen_simple != chosen_weighted:
                    differences += 1
                
                # Acumular pesos y errores
                for col_name, col_val in row.items():
                    # Buscar w_<model>
                    if col_name.startswith('w_') and col_name not in ('w_pre_', 'w_'):
                        model_name = col_name[2:]
                        try:
                            weight = float(col_val)
                            model_stats[model_name]["total_weight_gained"] += weight
                        except (ValueError, TypeError):
                            pass
                    
                    # Buscar rank_<model>
                    if col_name.startswith('rank_'):
                        model_name = col_name[5:]
                        try:
                            rank = int(col_val)
                            if rank == 1:
                                model_stats[model_name]["times_rank_1"] += 1
                        except (ValueError, TypeError):
                            pass
                    
                    # Buscar err_<model>
                    if col_name.startswith('err_') and not col_name.startswith('err_rel_'):
                        model_name = col_name[4:]
                        try:
                            err = float(col_val)
                            model_stats[model_name]["avg_error"] += err
                            model_stats[model_name]["error_count"] += 1
                        except (ValueError, TypeError):
                            pass
                
                # Datos para timeline (cada 10 steps para no cargar mucho)
                if total_steps % 10 == 0:
                    entry = {
                        "step": total_steps,
                        "chosen_simple": chosen_simple,
                        "chosen_weighted": chosen_weighted,
                        "differ": chosen_simple != chosen_weighted,
                    }
                    timeline.append(entry)
    
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        sys.exit(1)
    
    # Calcular promedios
    for model_name in model_stats:
        stats = model_stats[model_name]
        if stats["error_count"] > 0:
            stats["avg_error"] /= stats["error_count"]
    
    return {
        "total_steps": total_steps,
        "model_stats": dict(model_stats),
        "differences": differences,
        "difference_pct": (differences / total_steps * 100) if total_steps > 0 else 0,
        "timeline": timeline,
    }

def print_report(data):
    """Imprime un reporte formateado."""
    print(f"\n{'='*80}")
    print(f"AP3: ANÁLISIS DEL SISTEMA DE PESOS CON MEMORIA")
    print(f"{'='*80}\n")
    
    print(f"Total pasos: {data['total_steps']}")
    print(f"Selector simple vs weighted divergen: {data['differences']} veces ({data['difference_pct']:.1f}%)")
    
    print(f"\n{'Modelo':<15} {'Simple':<10} {'Weighted':<10} {'Weight':<12} {'Rank#1':<8} {'Err Avg':<10}")
    print(f"{'-'*80}")
    
    for model_name, stats in sorted(data['model_stats'].items()):
        simple_cnt = stats['times_chosen_simple']
        weighted_cnt = stats['times_chosen_weighted']
        total_weight = stats['total_weight_gained']
        rank1_cnt = stats['times_rank_1']
        avg_err = stats['avg_error']
        
        print(f"{model_name:<15} {simple_cnt:<10} {weighted_cnt:<10} {total_weight:>12.2f} {rank1_cnt:<8} {avg_err:>10.6f}")
    
    print(f"\n{'='*80}")
    print("INTERPRETACIÓN:")
    print(f"  - Si Weighted > Simple: El sistema de pesos adapta mejor que simple ranking")
    print(f"  - Weight: Acumulación total de puntos en el sistema de ranking")
    print(f"  - Rank#1: Cuántas veces fue el modelo mejor en ese step")
    print(f"\nPara visualizar en Excel: Exporta esta tabla y grafica Weighted vs Simple")

def save_json_report(data, output_path):
    """Guarda reporte en JSON para procesamiento posterior."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"✅ Reporte JSON guardado en {output_path}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    csv_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data"
    
    print(f"📊 Analizando {csv_path}...")
    data = analyze_weights(csv_path)
    
    # Imprimir reporte en consola
    print_report(data)
    
    # Guardar JSON para análisis posterior
    os.makedirs(output_dir, exist_ok=True)
    json_out = os.path.join(output_dir, "ap3_analysis.json")
    save_json_report(data, json_out)
    
    print(f"\n💡 Siguiente paso:")
    print(f"   1. Visualiza los datos en Excel o Python/Matplotlib")
    print(f"   2. Compara el rendimiento del selector simple vs weighted")
    print(f"   3. Analiza cuándo divergen las decisiones")

if __name__ == "__main__":
    main()
