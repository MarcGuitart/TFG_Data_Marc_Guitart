"""
Modelo naive/base: simplemente retorna el último valor observado (persistencia).
Útil como baseline de comparación.
"""
from typing import Sequence
from .base_model import BaseModel

class NaiveModel(BaseModel):
    """
    Predictor naive (baseline): retorna el último valor observado.
    Asume que el futuro = presente (modelo de persistencia).
    """
    def __init__(self, name: str = "base", **kwargs):
        super().__init__(name, **kwargs)
    
    def predict(self, series: Sequence[float]) -> float:
        """Retorna el último valor de la serie, o 0 si está vacía"""
        if not series:
            return 0.0
        return float(series[-1])
    
    def reset(self):
        """No tiene estado interno, no hace nada"""
        pass
