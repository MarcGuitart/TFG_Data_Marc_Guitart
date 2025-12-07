import React, { useMemo } from "react";

/**
 * AP2SelectorTable: Displays the selector table showing which model was chosen at each step
 * Shows: step, time, actual value, chosen model, all model predictions, and error metrics
 */
export default function AP2SelectorTable({ data = [], maxRows = 100 }) {
  const displayData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data.slice(0, maxRows);
  }, [data, maxRows]);

  if (displayData.length === 0) {
    return (
      <div style={{ padding: "16px", color: "#888", fontSize: 12 }}>
        No data available
      </div>
    );
  }

  // Detectar modelos disponibles
  const models = useMemo(() => {
    const modelSet = new Set();
    for (const row of displayData) {
      Object.keys(row).forEach(k => {
        if (!["t", "var", "prediction", "chosen_model", "error", "error_abs", "error_rel"].includes(k) && typeof row[k] === "number") {
          modelSet.add(k);
        }
      });
    }
    return Array.from(modelSet).sort();
  }, [displayData]);

  const modelColors = {
    "kalman": "#10B981",
    "linear": "#3B82F6",
    "poly": "#EC4899",
    "alphabeta": "#F59E0B",
    "ab_fast": "#10B981",
    "linear_8": "#6366F1",
    "poly2_12": "#EC4899",
  };

  const getModelColor = (modelName) => {
    // Match by exact name or partial match
    for (const [key, color] of Object.entries(modelColors)) {
      if (modelName.includes(key) || key.includes(modelName)) {
        return color;
      }
    }
    return "#888";
  };

  return (
    <div style={{ overflowX: "auto", marginTop: 12 }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 11,
          backgroundColor: "#0a0a0a",
          border: "1px solid #333",
        }}
      >
        <thead>
          <tr style={{ background: "#1a1a1a", borderBottom: "2px solid #444" }}>
            <th style={{ padding: "8px", textAlign: "left", color: "#00A3FF", fontWeight: 600, minWidth: 40 }}>
              Step
            </th>
            <th style={{ padding: "8px", textAlign: "left", color: "#00A3FF", fontWeight: 600, minWidth: 100 }}>
              Time
            </th>
            <th style={{ padding: "8px", textAlign: "right", color: "#00A3FF", fontWeight: 600, minWidth: 70 }}>
              Actual
            </th>
            <th style={{ padding: "8px", textAlign: "center", color: "#FF7A00", fontWeight: 600, minWidth: 80 }}>
              Chosen Model
            </th>
            {models.map(model => (
              <th
                key={model}
                style={{
                  padding: "8px",
                  textAlign: "right",
                  color: getModelColor(model),
                  fontWeight: 600,
                  minWidth: 80,
                  background: "rgba(0,163,255,0.05)",
                }}
              >
                {model.length > 12 ? model.substring(0, 12) + "…" : model}
              </th>
            ))}
            <th style={{ padding: "8px", textAlign: "right", color: "#00A3FF", fontWeight: 600, minWidth: 60 }}>
              Error Abs
            </th>
            <th style={{ padding: "8px", textAlign: "right", color: "#00A3FF", fontWeight: 600, minWidth: 60 }}>
              Error %
            </th>
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, idx) => {
            const chosenModel = row.chosen_model || "—";
            const errorAbs = typeof row.error_abs === "number" ? row.error_abs : (typeof row.error === "number" ? row.error : null);
            const errorRel = typeof row.error_rel === "number" ? row.error_rel : null;
            const actual = typeof row.var === "number" ? row.var : null;

            return (
              <tr
                key={idx}
                style={{
                  borderBottom: "1px solid #222",
                  background: idx % 2 === 0 ? "#0a0a0a" : "#121212",
                  transition: "background-color 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#1a2a3a";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = idx % 2 === 0 ? "#0a0a0a" : "#121212";
                }}
              >
                <td style={{ padding: "8px", textAlign: "left", color: "#888" }}>
                  {idx + 1}
                </td>
                <td style={{ padding: "8px", textAlign: "left", color: "#888", fontSize: 10 }}>
                  {row.t ? new Date(row.t * 1000 || row.t).toLocaleString() : "—"}
                </td>
                <td style={{ padding: "8px", textAlign: "right", color: "#fff", fontWeight: 500 }}>
                  {actual !== null ? actual.toFixed(3) : "—"}
                </td>
                <td style={{ padding: "8px", textAlign: "center", color: "#FF7A00", fontWeight: 600 }}>
                  {chosenModel}
                </td>
                {models.map(model => {
                  const value = typeof row[model] === "number" ? row[model] : null;
                  return (
                    <td
                      key={model}
                      style={{
                        padding: "8px",
                        textAlign: "right",
                        color: getModelColor(model),
                        fontWeight: row[model] === row.prediction ? 700 : 400,
                        background: row.chosen_model === model ? "rgba(255,122,0,0.1)" : "transparent",
                      }}
                    >
                      {value !== null ? value.toFixed(3) : "—"}
                    </td>
                  );
                })}
                <td style={{ padding: "8px", textAlign: "right", color: errorAbs !== null && errorAbs > 0.5 ? "#f87171" : "#86efac" }}>
                  {errorAbs !== null ? errorAbs.toFixed(3) : "—"}
                </td>
                <td style={{ padding: "8px", textAlign: "right", color: errorRel !== null && errorRel > 10 ? "#f87171" : "#86efac" }}>
                  {errorRel !== null ? errorRel.toFixed(1) : "—"}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {displayData.length > 0 && (
        <div style={{ marginTop: 12, fontSize: 11, color: "#666" }}>
          Showing <strong>{displayData.length}</strong> of <strong>{data.length}</strong> rows
          {data.length > maxRows && ` (max ${maxRows} rows)`}
        </div>
      )}

      <div style={{ marginTop: 16, padding: "12px", background: "#1a1a1a", borderRadius: "6px", fontSize: 11, color: "#888" }}>
        <div style={{ marginBottom: 8 }}>
          <strong style={{ color: "#00A3FF" }}>📋 AP2 Selector Adaptativo:</strong>
        </div>
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          <li>Shows the model selected at each step (AP2 Adaptive Selector)</li>
          <li>Color-coded columns for each model prediction</li>
          <li>Highlighted row shows which model was chosen (orange background)</li>
          <li>Error columns (absolute and relative %) show prediction accuracy</li>
          <li>Models with best predictions typically chosen have lower error values</li>
        </ul>
      </div>
    </div>
  );
}
