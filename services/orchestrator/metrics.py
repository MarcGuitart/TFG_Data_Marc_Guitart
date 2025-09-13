import time
import threading
from dataclasses import dataclass, field

@dataclass
class Counters:
    messages_in: int = 0
    messages_out: int = 0
    errors: int = 0

@dataclass
class LatencyStats:
    # Guarda últimas N latencias para p50/p95 aproximados
    max_samples: int = 1000
    samples: list = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, dt: float):
        with self.lock:
            self.samples.append(dt)
            if len(self.samples) > self.max_samples:
                self.samples.pop(0)

    def summary(self):
        with self.lock:
            if not self.samples:
                return {"p50": None, "p95": None, "avg": None, "n": 0}
            xs = sorted(self.samples)
            n = len(xs)
            p50 = xs[int(0.50*(n-1))]
            p95 = xs[int(0.95*(n-1))]
            avg = sum(xs)/n
            return {"p50": p50, "p95": p95, "avg": avg, "n": n}

class Metrics:
    def __init__(self):
        self.counters = Counters()
        self.latencies = LatencyStats()
        self.started_at = time.time()

    def now(self):
        return time.monotonic()

    def measure(self, fn, *args, **kwargs):
        t0 = self.now()
        try:
            return fn(*args, **kwargs)
        finally:
            dt = self.now() - t0
            self.latencies.add(dt)

    def as_dict(self):
        uptime = time.time() - self.started_at
        return {
            "uptime_s": uptime,
            "counters": vars(self.counters),
            "latency": self.latencies.summary(),
        }

METRICS = Metrics()
