import json, math
from typing import Sequence, Dict, Any, Tuple

from pydantic import BaseModel
from .linear import LinearModel
from .poly import PolyModel
from .alphabeta import AlphaBetaModel
from services.agent.hypermodel.kalman_model import KalmanModel

MODEL_REGISTRY = {
    "linear": LinearModel,
    "poly": PolyModel,
    "alphabeta": AlphaBetaModel,
    "kalman": KalmanModel,
    "base": BaseModel,
}

class HyperModel:
    def __init__(self, cfg_path: str, decay: float = 0.9, eps: float = 1e-6, w_cap: float = 10.0):
        """
        decay: factor de olvido exponencial (0<decay<1); cuanto más cercano a 1, más memoria.
        """
        self.decay = decay
        self.eps = eps
        self.w_cap = w_cap
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        self.models = []
        self.w: Dict[str, float] = {}
        for m in cfg.get("models", []):
            mtype = m["type"]
            name  = m["name"]
            cls = MODEL_REGISTRY[mtype]
            inst = cls(name=name, **(m.get("params", {})))
            self.models.append(inst)
            self.w[name] = float(m.get("init_weight", 1.0))
        self._last_preds: Dict[str, float] = {}

    def predict(self, series: Sequence[float]) -> Tuple[float, Dict[str, float]]:
        preds = {m.name: float(m.predict(series)) for m in self.models}
        self._last_preds = preds
        # Media ponderada (normalizar pesos > 0)
        total_w = sum(max(self.w[n], 0.0) for n in preds)
        if total_w <= self.eps:
            # fallback: promedio simple
            y_hat = sum(preds.values()) / max(len(preds), 1)
        else:
            y_hat = sum(preds[n] * max(self.w[n], 0.0) for n in preds) / total_w
        return float(y_hat), preds

    def update_weights(self, y_true: float):
        """ Actualiza pesos en función del error último (inversamente proporcional).
            w_i <- decay*w_i + (1-decay) * score_i,  score_i = 1 / (eps + |e_i|)
            y_true es la observación real que acaba de llegar.
        """
        if not self._last_preds:
            return
        scores = {}
        for name, y_pred in self._last_preds.items():
            e = abs(y_true - y_pred)
            scores[name] = 1.0 / (self.eps + e)

        # Normalizado opcional de scores
        s_sum = sum(scores.values())
        if s_sum > self.eps:
            for k in scores:
                scores[k] /= s_sum

        for name in self.w:
            new_w = self.decay * self.w[name] + (1.0 - self.decay) * scores.get(name, 0.0)
            self.w[name] = min(max(new_w, 0.0), self.w_cap)

    def export_state(self) -> Dict[str, float]:
        return dict(self.w)
