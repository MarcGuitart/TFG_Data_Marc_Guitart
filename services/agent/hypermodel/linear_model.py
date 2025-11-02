import numpy as np
from .base import BaseModel

class LinearModel(BaseModel):
    # deg=1 con últimas N observaciones
    def predict(self, series):
        n = int(self.cfg.get("window", 8))
        y = np.array(series[-n:], dtype=float)
        x = np.arange(len(y), dtype=float)
        if len(y) < 2:  # fallback
            return float(y[-1]) if len(y) else 0.0
        a, b = np.polyfit(x, y, 1)  # y ~ a*x + b
        y_next = a * len(y) + b
        return float(y_next)
