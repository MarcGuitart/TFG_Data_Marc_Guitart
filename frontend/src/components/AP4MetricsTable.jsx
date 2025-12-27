import React, { useMemo } from "react";

/**
 * AP4: Tabla de métricas por modelo con ranking por peso (Top-3).
 * 
 * Muestra:
 * - Rank (1,2,3,... con badges)
 * - Model name
 * - Weight final (weight_final) - ordenado por esto
 * - MAE, RMSE, MAPE
 * - Error relativo medio (%)
 * 
 * Props:
 * - data: array de modelos con {model, mae, rmse, mape, error_rel_mean, weight_final, weight_mean, n}
 */
export default function AP4MetricsTable({ data = [] }) {
  const processedData = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) {
      return [];
    }
    
    // Ya debería venir ordenado por weight_final DESC, pero nos aseguramos
    return [...data].sort((a, b) => {
      const wA = a.weight_final ?? -Infinity;
      const wB = b.weight_final ?? -Infinity;
      return wB - wA;
    });
  }, [data]);

  if (!processedData.length) {
    return (
      <div style={{ width: "100%", marginTop: 20 }}>
        <h3>AP4: Tabla de Métricas por Modelo</h3>
        <p style={{ color: "#ccc" }}>(no hay datos)</p>
      </div>
    );
  }

  const getBadge = (rank) => {
    const badges = ["🥇", "🥈", "🥉"];
    return rank <= 3 ? badges[rank - 1] : rank;
  };

  const getRowColor = (rank) => {
    if (rank === 1) return "#1a3a2a"; // verde oscuro
    if (rank === 2) return "#1a2a3a"; // azul oscuro
    if (rank === 3) return "#3a2a1a"; // naranja oscuro
    return "#1e1e1e";
  };

  return (
    <div style={{ width: "100%", marginTop: 20, marginBottom: 20 }}>
      <h3>AP4: Ranking de Modelos (Top-3)</h3>
      <p style={{ fontSize: 12, color: "#ffffffff", marginBottom: 10 }}>
        Ordenado por peso final acumulado (weight_final). Métricas globales: MAE, RMSE, MAPE, Error relativo medio (%).
      </p>

      {/* Tabla */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 12,
            backgroundColor: "#1e1e1e",
            color: "#e0e0e0",
          }}
        >
          <thead style={{ backgroundColor: "#2d2d2d", borderBottom: "2px solid #FFD700" }}>
            <tr>
              <th
                style={{
                  padding: "10px",
                  textAlign: "center",
                  borderRight: "1px solid #444",
                  minWidth: 60,
                }}
              >
                Rank
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "left",
                  borderRight: "1px solid #444",
                  minWidth: 100,
                }}
              >
                Model
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "right",
                  borderRight: "1px solid #444",
                  minWidth: 100,
                  color: "#FFD700",
                }}
              >
                Weight Final
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "right",
                  borderRight: "1px solid #444",
                  minWidth: 80,
                }}
              >
                MAE
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "right",
                  borderRight: "1px solid #444",
                  minWidth: 80,
                }}
              >
                RMSE
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "right",
                  borderRight: "1px solid #444",
                  minWidth: 80,
                }}
              >
                MAPE (%)
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "right",
                  borderRight: "1px solid #444",
                  minWidth: 100,
                }}
              >
                Err Rel Mean (%)
              </th>
              <th
                style={{
                  padding: "10px",
                  textAlign: "right",
                  minWidth: 80,
                }}
              >
                N points
              </th>
            </tr>
          </thead>
          <tbody>
            {processedData.map((row, idx) => {
              const rank = idx + 1;
              const badge = getBadge(rank);
              const bgColor = getRowColor(rank);
              
              return (
                <tr
                  key={row.model || idx}
                  style={{
                    backgroundColor: bgColor,
                    borderBottom: "1px solid #333",
                    borderLeft: rank <= 3 ? "4px solid #FFD700" : "4px solid transparent",
                  }}
                >
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "center",
                      borderRight: "1px solid #333",
                      fontWeight: "bold",
                      fontSize: 14,
                    }}
                  >
                    {badge}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      borderRight: "1px solid #333",
                      fontWeight: rank <= 3 ? "bold" : "normal",
                      color: rank <= 3 ? "#FFD700" : "#e0e0e0",
                    }}
                  >
                    {row.model}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "right",
                      borderRight: "1px solid #333",
                      fontWeight: "bold",
                      color: rank <= 3 ? "#FFD700" : "#99ccff",
                    }}
                  >
                    {row.weight_final != null ? row.weight_final.toFixed(2) : "—"}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "right",
                      borderRight: "1px solid #333",
                      color: row.mae != null && row.mae < 1 ? "#4ECDC4" : "#e0e0e0",
                    }}
                  >
                    {row.mae != null ? row.mae.toFixed(4) : "—"}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "right",
                      borderRight: "1px solid #333",
                      color: row.rmse != null && row.rmse < 1 ? "#4ECDC4" : "#e0e0e0",
                    }}
                  >
                    {row.rmse != null ? row.rmse.toFixed(4) : "—"}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "right",
                      borderRight: "1px solid #333",
                      color: row.mape != null && row.mape < 10 ? "#4ECDC4" : row.mape != null && row.mape > 50 ? "#FF6B6B" : "#e0e0e0",
                    }}
                  >
                    {row.mape != null ? row.mape.toFixed(2) : "—"}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "right",
                      borderRight: "1px solid #333",
                      color: row.error_rel_mean != null
                        ? Math.abs(row.error_rel_mean) < 5 ? "#4ECDC4"
                        : Math.abs(row.error_rel_mean) < 15 ? "#FFD93D"
                        : "#FF6B6B"
                        : "#e0e0e0",
                    }}
                  >
                    {row.error_rel_mean != null ? row.error_rel_mean.toFixed(2) : "—"}
                  </td>
                  <td
                    style={{
                      padding: "10px",
                      textAlign: "right",
                      color: "#999",
                    }}
                  >
                    {row.n != null ? row.n : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 15, padding: "12px", backgroundColor: "#252525", borderLeft: "4px solid #FFD700", fontSize: 12 }}>
        <strong>Top-3 Explanation:</strong>
        <ul style={{ margin: "10px 0", paddingLeft: 20 }}>
          <li><strong>🥇 Rank 1:</strong> Highest accumulated weight (best long-term performance)</li>
          <li><strong>🥈 Rank 2:</strong> Second-best weight accumulation</li>
          <li><strong>🥉 Rank 3:</strong> Third-best weight accumulation</li>
          <li><strong>Weight:</strong> Total points earned from the ranking + memory system</li>
          <li><strong>MAE/RMSE/MAPE:</strong> Global error metrics</li>
          <li><strong>Err Rel Mean:</strong> Average relative error (%) across all predictions</li>
        </ul>
      </div>
    </div>
  );
}
