import os
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CSV_PATH = Path(__file__).resolve().parents[1] / 'data' / 'dades_traffic_escenari1.csv'
OUT_DIR = Path(__file__).resolve().parents[1] / 'results'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / 'dades_traffic_escenari1_plot.png'

def main():
    df = pd.read_csv(CSV_PATH, parse_dates=['timestamp'])
    df = df.sort_values('timestamp')

    plt.figure(figsize=(10,4))
    plt.plot(df['timestamp'], df['value'], linestyle='-')
    plt.xlabel('timestamp')
    plt.ylabel('value')
    plt.title('Scenario Abrupt Shift')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(OUT_PATH)
    print(f'Wrote: {OUT_PATH}')

if __name__ == '__main__':
    main()
