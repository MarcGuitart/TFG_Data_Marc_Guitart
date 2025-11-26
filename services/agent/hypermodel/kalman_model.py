import numpy as np
from .base import BaseModel

class KalmanModel(BaseModel):
    """
    Kalman 1D (posición-velocidad) con dt fijo.
    Estado: [x, v]^T
    Medición: z = x + ruido
    Params esperados:
      dt: paso temporal
      q_pos, q_vel: varianzas proceso (Q)
      r: varianza de medición (R)
      x0, v0 (opcionales): init del estado
      p0: varianza inicial (diagonal)
    """
    def __init__(self, name: str, **kwargs):
        super().__init__(name, **kwargs)
        dt = float(self.cfg.get("dt", 1.0))
        self.F = np.array([[1, dt],
                           [0,  1 ]], dtype=float)         
        self.H = np.array([[1, 0]], dtype=float)           
        q_pos = float(self.cfg.get("q_pos", 1e-3))
        q_vel = float(self.cfg.get("q_vel", 1e-3))
        self.Q = np.array([[q_pos, 0],
                           [0,    q_vel]], dtype=float)    
        r = float(self.cfg.get("r", 1e-2))
        self.R = np.array([[r]], dtype=float)              

        x0 = float(self.cfg.get("x0", 0.0))
        v0 = float(self.cfg.get("v0", 0.0))
        p0 = float(self.cfg.get("p0", 1.0))
        self.x = np.array([[x0],[v0]], dtype=float)        
        self.P = np.eye(2) * p0                           

        self.dt = dt

    def _step(self, z: float):
        # Predict
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q

        # Update
        z = np.array([[float(z)]], dtype=float)
        y = z - (self.H @ x_pred)                           # innovación
        S = self.H @ P_pred @ self.H.T + self.R
        K = P_pred @ self.H.T @ np.linalg.inv(S)            # ganancia Kalman

        self.x = x_pred + K @ y
        I = np.eye(self.P.shape[0])
        self.P = (I - K @ self.H) @ P_pred

    def predict(self, series):
        if not series:
            return 0.0
        # Re-filtra toda la ventana (simple y robusto para demo)
        x0 = float(self.cfg.get("x0", series[0]))
        self.x = np.array([[x0],[0.0]], dtype=float)
        self.P = np.eye(2) * float(self.cfg.get("p0", 1.0))

        for z in series:
            self._step(z)

        # Predicción a un paso vista: x_next = x + v*dt
        x, v = float(self.x[0,0]), float(self.x[1,0])
        return x + v * self.dt
