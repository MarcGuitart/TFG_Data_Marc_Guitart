from collections import deque
from datetime import datetime
import json
import math

class ModelBase:
    def load(self, path_or_cfg): ...
    def save(self, path): ...
    def predict(self, xbuf, t_pred: datetime) -> float: ...
    def update(self, rows): ...

class NaiveDailyProfileModel(ModelBase):
    """
    Perfil diario simple (slots de 30') que guarda una media por franja.
    - predict(t_pred): devuelve el valor del perfil para la franja de t_pred.
    - update(rows): recalcula el perfil a partir de filas Influx ({"_time": dt, "var": float}).
    - buffer interno: últimos valores observados (para fallback si el perfil aún está vacío).
    """
    def __init__(self, slot_minutes=30, horizon_slots=1):
        self.slot_minutes = int(slot_minutes)
        self.nslots = 24 * 60 // self.slot_minutes
        self.horizon_slots = int(horizon_slots)
        self.profile = [math.nan] * self.nslots
        self.buffer = deque(maxlen=256)

    def _slot(self, ts: datetime) -> int:
        m = ts.hour * 60 + ts.minute
        return (m // self.slot_minutes) % self.nslots

    def update_buffer(self, x_value: float):
        try:
            self.buffer.append(float(x_value))
        except Exception:
            pass

    def predict(self, xbuf, t_pred: datetime) -> float:
        slot = self._slot(t_pred)
        v = self.profile[slot]
        if math.isnan(v):
            # Fallback: último valor observado si aún no hay perfil
            if self.buffer:
                return float(self.buffer[-1])
            return 0.0
        return float(v)

    def update(self, rows):
        # rows: iterable de {"_time": datetime, "var": float}
        sums = [0.0] * self.nslots
        cnts = [0] * self.nslots
        for r in rows:
            ts = r["_time"]
            v = float(r["var"])
            s = self._slot(ts)
            sums[s] += v
            cnts[s] += 1
        for i in range(self.nslots):
            if cnts[i]:
                self.profile[i] = sums[i] / cnts[i]

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({
                "slot_minutes": self.slot_minutes,
                "horizon_slots": self.horizon_slots,
                "profile": self.profile
            }, f)

    def load(self, path_or_cfg: str):
        with open(path_or_cfg) as f:
            d = json.load(f)
        self.slot_minutes = int(d["slot_minutes"])
        self.horizon_slots = int(d["horizon_slots"])
        self.nslots = 24 * 60 // self.slot_minutes
        self.profile = list(d["profile"])