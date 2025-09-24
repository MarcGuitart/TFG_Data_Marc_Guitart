import sys, pandas as pd
from pathlib import Path

# Uso: python3 utils/convert_simple_to_id_ts_var.py data/simple_window.csv data/simple_window_id_ts_var.csv
src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/simple_window.csv")
dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/simple_window_id_ts_var.csv")

df = pd.read_csv(src)

# Normaliza nombres (por si vienen con mayúsculas)
df.columns = [c.strip().lower() for c in df.columns]

# Columnas típicas del proyecto
ts_col = next((c for c in df.columns if c in ("ts","timestamp","time")), None)
id_col = next((c for c in df.columns if c in ("unit_id","id")), None)

# Elige la primera variable: v1, value, var, o el primer numérico distinto de ts/id
var_col = None
for cand in ("v1","value","var"):
    if cand in df.columns:
        var_col = cand
        break
if var_col is None:
    num_cols = [c for c in df.columns if c not in (ts_col, id_col)]
    # intenta coger la primera columna numérica
    for c in num_cols:
        if pd.api.types.is_numeric_dtype(df[c]):
            var_col = c
            break

if not ts_col or not id_col or not var_col:
    raise SystemExit(f"Faltan columnas. Encontradas: {list(df.columns)} "
                     f"(necesitamos ts/timestamp, unit_id/id y alguna variable numérica)")

out = df[[id_col, ts_col, var_col]].rename(columns={
    id_col: "id",
    ts_col: "timestamp",
    var_col: "var",
})

# Asegura tipos
out["id"] = out["id"].astype(str)
out["timestamp"] = out["timestamp"].astype(str)
out["var"] = pd.to_numeric(out["var"], errors="coerce")
out = out.dropna(subset=["var"])

dst.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(dst, index=False)
print(f"OK -> {dst} ({out.shape[0]} filas, cols={list(out.columns)})")
