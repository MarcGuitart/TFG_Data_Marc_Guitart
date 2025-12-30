import numpy as np
from .base import BaseModel

class PolyModel(BaseModel):
    def predict(self, series, horizon=1):
        """
        Polynomial regression extrapolation
        
        Args:
            series: Historical values
            horizon: Steps ahead (1=T+1, 2=T+2, etc.)
        """
        deg = int(self.cfg.get("degree", 2))
        n = int(self.cfg.get("window", 12))
        y = np.array(series[-n:], dtype=float)
        x = np.arange(len(y), dtype=float)
        if len(y) <= deg:
            return float(y[-1]) if len(y) else 0.0
        coeffs = np.polyfit(x, y, deg)
        # Extrapolate to T+horizon
        y_next = np.polyval(coeffs, len(y) + horizon - 1)
        return float(y_next)
