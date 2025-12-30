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
    def __init__(self, name: str = "naive", **kwargs):
        super().__init__(name, **kwargs)
    
    def predict(self, series: Sequence[float], horizon: int = 1) -> float:
        """
        Naive prediction (repeat last value)
        
        Args:
            series: Historical values
            horizon: Steps ahead (ignored for naive - always returns last value)
            
        Returns:
            Last observed value (persistence model)
        """
        if not series:
            return 0.0
        return float(series[-1])
    
    def reset(self):
        """No tiene estado interno, no hace nada"""
        pass
