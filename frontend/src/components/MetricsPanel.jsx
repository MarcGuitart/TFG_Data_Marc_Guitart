import React from "react";
import "./MetricsPanel.css"; // opcional, si quieres separar estilos

export default function MetricsPanel({ combined, models, loading, error, selectedId }) {
  if (!selectedId) {
    return (
      <div className="metrics-card">
        <h3 className="metrics-title">Metrics</h3>
        <p className="metrics-text">Select an ID to see metrics.</p>
      </div>
    );
  }

  return (
    <div className="metrics-card">
      <h3 className="metrics-title">Metrics for <span className="metrics-id">{selectedId}</span></h3>

      {loading && <p className="metrics-text">Loading metrics…</p>}

      {error && (
        <p className="metrics-error">
          {error}
        </p>
      )}

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

      {!loading && !error && models && models.overall && (
        <>
          <h4 className="metrics-subtitle">Per-model (telemetry_models)</h4>
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>MAE</th>
                <th>RMSE</th>
                <th>MAPE</th>
                <th>n</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(models.overall).map(([modelName, stats]) => (
                <tr key={modelName}>
                  <td>{modelName}</td>
                  <td>{stats.mae?.toFixed(6) ?? "-"}</td>
                  <td>{stats.rmse?.toFixed(6) ?? "-"}</td>
                  <td>{stats.mape?.toFixed(6) ?? "-"}</td>
                  <td>{stats.n ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
