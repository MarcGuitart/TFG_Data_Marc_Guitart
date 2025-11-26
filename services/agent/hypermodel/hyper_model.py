import json, math
from typing import Sequence, Dict, Any, Tuple

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
    def __init__(self, cfg_path: str, decay: float = 0.9, eps: float = 1e-6, w_cap: float = 10.0, mode: str = "weighted"):
        """
        Args:
            cfg_path: Path to model_config.json
            decay: Weight decay factor
            eps: Small epsilon for numerical stability
            w_cap: Maximum weight cap
            mode: "weighted" (average) or "adaptive" (best model selection)
        """
        self.decay = decay
        self.eps = eps
        self.w_cap = w_cap
        self.mode = mode  # "weighted" or "adaptive"
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        self.models = []
        self.w: Dict[str, float] = {}
        for m in cfg.get("models", []):
            mtype = m["type"]
            name  = m["name"]
            cls = MODEL_REGISTRY[mtype]  # lanzará KeyError si hay un type no soportado
            inst = cls(name=name, **(m.get("params", {})))
            self.models.append(inst)
            self.w[name] = float(m.get("init_weight", 1.0))
        self._last_preds: Dict[str, float] = {}
        self._last_chosen: str = ""  # Para modo adaptativo
        self._last_errors: Dict[str, float] = {}  # Errores del último step

    def predict(self, series: Sequence[float]) -> Tuple[float, Dict[str, float]]:
        """
        Genera predicciones de todos los modelos y devuelve la combinada.
        
        En modo "weighted": promedio ponderado por pesos adaptativos
        En modo "adaptive": usa solo el modelo ganador del último step
        
        Returns:
            (y_hat_combined, {model_name: y_hat, ...})
        """
        preds = {m.name: float(m.predict(series)) for m in self.models}
        self._last_preds = preds
        
        if self.mode == "adaptive":
            # Selector adaptativo: usa solo el modelo que ganó en el último step
            if self._last_chosen and self._last_chosen in preds:
                y_hat = preds[self._last_chosen]
            else:
                # Primer step o modelo no encontrado: usa el primero
                y_hat = preds[next(iter(preds))]
        else:
            # Modo weighted (original): promedio ponderado
            total_w = sum(max(self.w[n], 0.0) for n in preds)
            if total_w <= self.eps:
                y_hat = sum(preds.values()) / max(len(preds), 1)
            else:
                y_hat = sum(preds[n] * max(self.w[n], 0.0) for n in preds) / total_w
        
        return float(y_hat), preds

    def update_weights(self, y_true: float):
        """
        Actualiza pesos basándose en el error de predicción.
        
        AP3: Sistema de ranking con puntos:
        - Ordena modelos por error (mejor a peor)
        - Asigna puntos según ranking: M puntos al mejor, M-1 al segundo, ..., 1 al peor
        - Resta 1 punto a todos para evitar crecimiento infinito
        - Permite pesos negativos para contraste real
        
        En modo "adaptive": además selecciona el modelo ganador
        
        Returns:
            best_model (str): nombre del modelo ganador
        """
        if not self._last_preds:
            return None
        
        # Calcular errores
        errors = {}
        for name, y_pred in self._last_preds.items():
            e = abs(y_true - y_pred)
            errors[name] = e
        
        self._last_errors = errors
        
        # AP3: Sistema de ranking con puntos
        # 1) Restar 1 a todos los pesos
        for name in self.w:
            self.w[name] -= 1.0
        
        # 2) Ordenar modelos por error ascendente (mejor primero)
        ranked = sorted(errors.items(), key=lambda kv: kv[1])  # (name, error)
        M = len(ranked)
        
        # 3) Asignar puntos según ranking: M al mejor, M-1 al segundo, ..., 1 al peor
        for rank, (name, _) in enumerate(ranked):
            reward = M - rank  # mejor modelo → M puntos
            self.w[name] += reward
        
        # Encontrar modelo ganador (menor error = primer elemento del ranking)
        best_model = ranked[0][0]
        
        if self.mode == "adaptive":
            # Modo adaptativo: marcar el modelo elegido para usar en predict()
            self._last_chosen = best_model
        
        return best_model

    def export_state(self) -> Dict[str, float]:
        return dict(self.w)
    
    def get_chosen_model(self) -> str:
        """Devuelve el nombre del modelo elegido en el último step (modo adaptive)"""
        return self._last_chosen
    
    def get_last_errors(self) -> Dict[str, float]:
        """Devuelve los errores del último step por modelo"""
        return dict(self._last_errors)