import React, { useEffect, useMemo, useState } from "react";
import AP1Chart from "./AP1Chart";
import AP1PerModelChart from "./AP1PerModelChart";
import AP1GlobalChart from "./AP1GlobalChart";
import AP1VerificationTable from "./AP1VerificationTable";
import AP2SelectorTable from "./AP2SelectorTable";
import AP4MetricsTable from "./AP4MetricsTable";

const API_BASE = "http://localhost:8081";
const DEFAULT_HOURS = 24;

const TABS = {
  AP1_ZOOM: "ap1_zoom",
  AP1_GLOBAL: "ap1_global",
  AP2_SELECTOR: "ap2_selector",
  AP4_METRICS: "ap4_metrics",
  VERIFY: "verify",
};

export default function PredictionPanel() {
  const [currentId, setCurrentId] = useState("");
  const [points, setPoints] = useState([]);
  const [selectorData, setSelectorData] = useState([]);
  const [metricsData, setMetricsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState(TABS.AP1_ZOOM);
  const [zoomStartIdx, setZoomStartIdx] = useState(0);

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
        const params = new URLSearchParams({
          id: currentId,
          hours: String(DEFAULT_HOURS),
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

        // Fetch AP2: Tabla del selector
        try {
          const selectorParams = new URLSearchParams({
            id: currentId,
            hours: String(DEFAULT_HOURS),
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
  }, [currentId, refreshKey]);

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
    { id: TABS.AP1_ZOOM, label: "📊 AP1 Zoom", icon: "zoom" },
    { id: TABS.AP1_GLOBAL, label: "🌍 AP1 Global", icon: "globe" },
    { id: TABS.AP2_SELECTOR, label: "📋 AP2 Selector", icon: "list" },
    { id: TABS.AP4_METRICS, label: "🏆 AP4 Ranking", icon: "medal" },
    { id: TABS.VERIFY, label: "✓ Verify", icon: "check" },
  ];

  return (
    <div style={{ color: "white", padding: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>📈 Adaptive Prediction System</h2>
      </div>

      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 12, padding: "8px", backgroundColor: "#222", borderRadius: 4 }}>
        <strong>Series:</strong> <code style={{ background: "#333", padding: "2px 6px", borderRadius: 3 }}>{currentId || "(ninguna)"}</code>
        {" · "}
        <strong>Observations:</strong> {info.nObs}
        {" · "}
        <strong>Predictions:</strong> {info.nPred}
        {info.nModels > 0 && (
          <> · <strong>Models:</strong> {info.models?.join(", ")}</>
        )}
      </div>

      {/* Tab buttons */}
      {points.length > 0 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {tabButtons.map((btn) => (
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

      {loading && <p style={{ fontSize: 12 }}>Loading data…</p>}
      {error && <p style={{ fontSize: 12, color: "#fca5a5" }}>{error}</p>}

      {!loading && !error && points.length === 0 && (
        <p style={{ fontSize: 12, color: "#999" }}>No data available. Run the pipeline first.</p>
      )}

      {!loading && !error && points.length > 0 && (
        <div>
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
}
