"""
Modelo de media móvil simple: retorna el promedio de los últimos N valores.
Útil como baseline intermedio entre naive y modelos más sofisticados.
"""
from typing import Sequence
from .base_model import BaseModel

class MovingAverageModel(BaseModel):
    """
    Predictor de media móvil: retorna el promedio de los últimos N valores.
    """
    def __init__(self, name: str = "hyper", window: int = 5, **kwargs):
        super().__init__(name, **kwargs)
        self.window = window
    
    def predict(self, series: Sequence[float]) -> float:
        """Retorna la media de los últimos window valores"""
        if not series:
            return 0.0
        
        # Tomar los últimos window valores
        recent = list(series[-self.window:]) if len(series) >= self.window else list(series)
        
        if not recent:
            return 0.0
        
        return float(sum(recent) / len(recent))
    
    def reset(self):
        """No tiene estado interno, no hace nada"""
        pass
