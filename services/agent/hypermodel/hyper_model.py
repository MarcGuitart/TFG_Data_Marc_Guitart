import json, math, csv, os
from typing import Sequence, Dict, Any, Tuple, List
from datetime import datetime

from .linear_model import LinearModel
from .poly_model import PolyModel
from .alphabeta import AlphaBetaModel
from .kalman_model import KalmanModel


MODEL_REGISTRY = {
    "linear": LinearModel,
    "poly": PolyModel,
    "alphabeta": AlphaBetaModel,
    "kalman": KalmanModel,
}

class HyperModel:
    """
    HyperModel con sistema de pesos AP3.
    
    El sistema de pesos funciona así:
    1. Decadencia: Se resta total_reward/N a cada modelo (bolsa distribuida equitativamente)
    2. Ranking: Se ordenan modelos por error (menor a mayor)
    3. Recompensa: Se asignan puntos según ranking (N al mejor, N-1 al segundo, ..., 1 al peor)
    4. Selección: El modelo con mayor peso acumulado predice el siguiente punto
    
    Esto crea "memoria" - un modelo no pierde todo su peso por un mal resultado puntual.
    """
    
    def __init__(self, cfg_path: str, decay: float = 0.9, eps: float = 1e-6, 
                 w_cap: float = 10.0, mode: str = "weighted", allow_negative: bool = True):
        """
        Args:
            cfg_path: Path to model_config.json
            decay: (legacy, no se usa en AP3)
            eps: Small epsilon for numerical stability
            w_cap: (legacy, no se usa en AP3)
            mode: "weighted" (average) or "adaptive" (best model selection)
            allow_negative: Si True, permite pesos negativos. Si False, trunca a 0.
        """
        self.decay = decay
        self.eps = eps
        self.w_cap = w_cap
        self.mode = mode
        self.allow_negative = allow_negative
        
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        
        self.models: List = []
        self.model_names: List[str] = []
        self.w: Dict[str, float] = {}
        
        for m in cfg.get("models", []):
            mtype = m["type"]
            name  = m["name"]
            cls = MODEL_REGISTRY[mtype]
            inst = cls(name=name, **(m.get("params", {})))
            self.models.append(inst)
            self.model_names.append(name)
            self.w[name] = float(m.get("init_weight", 0.0))  # AP3: iniciar a 0
        
        # Estado interno
        self._last_preds: Dict[str, float] = {}
        self._last_chosen: str = ""
        self._last_errors: Dict[str, float] = {}
        self._last_errors_rel: Dict[str, float] = {}
        self._last_y_true: float = 0.0
        
        # AP3: Historial para análisis offline
        self._history: List[Dict[str, Any]] = []
        self._step_count: int = 0

    def predict(self, series: Sequence[float]) -> Tuple[float, Dict[str, float]]:
        """
        Genera predicciones de todos los modelos y devuelve la combinada.
        
        En modo "weighted": promedio ponderado por pesos adaptativos
        En modo "adaptive": usa solo el modelo con mayor peso actual (AP3)
        
        Returns:
            (y_hat_combined, {model_name: y_hat, ...})
        """
        preds = {m.name: float(m.predict(series)) for m in self.models}
        self._last_preds = preds
        
        if self.mode == "adaptive":
            # AP3: Selector adaptativo - usa el modelo con MAYOR peso acumulado
            if self.w:
                best_model = max(self.w.keys(), key=lambda n: self.w[n])
                self._last_chosen = best_model
                y_hat = preds[best_model]
            else:
                best_model = next(iter(preds))
                self._last_chosen = best_model
                y_hat = preds[best_model]
        else:
            # Modo weighted: promedio ponderado
            total_w = sum(max(self.w[n], 0.0) for n in preds)
            if total_w <= self.eps:
                y_hat = sum(preds.values()) / max(len(preds), 1)
            else:
                y_hat = sum(preds[n] * max(self.w[n], 0.0) for n in preds) / total_w
        
        return float(y_hat), preds

    def update_weights(self, y_true: float, ts: str = None) -> str:
        """
        AP3: Actualiza pesos con sistema de ranking y memoria.
        
        Algoritmo:
        1. Calcular errores de cada modelo
        2. DECADENCIA: restar (total_reward / N) a todos los modelos
        3. Ordenar por error (mejor a peor)
        4. RECOMPENSA: asignar N al mejor, N-1 al segundo, ..., 1 al peor
        5. Guardar historial para análisis
        6. Seleccionar modelo con mayor peso para siguiente predicción
        
        Args:
            y_true: Valor real observado
            ts: Timestamp opcional para el historial
            
        Returns:
            chosen_by_weight: nombre del modelo elegido por peso para la próxima predicción
        """
        if not self._last_preds:
            return None
        
        self._step_count += 1
        N = len(self.model_names)
        
        # --- 1) Calcular errores de predicción ---
        errors_abs = {}
        errors_rel = {}
        for name, y_pred in self._last_preds.items():
            e_abs = abs(y_true - y_pred)
            errors_abs[name] = e_abs
            if abs(y_true) > 1e-9:
                e_rel = ((y_pred - y_true) / y_true) * 100.0
            else:
                e_rel = 0.0 if abs(y_pred) < 1e-9 else float('inf')
            errors_rel[name] = e_rel
        
        self._last_errors = errors_abs
        self._last_errors_rel = errors_rel
        self._last_y_true = y_true
        
        # --- 2) DECADENCIA: Restar bolsa total repartida equitativamente ---
        # Bolsa = N + (N-1) + ... + 1 = N*(N+1)/2
        total_reward = sum(range(1, N + 1))
        decay_share = total_reward / N
        
        weights_before = dict(self.w)  # Guardar para historial
        
        for name in self.model_names:
            self.w[name] -= decay_share
            # Opcional: truncar a 0 si no permitimos negativos
            if not self.allow_negative and self.w[name] < 0:
                self.w[name] = 0.0
        
        # --- 3) Ordenar por error ascendente (mejor primero) ---
        ranked = sorted(errors_abs.items(), key=lambda kv: kv[1])
        
        # --- 4) RECOMPENSA: N al mejor, N-1 al segundo, ..., 1 al peor ---
        rewards = {}
        for rank, (name, _) in enumerate(ranked):
            reward = N - rank  # mejor → N puntos, peor → 1 punto
            self.w[name] += reward
            rewards[name] = reward
        
        # --- 5) Modelo elegido por error simple (para comparar) ---
        chosen_by_error_simple = ranked[0][0]
        
        # --- 6) Modelo elegido por peso acumulado (AP3) ---
        chosen_by_weight = max(self.model_names, key=lambda n: self.w[n])
        
        # --- 7) Guardar historial para análisis offline ---
        history_entry = {
            "step": self._step_count,
            "ts": ts or datetime.utcnow().isoformat(),
            "y_real": y_true,
            # Predicciones por modelo
            **{f"y_{name}": self._last_preds.get(name, 0.0) for name in self.model_names},
            # Errores absolutos por modelo
            **{f"err_{name}": errors_abs.get(name, 0.0) for name in self.model_names},
            # Errores relativos por modelo (%)
            **{f"err_rel_{name}": errors_rel.get(name, 0.0) for name in self.model_names},
            # Pesos ANTES del update
            **{f"w_pre_{name}": weights_before.get(name, 0.0) for name in self.model_names},
            # Pesos DESPUÉS del update
            **{f"w_{name}": self.w.get(name, 0.0) for name in self.model_names},
            # Rewards asignados
            **{f"reward_{name}": rewards.get(name, 0) for name in self.model_names},
            # Ranking (1 = mejor)
            **{f"rank_{name}": rank + 1 for rank, (name, _) in enumerate(ranked)},
            # Decisiones
            "chosen_by_error": chosen_by_error_simple,
            "chosen_by_weight": chosen_by_weight,
            "choices_differ": chosen_by_error_simple != chosen_by_weight,
            "decay_share": decay_share,
            "total_reward": total_reward,
        }
        self._history.append(history_entry)
        
        # Marcar modelo elegido para predict()
        if self.mode == "adaptive":
            self._last_chosen = chosen_by_weight
        
        return chosen_by_weight

    def export_state(self) -> Dict[str, float]:
        """Devuelve los pesos actuales"""
        return dict(self.w)
    
    def get_chosen_model(self) -> str:
        """Devuelve el nombre del modelo elegido en el último step (modo adaptive)"""
        return self._last_chosen
    
    def get_last_errors(self) -> Dict[str, float]:
        """Devuelve los errores absolutos del último step por modelo"""
        return dict(self._last_errors)
    
    def get_last_errors_rel(self) -> Dict[str, float]:
        """AP2: Devuelve los errores relativos (%) del último step por modelo"""
        return dict(getattr(self, '_last_errors_rel', {}))
    
    def get_chosen_error(self) -> Dict[str, float]:
        """
        AP2: Devuelve el error del modelo elegido.
        Returns: {"abs": float, "rel": float} o vacío si no hay datos
        """
        chosen = self._last_chosen
        if not chosen:
            return {}
        e_abs = self._last_errors.get(chosen, 0.0)
        e_rel = getattr(self, '_last_errors_rel', {}).get(chosen, 0.0)
        return {"abs": e_abs, "rel": e_rel}
    
    # =====================================================================
    # AP3: Métodos para análisis offline
    # =====================================================================
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        AP3: Devuelve el historial completo para análisis.
        Cada entrada contiene: step, ts, y_real, predicciones, errores, pesos, 
        rewards, rankings, decisiones, etc.
        """
        return list(self._history)
    
    def get_last_history_entry(self) -> Dict[str, Any]:
        """AP3: Devuelve la última entrada del historial"""
        return self._history[-1] if self._history else {}
    
    def get_choices_diff_count(self) -> Dict[str, int]:
        """
        AP3: Cuántas veces difieren chosen_by_error vs chosen_by_weight.
        Útil para analizar si el sistema de memoria aporta algo.
        """
        total = len(self._history)
        differ = sum(1 for h in self._history if h.get("choices_differ", False))
        return {
            "total_steps": total,
            "choices_differ": differ,
            "choices_same": total - differ,
            "differ_pct": (differ / total * 100) if total > 0 else 0.0
        }
    
    def export_history_csv(self, filepath: str) -> str:
        """
        AP3: Exporta el historial completo a CSV para análisis en Excel.
        
        Args:
            filepath: Ruta del archivo CSV a crear
            
        Returns:
            filepath si éxito, o mensaje de error
        """
        if not self._history:
            return "No hay historial para exportar"
        
        try:
            # Asegurar directorio existe
            os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
            
            # Obtener todas las columnas de la primera entrada
            fieldnames = list(self._history[0].keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for entry in self._history:
                    # Redondear floats para legibilidad
                    row = {}
                    for k, v in entry.items():
                        if isinstance(v, float):
                            row[k] = round(v, 6)
                        else:
                            row[k] = v
                    writer.writerow(row)
            
            return filepath
        except Exception as e:
            return f"Error exportando CSV: {e}"
    
    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        AP3: Estadísticas por modelo para la memoria del TFG.
        """
        if not self._history:
            return {}
        
        stats = {name: {
            "times_chosen_by_error": 0,
            "times_chosen_by_weight": 0,
            "times_rank_1": 0,
            "total_reward": 0,
            "avg_error": 0.0,
            "final_weight": self.w.get(name, 0.0),
        } for name in self.model_names}
        
        for h in self._history:
            for name in self.model_names:
                if h.get("chosen_by_error") == name:
                    stats[name]["times_chosen_by_error"] += 1
                if h.get("chosen_by_weight") == name:
                    stats[name]["times_chosen_by_weight"] += 1
                if h.get(f"rank_{name}") == 1:
                    stats[name]["times_rank_1"] += 1
                stats[name]["total_reward"] += h.get(f"reward_{name}", 0)
                stats[name]["avg_error"] += h.get(f"err_{name}", 0.0)
        
        n = len(self._history)
        for name in self.model_names:
            stats[name]["avg_error"] = stats[name]["avg_error"] / n if n > 0 else 0.0
        
        return stats
    
    def reset_history(self):
        """AP3: Resetea el historial (para nuevas ejecuciones)"""
        self._history = []
        self._step_count = 0