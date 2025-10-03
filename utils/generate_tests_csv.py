import numpy as np
import pandas as pd
import os

output_dir = "data/test_csvs"
os.makedirs(output_dir, exist_ok=True)

def generate_csv(name, N=900, freq="s", periods=2, amplitude=1.0):
    t = np.linspace(0, 2 * np.pi * periods, N)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=N, freq=freq),
        "id": [f"unit-{name}"] * N,
        "var": amplitude * np.sin(t)
    })
    df.to_csv(f"{output_dir}/{name}.csv", index=False)

# Variaciones
generate_csv("sine_900", N=900)
generate_csv("sine_300", N=300)
generate_csv("sine_900_a2", N=900, amplitude=2)
generate_csv("sine_900_a5", N=900, amplitude=0.5)
generate_csv("sine_1800_doub", N=1800, periods=4)
