"""
Sistema de gestión de escenarios para el TFG.

Permite guardar y comparar resultados de diferentes ejecuciones:
- Escenario 0: Tráfico estable (baseline)
- Escenario 1: Cambio brusco (concept drift)
- Escenario 2: Ruido alto
- etc.

Cada escenario guarda:
- Configuración (modo hypermodel, parámetros, CSV usado)
- Métricas agregadas (MAE, RMSE, distribución de modelos)
- Historial de pesos completo
- Timestamp de ejecución
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

SCENARIOS_DIR = Path("/app/data/scenarios")
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)


class ScenarioManager:
    """Gestiona guardado y carga de escenarios experimentales"""
    
    @staticmethod
    def save_scenario(
        scenario_name: str,
        unit_id: str,
        config: Dict[str, Any],
        metrics: Dict[str, Any],
        history: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Guarda un escenario completo.
        
        Args:
            scenario_name: Nombre descriptivo (ej: "escenario_0_baseline")
            unit_id: ID de la serie temporal
            config: Configuración del experimento (modo, decay, etc.)
            metrics: Métricas agregadas (MAE global, distribución, etc.)
            history: Historial completo de pesos paso a paso
            metadata: Info adicional (CSV usado, timestamp, etc.)
            
        Returns:
            filepath: Ruta del archivo JSON guardado
        """
        timestamp = datetime.utcnow().isoformat()
        
        scenario_data = {
            "scenario_name": scenario_name,
            "unit_id": unit_id,
            "timestamp": timestamp,
            "config": config,
            "metrics": metrics,
            "history": history,
            "metadata": metadata or {}
        }
        
        # Sanitizar nombre para filesystem
        safe_name = scenario_name.replace(" ", "_").replace("/", "_")
        filepath = SCENARIOS_DIR / f"{safe_name}_{timestamp.split('T')[0]}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scenario_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    @staticmethod
    def load_scenario(filepath: str) -> Dict[str, Any]:
        """Carga un escenario guardado"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def list_scenarios() -> List[Dict[str, Any]]:
        """Lista todos los escenarios guardados con metadata"""
        scenarios = []
        
        for filepath in SCENARIOS_DIR.glob("*.json"):
            try:
                data = ScenarioManager.load_scenario(filepath)
                scenarios.append({
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "scenario_name": data.get("scenario_name"),
                    "unit_id": data.get("unit_id"),
                    "timestamp": data.get("timestamp"),
                    "config": data.get("config", {}),
                    "metrics_summary": {
                        "mae": data.get("metrics", {}).get("mae_global"),
                        "rmse": data.get("metrics", {}).get("rmse_global"),
                        "models_used": data.get("metrics", {}).get("models_distribution"),
                    }
                })
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        
        # Ordenar por timestamp descendente (más reciente primero)
        scenarios.sort(key=lambda x: x["timestamp"], reverse=True)
        return scenarios
    
    @staticmethod
    def compare_scenarios(scenario_names: List[str]) -> Dict[str, Any]:
        """
        Compara múltiples escenarios lado a lado.
        
        Args:
            scenario_names: Lista de nombres de escenarios a comparar
            
        Returns:
            Tabla comparativa con métricas clave
        """
        comparison = {
            "scenarios": [],
            "summary": {}
        }
        
        for name in scenario_names:
            # Buscar último archivo con ese nombre
            matches = list(SCENARIOS_DIR.glob(f"{name}*.json"))
            if not matches:
                continue
            
            latest = max(matches, key=lambda p: p.stat().st_mtime)
            data = ScenarioManager.load_scenario(latest)
            
            comparison["scenarios"].append({
                "name": name,
                "timestamp": data.get("timestamp"),
                "mode": data.get("config", {}).get("hypermodel_mode"),
                "metrics": data.get("metrics", {}),
                "history_length": len(data.get("history", []))
            })
        
        # Calcular summary (mejor MAE, mejor RMSE, etc.)
        if comparison["scenarios"]:
            comparison["summary"] = {
                "best_mae": min(comparison["scenarios"], key=lambda x: x["metrics"].get("mae_global", float('inf')))["name"],
                "best_rmse": min(comparison["scenarios"], key=lambda x: x["metrics"].get("rmse_global", float('inf')))["name"],
            }
        
        return comparison
    
    @staticmethod
    def delete_scenario(filepath: str) -> bool:
        """Elimina un escenario guardado"""
        try:
            Path(filepath).unlink()
            return True
        except Exception as e:
            print(f"Error deleting {filepath}: {e}")
            return False
