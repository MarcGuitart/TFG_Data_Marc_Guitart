from abc import ABC, abstractmethod
from typing import Sequence, Dict, Any

class BaseModel(ABC):
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.cfg = kwargs

    @abstractmethod
    def predict(self, series: Sequence[float], horizon: int = 1) -> float:
        """
        Predict value at T+horizon
        
        Args:
            series: Historical observations
            horizon: Steps ahead to predict (1 = next step, 2 = T+2, etc.)
            
        Returns:
            Predicted value at T+horizon
        """
        ...
    
    def predict_multi_horizon(self, series: Sequence[float], max_horizon: int) -> Dict[int, float]:
        """
        Predict multiple horizons at once
        
        Args:
            series: Historical observations
            max_horizon: Maximum horizon (e.g., 10 for T+1 to T+10)
            
        Returns:
            {1: pred_t1, 2: pred_t2, ..., max_horizon: pred_tM}
        """
        predictions = {}
        for h in range(1, max_horizon + 1):
            predictions[h] = self.predict(series, horizon=h)
        return predictions

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"
