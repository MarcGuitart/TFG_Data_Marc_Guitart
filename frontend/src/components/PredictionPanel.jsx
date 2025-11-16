import React, { useEffect, useMemo, useState } from "react";
import CsvChart from "./CsvChart";

const API_BASE = "http://localhost:8081";  // igual que en DataPipelineLiveViewer
const DEFAULT_HOURS = 24;

export default function PredictionPanel() {
  const [currentId, setCurrentId] = useState("");
  const [merged, setMerged] = useState([]);    // [{ t:number, var?:number, prediction?:number }]
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

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
        setMerged([]);
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

        const obsArr = Array.isArray(j?.observed) ? j.observed : [];
        const predArr = Array.isArray(j?.predicted) ? j.predicted : [];

        const n = Math.min(obsArr.length, predArr.length);
        const rows = [];
        for (let i = 0; i < n; i++) {
          const o = obsArr[i];
          const p = predArr[i];
          const tIso = p?.t || o?.t;
          const tNum = Date.parse(String(tIso));
          if (!Number.isFinite(tNum)) continue;

          const yObs = typeof o?.y === "number"
            ? o.y
            : parseFloat(String(o?.y ?? "").replace(",", "."));
          const yHat = typeof p?.y_hat === "number"
            ? p.y_hat
            : parseFloat(String(p?.y_hat ?? "").replace(",", "."));

          const row = { t: tNum };
          if (Number.isFinite(yObs)) row.var = yObs;
          if (Number.isFinite(yHat)) row.prediction = yHat;
          rows.push(row);
        }

        if (!cancel) {
          // Ordenamos por tiempo, por si acaso
          rows.sort((a, b) => a.t - b.t);
          setMerged(rows);
        }
      } catch (e) {
        console.error("[PredictionPanel] error fetching /api/series", e);
        if (!cancel) {
          setError(e.message || "Error loading series");
          setMerged([]);
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
    if (!merged.length) return { nObs: 0, nPred: 0 };
    const nObs = merged.filter(r => typeof r.var === "number").length;
    const nPred = merged.filter(r => typeof r.prediction === "number").length;
    return { nObs, nPred };
  }, [merged]);

  return (
    <div style={{ color: "white" }}>
      <h3>Uploaded + Predicción (sobrepuesto)</h3>
      <div style={{ fontSize: 12, opacity: .8, marginBottom: 8 }}>
        id actual: <code>{currentId || "(sin id)"}</code> ·
        {" "}obs: {info.nObs} · preds: {info.nPred}
      </div>

      {loading && <p style={{ fontSize: 12 }}>Loading series…</p>}
      {error && <p style={{ fontSize: 12, color: "#fca5a5" }}>{error}</p>}

      {!loading && !error && merged.length === 0 && (
        <p style={{ fontSize: 12 }}>No hay datos disponibles todavía.</p>
      )}

      {!loading && !error && merged.length > 0 && (
        <CsvChart data={merged} />
      )}
    </div>
  );
}
