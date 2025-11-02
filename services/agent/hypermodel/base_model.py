from abc import ABC, abstractmethod
from typing import Sequence, Dict, Any

class BaseModel(ABC):
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.cfg = kwargs

    @abstractmethod
    def predict(self, series: Sequence[float]) -> float:
        ...

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"
