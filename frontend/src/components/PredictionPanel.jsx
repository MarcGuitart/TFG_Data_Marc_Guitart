import React, { useEffect, useMemo, useState } from "react";
import AP1Chart from "./AP1Chart";
import AP1VerificationTable from "./AP1VerificationTable";
import AP2SelectorTable from "./AP2SelectorTable";

const API_BASE = "http://localhost:8081";  // igual que en DataPipelineLiveViewer
const DEFAULT_HOURS = 24;

// Vistas disponibles
const VIEWS = {
  CHART: "chart",
  VERIFY: "verify",
  SELECTOR: "selector",
};

export default function PredictionPanel() {
  const [currentId, setCurrentId] = useState("");
  // AP1: Usamos `points` del backend que ya trae todo alineado
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [view, setView] = useState(VIEWS.CHART);

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

  // Fetch a /api/series cuando cambia id o refreshKey
  useEffect(() => {
    let cancel = false;

    const fetchSeries = async () => {
      if (!currentId) {
        setPoints([]);
        return;
      }
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({
          id: currentId,
          hours: String(DEFAULT_HOURS),
        });
        const r = await fetch(`${API_BASE}/api/series?${params.toString()}`);
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}`);
        }
        const j = await r.json();

        // AP1: Usamos directamente `points` que ya viene del backend
        // con estructura: {t, var, prediction, chosen_model, linear, poly, alphabeta, kalman, ...}
        const pts = Array.isArray(j?.points) ? j.points : [];
        
        if (!cancel) {
          // Ordenamos por tiempo, por si acaso
          pts.sort((a, b) => (a.t || 0) - (b.t || 0));
          setPoints(pts);
        }
      } catch (e) {
        console.error("[PredictionPanel] error fetching /api/series", e);
        if (!cancel) {
          setError(e.message || "Error loading series");
          setPoints([]);
        }
      } finally {
        if (!cancel) setLoading(false);
      }
    };

    fetchSeries();
    return () => {
      cancel = true;
    };
  }, [currentId, refreshKey]);

  const info = useMemo(() => {
    if (!points.length) return { nObs: 0, nPred: 0, nModels: 0 };
    const nObs = points.filter(r => typeof r.var === "number").length;
    const nPred = points.filter(r => typeof r.prediction === "number").length;
    // Detectar modelos presentes
    const modelKeys = new Set();
    for (const p of points) {
      Object.keys(p).forEach(k => {
        if (!["t", "var", "prediction", "chosen_model"].includes(k) && typeof p[k] === "number") {
          modelKeys.add(k);
        }
      });
    }
    return { nObs, nPred, nModels: modelKeys.size, models: [...modelKeys] };
  }, [points]);

  return (
    <div style={{ color: "white", padding: "0 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>📈 Predicciones Adaptativas</h3>
        {points.length > 0 && (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setView(VIEWS.CHART)}
              style={{
                padding: "4px 12px",
                background: view === VIEWS.CHART ? "#FF7A00" : "#333",
                border: "1px solid #555",
                borderRadius: 4,
                color: "#fff",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              📊 Gráfico
            </button>
            <button
              onClick={() => setView(VIEWS.SELECTOR)}
              style={{
                padding: "4px 12px",
                background: view === VIEWS.SELECTOR ? "#FF7A00" : "#333",
                border: "1px solid #555",
                borderRadius: 4,
                color: "#fff",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              📋 Selector (AP2)
            </button>
            <button
              onClick={() => setView(VIEWS.VERIFY)}
              style={{
                padding: "4px 12px",
                background: view === VIEWS.VERIFY ? "#FF7A00" : "#333",
                border: "1px solid #555",
                borderRadius: 4,
                color: "#fff",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              ✓ Verificación
            </button>
          </div>
        )}
      </div>
      
      <div style={{ fontSize: 12, opacity: .8, marginBottom: 12 }}>
        Serie: <code style={{ background: "#333", padding: "2px 6px", borderRadius: 4 }}>{currentId || "(ninguna)"}</code>
        {" · "}Observaciones: {info.nObs}
        {" · "}Predicciones: {info.nPred}
        {info.nModels > 0 && (
          <> · Modelos: {info.models?.join(", ")}</>
        )}
      </div>

      {loading && <p style={{ fontSize: 12 }}>Cargando serie…</p>}
      {error && <p style={{ fontSize: 12, color: "#fca5a5" }}>{error}</p>}

      {!loading && !error && points.length === 0 && (
        <p style={{ fontSize: 12 }}>No hay datos disponibles. Ejecuta el pipeline primero.</p>
      )}

      {!loading && !error && points.length > 0 && (
        view === VIEWS.VERIFY ? (
          <AP1VerificationTable data={points} maxRows={50} />
        ) : view === VIEWS.SELECTOR ? (
          <AP2SelectorTable data={points} maxRows={100} />
        ) : (
          <AP1Chart data={points} />
        )
      )}
    </div>
  );
}
