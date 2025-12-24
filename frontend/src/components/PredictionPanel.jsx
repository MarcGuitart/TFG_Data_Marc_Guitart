import React, { useEffect, useMemo, useState, useImperativeHandle, forwardRef } from "react";
import AP1Chart from "./AP1Chart";
import AP1PerModelChart from "./AP1PerModelChart";
import AP1GlobalChart from "./AP1GlobalChart";
import AP1VerificationTable from "./AP1VerificationTable";
import AP2SelectorTable from "./AP2SelectorTable";
import AP4MetricsTable from "./AP4MetricsTable";

const API_BASE = "http://localhost:8081";
const DEFAULT_HOURS = 24;
const FULL_HOURS = 999; // Para obtener todos los datos disponibles

const TABS = {
  DEMO: "demo",
  GLOBAL_STATS: "global_stats",
  AP1_GLOBAL: "ap1_global",
  AP2_SELECTOR: "ap2_selector",
  AP4_METRICS: "ap4_metrics",
  AP1_ZOOM: "ap1_zoom",
  VERIFY: "verify",
};

const PredictionPanel = forwardRef((props, ref) => {
  const [currentId, setCurrentId] = useState("");
  const [points, setPoints] = useState([]);
  const [selectorData, setSelectorData] = useState([]);
  const [metricsData, setMetricsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState(TABS.DEMO);
  const [zoomStartIdx, setZoomStartIdx] = useState(0);
  const [viewMode, setViewMode] = useState("demo"); // "demo" (1h) o "full" (todos los datos)

  // Exponer método refreshData para que App.jsx pueda llamarlo
  useImperativeHandle(ref, () => ({
    refreshData: () => {
      setRefreshKey(k => k + 1);
    }
  }));

  // Escuchar selección de serie y eventos de pipeline
  useEffect(() => {
    const onSel = (e) => {
      const id = e.detail?.id || "";
      setCurrentId(id);
      setRefreshKey(k => k + 1);
    };

    const onPipelineUpdated = () => {
      // cuando se ejecuta de nuevo el pipeline, recargamos
      setRefreshKey(k => k + 1);
    };

    window.addEventListener("seriesSelected", onSel);
    window.addEventListener("pipelineUpdated", onPipelineUpdated);

    return () => {
      window.removeEventListener("seriesSelected", onSel);
      window.removeEventListener("pipelineUpdated", onPipelineUpdated);
    };
  }, []);

  // Fetch IDs disponibles al inicio (si no hay currentId)
  useEffect(() => {
    const fetchIds = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/ids`);
        if (!res.ok) return;
        
        const data = await res.json();
        const ids = data.ids || [];
        
        // Si hay IDs y no tenemos ninguno seleccionado, usar el primero
        if (ids.length > 0 && !currentId) {
          console.log("Auto-seleccionando primer ID:", ids[0]);
          setCurrentId(ids[0]);
          setRefreshKey(k => k + 1);
        }
      } catch (err) {
        console.error("Error fetching IDs:", err);
      }
    };

    // Fetch IDs al montar y cada vez que refreshKey cambie
    fetchIds();
  }, [refreshKey]);

  // Fetch a /api/series y endpoints relacionados
  useEffect(() => {
    let cancel = false;

    const fetchData = async () => {
      if (!currentId) {
        setPoints([]);
        setSelectorData([]);
        setMetricsData([]);
        return;
      }
      setLoading(true);
      setError("");
      try {
        const hoursToFetch = viewMode === "full" ? FULL_HOURS : DEFAULT_HOURS;
        const params = new URLSearchParams({
          id: currentId,
          hours: String(hoursToFetch),
        });

        // Fetch serie completa
        const r = await fetch(`${API_BASE}/api/series?${params.toString()}`);
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}`);
        }
        const j = await r.json();
        const pts = Array.isArray(j?.points) ? j.points : [];
        
        if (!cancel) {
          pts.sort((a, b) => (a.t || 0) - (b.t || 0));
          setPoints(pts);
        }

        // Fetch AP2: Tabla del selector (TODOS los datos, no solo 24h)
        try {
          const selectorParams = new URLSearchParams({
            id: currentId,
            hours: String(FULL_HOURS), // Cambiado a FULL_HOURS para obtener todos los datos
          });
          const rSelector = await fetch(`${API_BASE}/api/selector?${selectorParams.toString()}`);
          if (rSelector.ok) {
            const jSelector = await rSelector.json();
            if (!cancel) {
              setSelectorData(Array.isArray(jSelector?.selector_table) ? jSelector.selector_table : []);
            }
          }
        } catch (e) {
          console.warn("[PredictionPanel] error fetching /api/selector", e);
        }

        // Fetch AP4: Métricas por modelo
        try {
          const metricsParams = new URLSearchParams({ id: currentId });
          const rMetrics = await fetch(`${API_BASE}/api/metrics/models/ranked?${metricsParams.toString()}`);
          if (rMetrics.ok) {
            const jMetrics = await rMetrics.json();
            if (!cancel) {
              setMetricsData(Array.isArray(jMetrics?.models) ? jMetrics.models : []);
            }
          }
        } catch (e) {
          console.warn("[PredictionPanel] error fetching /api/metrics/models/ranked", e);
        }
      } catch (e) {
        console.error("[PredictionPanel] error fetching data", e);
        if (!cancel) {
          setError(e.message || "Error loading series");
          setPoints([]);
          setSelectorData([]);
          setMetricsData([]);
        }
      } finally {
        if (!cancel) setLoading(false);
      }
    };

    fetchData();
    return () => {
      cancel = true;
    };
  }, [currentId, refreshKey, viewMode]);

  const info = useMemo(() => {
    if (!points.length) return { nObs: 0, nPred: 0, nModels: 0 };
    const nObs = points.filter(r => typeof r.var === "number").length;
    const nPred = points.filter(r => typeof r.prediction === "number").length;
    const modelKeys = new Set();
    for (const p of points) {
      Object.keys(p).forEach(k => {
        if (!["t", "var", "prediction", "chosen_model", "error_abs", "error_rel"].includes(k) && typeof p[k] === "number") {
          modelKeys.add(k);
        }
      });
    }
    return { nObs, nPred, nModels: modelKeys.size, models: [...modelKeys] };
  }, [points]);

  const tabButtons = [
    { id: TABS.DEMO, label: "🎯 Demo Principal", icon: "presentation" },
    { id: TABS.GLOBAL_STATS, label: "🌐 Vista Global Completa", icon: "analytics" },
    { id: TABS.AP2_SELECTOR, label: "📋 Tabla Selector (AP2)", icon: "list" },
    { id: TABS.AP4_METRICS, label: "🏆 Ranking Modelos (AP4)", icon: "medal" },
    { id: TABS.AP1_GLOBAL, label: "📊 Vista Gráfica (AP1)", icon: "globe" },
    { id: TABS.AP1_ZOOM, label: "🔍 Zoom Detalle", icon: "zoom", hidden: true },
    { id: TABS.VERIFY, label: "✓ Verificación", icon: "check", hidden: true },
  ];

  return (
    <div style={{ color: "white", padding: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>🧠 HyperModel: Sistema de Predicción Adaptativa</h2>
      </div>

      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 12, padding: "8px", backgroundColor: "#222", borderRadius: 4, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <strong>Serie actual:</strong> <code style={{ background: "#333", padding: "2px 6px", borderRadius: 3 }}>{currentId || "sin datos"}</code>
          {" · "}
          <strong>Observaciones:</strong> {info.nObs}
          {" · "}
          <strong>Predicciones:</strong> {info.nPred}
          {info.nModels > 0 && (
            <> · <strong>Modelos activos:</strong> {info.models?.join(", ")}</>
          )}
        </div>
        
        {/* Toggle Vista Demo / Completa */}
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <span style={{ fontSize: 11, opacity: 0.7, marginRight: 4 }}>Modo vista:</span>
          <button
            onClick={() => setViewMode("demo")}
            style={{
              padding: "4px 10px",
              fontSize: 11,
              background: viewMode === "demo" ? "#FF7A00" : "#444",
              border: "1px solid #666",
              borderRadius: 3,
              color: "#fff",
              cursor: "pointer",
              fontWeight: viewMode === "demo" ? "bold" : "normal",
            }}
          >
            📊 Demo (últimas 24h)
          </button>
          <button
            onClick={() => setViewMode("full")}
            style={{
              padding: "4px 10px",
              fontSize: 11,
              background: viewMode === "full" ? "#FF7A00" : "#444",
              border: "1px solid #666",
              borderRadius: 3,
              color: "#fff",
              cursor: "pointer",
              fontWeight: viewMode === "full" ? "bold" : "normal",
            }}
          >
            🌐 Completa (todos los datos)
          </button>
        </div>
      </div>

      {/* Tab buttons */}
      {points.length > 0 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {tabButtons.filter(btn => !btn.hidden).map((btn) => (
            <button
              key={btn.id}
              onClick={() => setActiveTab(btn.id)}
              style={{
                padding: "6px 12px",
                background: activeTab === btn.id ? "#FF7A00" : "#333",
                border: "1px solid #555",
                borderRadius: 4,
                color: "#fff",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: activeTab === btn.id ? "bold" : "normal",
              }}
            >
              {btn.label}
            </button>
          ))}
        </div>
      )}

      {loading && <p style={{ fontSize: 12 }}>Cargando datos…</p>}
      {error && <p style={{ fontSize: 12, color: "#fca5a5" }}>{error}</p>}

      {!loading && !error && points.length === 0 && (
        <p style={{ fontSize: 12, color: "#999" }}>
          Sin datos disponibles. Ejecuta el pipeline primero para cargar una serie temporal.
        </p>
      )}

      {!loading && !error && points.length > 0 && (
        <div>
          {activeTab === TABS.DEMO && (
            <div>
              <div style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: 16, marginBottom: 12 }}>📈 Serie Real vs Predicción Adaptativa</h3>
                <AP1GlobalChart data={points} />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 24 }}>
                <div>
                  <h3 style={{ fontSize: 16, marginBottom: 12 }}>📋 Decisiones del Selector (AP2)</h3>
                  <AP2SelectorTable data={selectorData} maxRows={10} />
                </div>

                <div>
                  <h3 style={{ fontSize: 16, marginBottom: 12 }}>🏆 Ranking de Modelos (AP4)</h3>
                  <AP4MetricsTable data={metricsData} />
                </div>
              </div>
            </div>
          )}

          {activeTab === TABS.GLOBAL_STATS && (
            <div>
              <h3 style={{ fontSize: 18, marginBottom: 16 }}>🌐 Análisis Global Completo - Todos los Datos</h3>
              
              {/* Estadísticas generales */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 24 }}>
                <div style={{ background: "#1a1a1a", padding: 16, borderRadius: 6, border: "1px solid #333" }}>
                  <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>Total de Puntos</div>
                  <div style={{ fontSize: 24, fontWeight: "bold", color: "#4ade80" }}>{points.length}</div>
                </div>
                <div style={{ background: "#1a1a1a", padding: 16, borderRadius: 6, border: "1px solid #333" }}>
                  <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>Observaciones (var)</div>
                  <div style={{ fontSize: 24, fontWeight: "bold", color: "#60a5fa" }}>{info.nObs}</div>
                </div>
                <div style={{ background: "#1a1a1a", padding: 16, borderRadius: 6, border: "1px solid #333" }}>
                  <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>Predicciones (yhat)</div>
                  <div style={{ fontSize: 24, fontWeight: "bold", color: "#f59e0b" }}>{info.nPred}</div>
                </div>
                <div style={{ background: "#1a1a1a", padding: 16, borderRadius: 6, border: "1px solid #333" }}>
                  <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>Modelos Activos</div>
                  <div style={{ fontSize: 24, fontWeight: "bold", color: "#a78bfa" }}>{info.nModels}</div>
                </div>
              </div>

              {/* Distribución de modelos elegidos */}
              <div style={{ background: "#1a1a1a", padding: 16, borderRadius: 6, border: "1px solid #333", marginBottom: 24 }}>
                <h4 style={{ fontSize: 14, marginBottom: 12, color: "#FF7A00" }}>
                  📊 Distribución de Modelos Elegidos (chosen_model)
                </h4>
                {(() => {
                  const modelCounts = {};
                  points.forEach(p => {
                    const m = p.chosen_model;
                    if (m) modelCounts[m] = (modelCounts[m] || 0) + 1;
                  });
                  const total = Object.values(modelCounts).reduce((a, b) => a + b, 0);
                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {Object.entries(modelCounts)
                        .sort((a, b) => b[1] - a[1])
                        .map(([model, count]) => {
                          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                          return (
                            <div key={model} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                              <div style={{ width: 100, fontSize: 12, fontWeight: "bold" }}>{model}</div>
                              <div style={{ flex: 1, background: "#333", borderRadius: 4, height: 24, position: "relative" }}>
                                <div
                                  style={{
                                    background: model === "linear" ? "#3b82f6" : 
                                               model === "poly" ? "#10b981" : 
                                               model === "alphabeta" ? "#f59e0b" : 
                                               model === "kalman" ? "#8b5cf6" : "#6b7280",
                                    height: "100%",
                                    borderRadius: 4,
                                    width: `${pct}%`,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: 11,
                                    fontWeight: "bold",
                                  }}
                                >
                                  {pct}%
                                </div>
                              </div>
                              <div style={{ width: 60, fontSize: 12, textAlign: "right" }}>{count} pts</div>
                            </div>
                          );
                        })}
                    </div>
                  );
                })()}
              </div>

              {/* Gráfico completo */}
              <div style={{ marginBottom: 24 }}>
                <h4 style={{ fontSize: 14, marginBottom: 12, color: "#FF7A00" }}>
                  📈 Visualización Completa de la Serie
                </h4>
                <AP1GlobalChart data={points} />
              </div>

              {/* Tabla completa con todos los puntos */}
              <div style={{ marginBottom: 24 }}>
                <h4 style={{ fontSize: 14, marginBottom: 12, color: "#FF7A00" }}>
                  📋 Tabla Completa de Decisiones (todos los puntos)
                </h4>
                <AP2SelectorTable data={selectorData} maxRows={9999} />
              </div>

              {/* Métricas de rendimiento */}
              <div>
                <h4 style={{ fontSize: 14, marginBottom: 12, color: "#FF7A00" }}>
                  🏆 Ranking Final de Modelos
                </h4>
                <AP4MetricsTable data={metricsData} />
              </div>
            </div>
          )}

          {activeTab === TABS.AP1_ZOOM && (
            <AP1PerModelChart
              data={points}
              startIdx={zoomStartIdx}
              windowSize={40}
              onZoomChange={setZoomStartIdx}
            />
          )}

          {activeTab === TABS.AP1_GLOBAL && (
            <AP1GlobalChart data={points} />
          )}

          {activeTab === TABS.AP2_SELECTOR && (
            <AP2SelectorTable data={selectorData} maxRows={500} />
          )}

          {activeTab === TABS.AP4_METRICS && (
            <AP4MetricsTable data={metricsData} />
          )}

          {activeTab === TABS.VERIFY && (
            <AP1VerificationTable data={points} maxRows={100} />
          )}
        </div>
      )}
    </div>
  );
});

PredictionPanel.displayName = 'PredictionPanel';

export default PredictionPanel;
