import numpy as np
import pandas as pd
from pathlib import Path

# Parámetros
N = 900
PERIODOS = 2
ID = "unit_01"  # puedes cambiar o generar varias unidades

t = np.linspace(0, 2*np.pi*PERIODOS, N)
timestamps = pd.date_range("2024-01-01", periods=N, freq="S")

df = pd.DataFrame({
    "id": ID,
    "timestamp": timestamps.astype(str),  
    "var": np.sin(t)
})

out = Path("data/sine_window.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"Escrito: {out} -> {df.shape}")
