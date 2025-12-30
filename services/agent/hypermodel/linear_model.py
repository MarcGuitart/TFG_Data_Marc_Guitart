import numpy as np
from .base import BaseModel

class LinearModel(BaseModel):
    # deg=1 con últimas N observaciones
    def predict(self, series, horizon=1):
        """
        Linear regression extrapolation
        
        Args:
            series: Historical values
            horizon: Steps ahead (1=T+1, 2=T+2, etc.)
        """
        n = int(self.cfg.get("window", 8))
        y = np.array(series[-n:], dtype=float)
        x = np.arange(len(y), dtype=float)
        if len(y) < 2:  # fallback
            return float(y[-1]) if len(y) else 0.0
        a, b = np.polyfit(x, y, 1)  # y ~ a*x + b
        # Extrapolate to T+horizon
        y_next = a * (len(y) + horizon - 1) + b
        return float(y_next)
