from .base import BaseModel

class AlphaBetaModel(BaseModel):
    """
    Filtro α-β 1D (posición y velocidad), ganancias fijas.
    Params: alpha (0..1), beta (0..1), dt (>0)
    """
    def predict(self, series, horizon=1):
        """
        Alpha-Beta filter prediction with multi-horizon support
        
        Args:
            series: Historical values
            horizon: Steps ahead (1=T+1, 2=T+2, etc.)
        """
        alpha = float(self.cfg.get("alpha", 0.85))
        beta  = float(self.cfg.get("beta", 0.01))
        dt    = float(self.cfg.get("dt", 1.0))
        if not series:
            return 0.0

        x = float(series[0])  # posición
        v = 0.0               # velocidad
        for z in series[1:]:
            # predicción
            x_pred = x + v*dt
            # innovación
            r = float(z) - x_pred
            # actualización
            x = x_pred + alpha * r
            v = v + (beta * r) / dt

        # Multi-step prediction: x(t+h) = x(t) + v*dt*h
        return x + v * dt * horizon
