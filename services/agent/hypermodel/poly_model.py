import numpy as np
from .base import BaseModel

class PolyModel(BaseModel):
    def predict(self, series):
        deg = int(self.cfg.get("degree", 2))
        n = int(self.cfg.get("window", 12))
        y = np.array(series[-n:], dtype=float)
        x = np.arange(len(y), dtype=float)
        if len(y) <= deg:
            return float(y[-1]) if len(y) else 0.0
        coeffs = np.polyfit(x, y, deg)
        y_next = np.polyval(coeffs, len(y))
        return float(y_next)
