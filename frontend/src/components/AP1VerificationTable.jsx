import React, { useMemo } from "react";

// AP1: Colores para modelos
const MODEL_COLORS = {
  linear: "#10B981",
  poly: "#8B5CF6",
  alphabeta: "#EC4899",
  kalman: "#6366F1",
};

/**
 * AP1: Tabla de verificación que muestra para cada timestamp:
 * - El valor real
 * - El valor adaptativo (prediction)
 * - El modelo elegido
 * - Los valores de todos los modelos
 * - Verificación de que y_adaptive == models[chosen]
 */
export default function AP1VerificationTable({ data = [], maxRows = 20 }) {
  const { rows, modelKeys, hasInconsistencies } = useMemo(() => {
    const modelKeys = new Set();
    
    // Detectar modelos
    for (const p of data) {
      Object.keys(p).forEach(k => {
        if (!["t", "x", "var", "prediction", "chosen_model", "idx"].includes(k) && 
            typeof p[k] === "number") {
          modelKeys.add(k);
        }
      });
    }
    
    const models = [...modelKeys].sort();
    
    // Verificar consistencia
    let hasInconsistencies = false;
    const rows = data.slice(-maxRows).map((p, i) => {
      const chosen = p.chosen_model;
      const yAdaptive = p.prediction;
      const yChosen = chosen ? p[chosen] : null;
      
      let consistent = null;
      if (yAdaptive !== null && yAdaptive !== undefined && yChosen !== null && yChosen !== undefined) {
        consistent = Math.abs(yAdaptive - yChosen) < 1e-6;
        if (!consistent) hasInconsistencies = true;
      }
      
      const ts = p.t ? new Date(p.t).toLocaleTimeString() : `[${i}]`;
      
      return {
        idx: i,
        ts,
        var: p.var,
        prediction: yAdaptive,
        chosen_model: chosen,
        models: models.reduce((acc, m) => {
          acc[m] = p[m];
          return acc;
        }, {}),
        consistent,
      };
    });
    
    return { rows, modelKeys: models, hasInconsistencies };
  }, [data, maxRows]);

  if (!rows.length) {
    return <div style={{ color: "#888", fontSize: 12 }}>Sin datos para verificar</div>;
  }

  return (
    <div style={{ marginTop: 16 }}>
      <h4 style={{ margin: "0 0 8px 0", color: "#f0f0f0" }}>
        🔎 Tabla de Verificación AP1
        {hasInconsistencies && (
          <span style={{ color: "#ef4444", marginLeft: 8, fontSize: 12 }}>
            ⚠️ Inconsistencias detectadas
          </span>
        )}
        {!hasInconsistencies && rows.some(r => r.consistent !== null) && (
          <span style={{ color: "#10B981", marginLeft: 8, fontSize: 12 }}>
            ✅ Consistente
          </span>
        )}
      </h4>
      <div style={{ overflowX: "auto", maxHeight: 300, overflowY: "auto" }}>
        <table style={{ 
          width: "100%", 
          borderCollapse: "collapse", 
          fontSize: 11,
          color: "#e0e0e0"
        }}>
          <thead>
            <tr style={{ background: "#2a2a2a", position: "sticky", top: 0 }}>
              <th style={{ padding: "6px 8px", borderBottom: "1px solid #444", textAlign: "left" }}>Time</th>
              <th style={{ padding: "6px 8px", borderBottom: "1px solid #444", textAlign: "right", color: "#00A3FF" }}>Real</th>
              <th style={{ padding: "6px 8px", borderBottom: "1px solid #444", textAlign: "right", color: "#FF7A00" }}>Adaptive</th>
              <th style={{ padding: "6px 8px", borderBottom: "1px solid #444", textAlign: "center" }}>Chosen</th>
              {modelKeys.map(m => (
                <th key={m} style={{ 
                  padding: "6px 8px", 
                  borderBottom: "1px solid #444", 
                  textAlign: "right",
                  color: MODEL_COLORS[m] || "#888"
                }}>
                  {m}
                </th>
              ))}
              <th style={{ padding: "6px 8px", borderBottom: "1px solid #444", textAlign: "center" }}>✓</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr 
                key={i}
                style={{ 
                  background: r.consistent === false ? "rgba(239, 68, 68, 0.15)" : "transparent",
                  borderBottom: "1px solid #333"
                }}
              >
                <td style={{ padding: "4px 8px", fontFamily: "monospace" }}>{r.ts}</td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: "#00A3FF" }}>
                  {r.var?.toFixed(2) ?? "-"}
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: "#FF7A00", fontWeight: 600 }}>
                  {r.prediction?.toFixed(2) ?? "-"}
                </td>
                <td style={{ 
                  padding: "4px 8px", 
                  textAlign: "center",
                  color: MODEL_COLORS[r.chosen_model] || "#ccc",
                  fontWeight: 600
                }}>
                  {r.chosen_model || "-"}
                </td>
                {modelKeys.map(m => {
                  const isChosen = m === r.chosen_model;
                  return (
                    <td 
                      key={m} 
                      style={{ 
                        padding: "4px 8px", 
                        textAlign: "right",
                        color: MODEL_COLORS[m] || "#888",
                        fontWeight: isChosen ? 700 : 400,
                        background: isChosen ? "rgba(255, 122, 0, 0.1)" : "transparent"
                      }}
                    >
                      {r.models[m]?.toFixed(2) ?? "-"}
                    </td>
                  );
                })}
                <td style={{ padding: "4px 8px", textAlign: "center" }}>
                  {r.consistent === true && "✅"}
                  {r.consistent === false && "❌"}
                  {r.consistent === null && "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ fontSize: 10, color: "#888", marginTop: 4 }}>
        Mostrando últimos {rows.length} puntos. La columna "✓" verifica que Adaptive == models[Chosen].
      </div>
    </div>
  );
}
