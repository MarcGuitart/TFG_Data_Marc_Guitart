import React from "react";
import "./MetricsPanel.css";

export default function MetricsPanel({ combined, models, loading, error, selectedId }) {
  if (!selectedId) {
    return (
      <div className="metrics-card">
        <h3 className="metrics-title">Metrics</h3>
        <p className="metrics-text">Select an ID to see metrics.</p>
      </div>
    );
  }

  // AP4: Obtener todos los modelos ordenados por weight descendente
  const getAllModelsSorted = (modelsOverall) => {
    if (!modelsOverall) return [];
    
    return Object.entries(modelsOverall)
      .map(([name, stats]) => ({ name, ...stats }))
      .sort((a, b) => {
        const weightA = a.weight ?? -Infinity;
        const weightB = b.weight ?? -Infinity;
        return weightB - weightA;
      });
  };

  // AP4: Obtener medalla según posición
  const getRankDisplay = (idx) => {
    if (idx === 0) return "🥇";
    if (idx === 1) return "🥈";
    if (idx === 2) return "🥉";
    return idx + 1;
  };

  // AP4: Clase CSS para destacar top-3
  const getRowClass = (idx) => {
    if (idx === 0) return "metrics-row--gold";
    if (idx === 1) return "metrics-row--silver";
    if (idx === 2) return "metrics-row--bronze";
    return "";
  };

  return (
    <div className="metrics-card">
      <h3 className="metrics-title">Metrics for <span className="metrics-id">{selectedId}</span></h3>

      {loading && <p className="metrics-text">Loading metrics…</p>}

      {error && (
        <p className="metrics-error">{error}</p>
      )}

      {/* Métricas combinadas (predicción híbrida) */}
      {!loading && !error && combined && (
        <>
          <h4 className="metrics-subtitle">Overall (hybrid prediction)</h4>
          <table className="metrics-table">
            <thead>
              <tr>
                <th>MAE</th>
                <th>RMSE</th>
                <th>MAPE</th>
                <th>n</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{combined.overall?.mae?.toFixed(6) ?? "-"}</td>
                <td>{combined.overall?.rmse?.toFixed(6) ?? "-"}</td>
                <td>{combined.overall?.mape?.toFixed(6) ?? "-"}</td>
                <td>{combined.overall?.n ?? "-"}</td>
              </tr>
            </tbody>
          </table>

          {combined.daily && combined.daily.length > 0 && (
            <>
              <h4 className="metrics-subtitle">Daily (hybrid prediction)</h4>
              <table className="metrics-table metrics-table--small">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>MAE</th>
                    <th>RMSE</th>
                    <th>MAPE</th>
                  </tr>
                </thead>
                <tbody>
                  {combined.daily.map((d) => (
                    <tr key={d.time}>
                      <td>{d.time}</td>
                      <td>{d.mae?.toFixed(6) ?? "-"}</td>
                      <td>{d.rmse?.toFixed(6) ?? "-"}</td>
                      <td>{d.mape?.toFixed(6) ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}

      {/* AP4: Tabla de métricas por modelo ordenada por weight con Top-3 destacados */}
      {!loading && !error && models && models.overall && (
        <>
          <h4 className="metrics-subtitle">
            🏆 Model Ranking (AP4 - by Weight)
          </h4>
          <p style={{ fontSize: "12px", color: "#888", margin: "0 0 8px 0" }}>
            Modelos ordenados por <strong>weight</strong> descendente. Top-3 destacados con medalla.
          </p>
          <table className="metrics-table metrics-table--ap4">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>Weight</th>
                <th>MAE</th>
                <th>RMSE</th>
                <th>MAPE (%)</th>
                <th>n</th>
              </tr>
            </thead>
            <tbody>
              {getAllModelsSorted(models.overall).map((model, idx) => (
                <tr key={model.name} className={getRowClass(idx)}>
                  <td className="metrics-rank">{getRankDisplay(idx)}</td>
                  <td className="metrics-model-name">{model.name}</td>
                  <td className="metrics-weight">
                    <strong>
                      {model.weight !== null && model.weight !== undefined 
                        ? model.weight.toFixed(2) 
                        : "-"}
                    </strong>
                  </td>
                  <td>{model.mae?.toFixed(6) ?? "-"}</td>
                  <td>{model.rmse?.toFixed(6) ?? "-"}</td>
                  <td>{model.mape !== null && model.mape !== undefined 
                    ? (model.mape * 100).toFixed(2) 
                    : "-"}</td>
                  <td>{model.n ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Resumen del Top-3 */}
          {getAllModelsSorted(models.overall).length >= 3 && (
            <div className="metrics-top3-summary">
              <strong>🏅 Top-3:</strong>{" "}
              {getAllModelsSorted(models.overall).slice(0, 3).map((m, i) => (
                <span key={m.name}>
                  {getRankDisplay(i)} {m.name}
                  {i < 2 ? " • " : ""}
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
