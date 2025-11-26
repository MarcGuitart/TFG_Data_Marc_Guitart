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

  // AP4: Función para obtener top-3 modelos ordenados por weight
  const getTop3Models = (modelsOverall) => {
    if (!modelsOverall) return [];
    
    const modelArray = Object.entries(modelsOverall).map(([name, stats]) => ({
      name,
      ...stats
    }));
    
    // Ordenar por weight descendente (modelos con mayor peso primero)
    modelArray.sort((a, b) => {
      const weightA = a.weight ?? -Infinity;
      const weightB = b.weight ?? -Infinity;
      return weightB - weightA;
    });
    
    // Retornar solo top-3
    return modelArray.slice(0, 3);
  };

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
          <h4 className="metrics-subtitle">
            🏆 Top-3 Models (AP4 - Ranked by Weight)
          </h4>
          <p style={{ fontSize: "12px", color: "#888", margin: "0 0 8px 0" }}>
            💡 Ordenados por weight descendente. Los modelos con mayor peso han demostrado mejor rendimiento.
          </p>
          <table className="metrics-table metrics-table--ap4">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>Weight</th>
                <th>MAE</th>
                <th>RMSE</th>
                <th>MAPE</th>
                <th>n</th>
              </tr>
            </thead>
            <tbody>
              {getTop3Models(models.overall).map((model, idx) => (
                <tr key={model.name} className={idx === 0 ? "metrics-row--best" : ""}>
                  <td className="metrics-rank">
                    {idx === 0 ? "🥇" : idx === 1 ? "🥈" : "🥉"}
                  </td>
                  <td className="metrics-model-name">{model.name}</td>
                  <td className="metrics-weight">
                    <strong>{model.weight !== null ? model.weight.toFixed(2) : "-"}</strong>
                  </td>
                  <td>{model.mae?.toFixed(6) ?? "-"}</td>
                  <td>{model.rmse?.toFixed(6) ?? "-"}</td>
                  <td>{model.mape?.toFixed(6) ?? "-"}</td>
                  <td>{model.n ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mostrar todos los modelos (opcional, colapsible) */}
          {Object.keys(models.overall).length > 3 && (
            <>
              <h4 className="metrics-subtitle" style={{ marginTop: "20px" }}>
                📊 All Models
              </h4>
              <table className="metrics-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Weight</th>
                    <th>MAE</th>
                    <th>RMSE</th>
                    <th>MAPE</th>
                    <th>n</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(models.overall)
                    .map(([modelName, stats]) => ({
                      name: modelName,
                      ...stats
                    }))
                    .sort((a, b) => (b.weight ?? -Infinity) - (a.weight ?? -Infinity))
                    .map(([modelName, stats]) => (
                      <tr key={modelName}>
                        <td>{modelName}</td>
                        <td>{stats.weight !== null ? stats.weight.toFixed(2) : "-"}</td>
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
        </>
      )}
    </div>
  );
}
