import React, { useState, useEffect, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine
} from "recharts";
import { CheckCircle, XCircle, AlertTriangle, TrendingUp, BarChart3, Lightbulb } from 'lucide-react';

const API_BASE = "http://localhost:8081";

// Colores para modelos (consistentes con otros componentes)
const MODEL_COLORS = {
  linear: "#10B981",
  poly: "#8B5CF6",
  alphabeta: "#EC4899",
  kalman: "#6366F1",
};

/**
 * AP3: Panel de Visualización del Sistema de Pesos con Memoria
 * 
 * Muestra:
 * 1. Gráfico de evolución de pesos por modelo
 * 2. Tabla de estadísticas por modelo
 * 3. Comparación chosen_by_error vs chosen_by_weight
 * 4. Botón para exportar CSV
 */
export default function AP3WeightsPanel({ selectedId }) {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [exportStatus, setExportStatus] = useState("");
  const [view, setView] = useState("chart"); // "chart" | "table" | "stats"

  // Cargar datos cuando cambia el ID
  useEffect(() => {
    if (!selectedId) {
      setHistory([]);
      setStats(null);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setError("");
      try {
        // Fetch history and stats in parallel
        const [histRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/agent/history/${selectedId}?last_n=200`),
          fetch(`${API_BASE}/api/agent/stats/${selectedId}`)
        ]);

        if (!histRes.ok) throw new Error(`History: ${histRes.status}`);
        if (!statsRes.ok) throw new Error(`Stats: ${statsRes.status}`);

        const histData = await histRes.json();
        const statsData = await statsRes.json();

        setHistory(histData.history || []);
        setStats(statsData);
      } catch (e) {
        console.error("[AP3] Error fetching:", e);
        setError(e.message || "Error loading AP3 data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedId]);

  // Preparar datos para el gráfico
  const chartData = useMemo(() => {
    if (!history.length) return [];
    
    // Detectar modelos disponibles
    const modelNames = new Set();
    for (const h of history) {
      Object.keys(h).forEach(k => {
        if (k.startsWith("w_") && !k.startsWith("w_pre_")) {
          modelNames.add(k.replace("w_", ""));
        }
      });
    }

    return history.map((h, idx) => {
      const point = {
        step: h.step || idx,
        ts: h.ts ? new Date(h.ts).toLocaleTimeString() : `[${idx}]`,
      };
      
      // Pesos por modelo
      for (const m of modelNames) {
        point[`w_${m}`] = h[`w_${m}`];
      }
      
      // Añadir info de decisión
      point.chosen_by_error = h.chosen_by_error;
      point.chosen_by_weight = h.chosen_by_weight;
      point.choices_differ = h.choices_differ;
      
      return point;
    });
  }, [history]);

  // Detectar modelos del chartData
  const modelNames = useMemo(() => {
    if (!chartData.length) return [];
    return Object.keys(chartData[0])
      .filter(k => k.startsWith("w_"))
      .map(k => k.replace("w_", ""));
  }, [chartData]);

  // Exportar CSV
  const handleExportCSV = async () => {
    if (!selectedId) return;
    setExportStatus("Exportando...");
    try {
      const res = await fetch(`${API_BASE}/api/agent/export_csv/${selectedId}`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        setExportStatus(`success:CSV exported: ${data.filepath}`);
      } else {
        setExportStatus(`error:Error: ${data.error || data.detail}`);
      }
    } catch (e) {
      setExportStatus(`error:Error: ${e.message}`);
    }
    // Limpiar mensaje después de 5 segundos
    setTimeout(() => setExportStatus(""), 5000);
  };

  if (!selectedId) {
    return (
      <div style={{ color: "#888", padding: 16 }}>
        Selecciona un ID para ver el sistema de pesos AP3.
      </div>
    );
  }

  return (
    <div style={{ padding: "0 16px", color: "#fff" }}>
      {/* Header */}
      <div style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center",
        marginBottom: 12,
        flexWrap: "wrap",
        gap: 8
      }}>
        <h3 style={{ margin: 0 }}>⚖️ AP3: Sistema de Pesos con Memoria</h3>
        
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {/* Botones de vista */}
          <button
            onClick={() => setView("chart")}
            style={{
              padding: "6px 14px",
              background: view === "chart" ? "#FF7A00" : "#333",
              border: "1px solid #555",
              borderRadius: 4,
              color: "#fff",
              cursor: "pointer",
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <TrendingUp size={14} />
            Chart
          </button>
          <button
            onClick={() => setView("table")}
            style={{
              padding: "6px 14px",
              background: view === "table" ? "#FF7A00" : "#333",
              border: "1px solid #555",
              borderRadius: 4,
              color: "#fff",
              cursor: "pointer",
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            History
          </button>
          <button
            onClick={() => setView("stats")}
            style={{
              padding: "6px 14px",
              background: view === "stats" ? "#FF7A00" : "#333",
              border: "1px solid #555",
              borderRadius: 4,
              color: "#fff",
              cursor: "pointer",
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <BarChart3 size={14} />
            Statistics
          </button>
          
          {/* Botón exportar CSV */}
          <button
            onClick={handleExportCSV}
            style={{
              padding: "6px 14px",
              background: "#2563EB",
              border: "1px solid #3B82F6",
              borderRadius: 4,
              color: "#fff",
              cursor: "pointer",
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            � Export CSV
          </button>
        </div>
      </div>

      {/* Status de exportación */}
      {exportStatus && (
        <div style={{ 
          fontSize: 12, 
          padding: "8px 12px", 
          background: exportStatus.startsWith("success:") ? "#064E3B" : exportStatus.startsWith("error:") ? "#7F1D1D" : "#1E3A8A",
          borderRadius: 4,
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          {exportStatus.startsWith("success:") && <CheckCircle size={16} />}
          {exportStatus.startsWith("error:") && <XCircle size={16} />}
          {exportStatus.replace(/^(success:|error:|warning:)/, '')}
        </div>
      )}

      {/* Info del ID */}
      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 12 }}>
        Serie: <code style={{ background: "#333", padding: "2px 6px", borderRadius: 4 }}>{selectedId}</code>
        {" · "}Steps: {history.length}
        {stats?.choices_diff && (
          <>
            {" · "}Decisiones que difieren: <strong style={{ color: "#F59E0B" }}>
              {stats.choices_diff.differ_pct?.toFixed(1)}%
            </strong>
          </>
        )}
      </div>

      {loading && <p style={{ fontSize: 12 }}>Cargando datos AP3…</p>}
      {error && <p style={{ fontSize: 12, color: "#fca5a5" }}>{error}</p>}

      {!loading && !error && (
        <>
          {/* Vista: Gráfico */}
          {view === "chart" && chartData.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ margin: "0 0 8px 0", fontSize: 14 }}>Evolución de Pesos por Modelo</h4>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffffff" />
                  <XAxis 
                    dataKey="step" 
                    stroke="#ffffff"
                    tick={{ fontSize: 10, fill: "#ffffff" }}
                  />
                  <YAxis 
                    stroke="#ffffff"
                    tick={{ fontSize: 10, fill: "#ffffff" }}
                  />
                  <Tooltip 
                    contentStyle={{ background: "#1a1a1a", border: "1px solid #444" }}
                    formatter={(value, name) => [
                      typeof value === 'number' ? value.toFixed(2) : value,
                      name.replace("w_", "")
                    ]}
                  />
                  <Legend />
                  <ReferenceLine y={0} stroke="#ffffffff" strokeDasharray="3 3" />
                  
                  {modelNames.map(m => (
                    <Line
                      key={m}
                      type="monotone"
                      dataKey={`w_${m}`}
                      name={m}
                      stroke={MODEL_COLORS[m] || "#888"}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              
              <p style={{ fontSize: 10, color: "#ffffffff", marginTop: 4 }}>
                Los pesos muestran el "historial acumulado" de cada modelo. 
                Modelo con mayor peso = mejor rendimiento histórico.
              </p>
            </div>
          )}

          {/* Vista: Tabla de historial */}
          {view === "table" && history.length > 0 && (
            <div style={{ maxHeight: 400, overflowY: "auto" }}>
              <table style={{ 
                width: "100%", 
                borderCollapse: "collapse", 
                fontSize: 11 
              }}>
                <thead>
                  <tr style={{ background: "#2a2a2a", position: "sticky", top: 0 }}>
                    <th style={{ padding: 6, borderBottom: "2px solid #444", textAlign: "left" }}>Step</th>
                    <th style={{ padding: 6, borderBottom: "2px solid #444", textAlign: "left" }}>Time</th>
                    {modelNames.map(m => (
                      <th key={m} style={{ 
                        padding: 6, 
                        borderBottom: "2px solid #444", 
                        textAlign: "right",
                        color: MODEL_COLORS[m] || "#888"
                      }}>
                        w_{m}
                      </th>
                    ))}
                    <th style={{ padding: 6, borderBottom: "2px solid #444", textAlign: "center" }}>By Error</th>
                    <th style={{ padding: 6, borderBottom: "2px solid #444", textAlign: "center" }}>By Weight</th>
                    <th style={{ padding: 6, borderBottom: "2px solid #444", textAlign: "center" }}>Diff?</th>
                  </tr>
                </thead>
                <tbody>
                  {history.slice(-100).map((h, i) => (
                    <tr 
                      key={i}
                      style={{ 
                        background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
                        borderBottom: "1px solid #333"
                      }}
                    >
                      <td style={{ padding: 4 }}>{h.step}</td>
                      <td style={{ padding: 4, fontFamily: "monospace", fontSize: 10 }}>
                        {h.ts ? new Date(h.ts).toLocaleTimeString() : "-"}
                      </td>
                      {modelNames.map(m => (
                        <td key={m} style={{ 
                          padding: 4, 
                          textAlign: "right",
                          color: MODEL_COLORS[m] || "#888"
                        }}>
                          {h[`w_${m}`]?.toFixed(1) ?? "-"}
                        </td>
                      ))}
                      <td style={{ 
                        padding: 4, 
                        textAlign: "center",
                        color: MODEL_COLORS[h.chosen_by_error] || "#ccc"
                      }}>
                        {h.chosen_by_error || "-"}
                      </td>
                      <td style={{ 
                        padding: 4, 
                        textAlign: "center",
                        color: MODEL_COLORS[h.chosen_by_weight] || "#ccc",
                        fontWeight: 600
                      }}>
                        {h.chosen_by_weight || "-"}
                      </td>
                      <td style={{ padding: 4, textAlign: "center", display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {h.choices_differ ? <AlertTriangle size={14} style={{ color: '#f59e0b' }} /> : <CheckCircle size={14} style={{ color: '#10b981' }} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Vista: Estadísticas */}
          {view === "stats" && stats && (
            <div>
              {/* Estadísticas de decisiones */}
              <div style={{ 
                background: "#1E3A8A", 
                padding: 12, 
                borderRadius: 8, 
                marginBottom: 16 
              }}>
                <h4 style={{ margin: "0 0 8px 0", fontSize: 14, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <BarChart3 size={16} />
                  Decision Comparison
                </h4>
                <div style={{ display: "flex", gap: 24, flexWrap: "wrap", fontSize: 13 }}>
                  <div>
                    <span style={{ opacity: 0.7 }}>Total steps:</span>{" "}
                    <strong>{stats.choices_diff?.total_steps || 0}</strong>
                  </div>
                  <div>
                    <span style={{ opacity: 0.7 }}>Decisiones iguales:</span>{" "}
                    <strong style={{ color: "#10B981" }}>{stats.choices_diff?.choices_same || 0}</strong>
                  </div>
                  <div>
                    <span style={{ opacity: 0.7 }}>Decisiones que difieren:</span>{" "}
                    <strong style={{ color: "#F59E0B" }}>{stats.choices_diff?.choices_differ || 0}</strong>
                    {" "}({stats.choices_diff?.differ_pct?.toFixed(1) || 0}%)
                  </div>
                </div>
              </div>

              {/* Estadísticas por modelo */}
              <h4 style={{ margin: "0 0 8px 0", fontSize: 14 }}>🏆 Estadísticas por Modelo</h4>
              <table style={{ 
                width: "100%", 
                borderCollapse: "collapse", 
                fontSize: 12 
              }}>
                <thead>
                  <tr style={{ background: "#2a2a2a" }}>
                    <th style={{ padding: 8, borderBottom: "2px solid #444", textAlign: "left" }}>Modelo</th>
                    <th style={{ padding: 8, borderBottom: "2px solid #444", textAlign: "right" }}>Peso Final</th>
                    <th style={{ padding: 8, borderBottom: "2px solid #444", textAlign: "right" }}>Elegido por Error</th>
                    <th style={{ padding: 8, borderBottom: "2px solid #444", textAlign: "right" }}>Elegido por Peso</th>
                    <th style={{ padding: 8, borderBottom: "2px solid #444", textAlign: "right" }}>Veces Rank 1</th>
                    <th style={{ padding: 8, borderBottom: "2px solid #444", textAlign: "right" }}>Error Medio</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.stats && Object.entries(stats.stats)
                    .sort((a, b) => (b[1].final_weight || 0) - (a[1].final_weight || 0))
                    .map(([model, s], idx) => (
                      <tr 
                        key={model}
                        style={{ 
                          background: idx === 0 ? "rgba(16, 185, 129, 0.1)" : "transparent",
                          borderBottom: "1px solid #333"
                        }}
                      >
                        <td style={{ 
                          padding: 8, 
                          color: MODEL_COLORS[model] || "#ccc",
                          fontWeight: 600
                        }}>
                          {idx === 0 && "🥇 "}{model}
                        </td>
                        <td style={{ padding: 8, textAlign: "right" }}>
                          <strong>{s.final_weight?.toFixed(2) ?? "-"}</strong>
                        </td>
                        <td style={{ padding: 8, textAlign: "right" }}>
                          {s.times_chosen_by_error ?? 0}
                        </td>
                        <td style={{ padding: 8, textAlign: "right" }}>
                          {s.times_chosen_by_weight ?? 0}
                        </td>
                        <td style={{ padding: 8, textAlign: "right" }}>
                          {s.times_rank_1 ?? 0}
                        </td>
                        <td style={{ padding: 8, textAlign: "right" }}>
                          {s.avg_error?.toFixed(4) ?? "-"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
              
              <p style={{ fontSize: 11, color: "#aaa", marginTop: 12, display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <Lightbulb size={14} style={{ marginTop: 2, flexShrink: 0 }} />
                <span>
                  The model with the highest final weight is the one that has demonstrated the best historical performance according to the AP3 ranking system.
                </span>
              </p>
            </div>
          )}

          {/* Sin datos */}
          {!loading && history.length === 0 && (
            <p style={{ fontSize: 12, color: "#888" }}>
              No hay datos AP3 disponibles. Ejecuta el pipeline primero.
            </p>
          )}
        </>
      )}
    </div>
  );
}
