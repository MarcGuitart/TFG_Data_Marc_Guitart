import React, { useEffect, useMemo, useState } from "react";
import CsvChart from "./CsvChart";

const HORIZON_STEPS = 1; // T+1 (un solo paso por delante)

export default function PredictionPanel() {
  const [baseChart, setBaseChart] = useState([]);   // [{ t:number, var:number }]
  const [currentId, setCurrentId] = useState("");
  const [predData, setPredData] = useState([]);     // [{ ts?:number, value:number }]
  const [allowPredFetch, setAllowPredFetch] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // ---- Suscripciones a eventos externos (selección + datos base) ----
  useEffect(() => {
    const onSel = (e) => setCurrentId(e.detail?.id || "");
    const onChart = (e) => {
      const pts = Array.isArray(e.detail?.points) ? e.detail.points : [];
      const norm = pts
        .filter(p => Number.isFinite(p?.t) && typeof p?.var === "number")
        .sort((a,b)=>a.t - b.t);
      setBaseChart(norm);
      if (norm.length) { setAllowPredFetch(true); setRefreshKey(k => k + 1); }
    };
    const onDataUpdated = () => { setAllowPredFetch(true); setRefreshKey(k => k + 1); };

    window.addEventListener("seriesSelected", onSel);
    window.addEventListener("seriesChartData", onChart);
    window.addEventListener("seriesDataUpdated", onDataUpdated);
    return () => {
      window.removeEventListener("seriesSelected", onSel);
      window.removeEventListener("seriesChartData", onChart);
      window.removeEventListener("seriesDataUpdated", onDataUpdated);
    };
  }, []);

  useEffect(() => {
    if (currentId) { setAllowPredFetch(true); setRefreshKey(k => k + 1); }
  }, [currentId]);

  // ---- Traer predicciones crudas (NO confiamos en su ts: alineamos por índice) ----
useEffect(() => {
  let cancel = false;

  // estima stepMs a partir de los observados
  const estimateStepMs = () => {
    const ts = baseChart.map(p => +p.t).filter(Number.isFinite).sort((a,b)=>a-b);
    if (ts.length < 2) return 30 * 60 * 1000;
    const diffs = [];
    for (let i=1;i<ts.length;i++) {
      const d = ts[i] - ts[i-1];
      if (d > 0) diffs.push(d);
    }
    if (!diffs.length) return 30 * 60 * 1000;
    const mid = Math.floor(diffs.length/2);
    return (diffs.length % 2) ? diffs[mid] : Math.round((diffs[mid-1] + diffs[mid]) / 2);
  };

  const fetchIt = async () => {
    if (!currentId || baseChart.length === 0 || !allowPredFetch) {
      if (!cancel) setPredData([]);
      return;
    }
    try {
      const stepMs = estimateStepMs();
      // horas necesarias para cubrir N puntos + el T+1
      const needHours = Math.ceil(((baseChart.length + 1) * stepMs) / 3600_000);
      // límites razonables: mínimo 24h, máximo 240h (10 días)
      const hours = Math.max(24, Math.min(240, needHours));

      const params = new URLSearchParams({ id: currentId, hours: String(hours) });
      const r = await fetch(`http://localhost:8081/api/series?${params.toString()}`);
      const j = await r.json().catch(() => ({}));
      const predArr = Array.isArray(j?.predicted) ? j.predicted : [];

      const norm = predArr.map((p) => {
        const raw = (p?.y_hat ?? p?.value ?? p?.var);
        const val = typeof raw === "number" ? raw : parseFloat(String(raw ?? "").replace(",", "."));
        const tsNum = Number(p?.t);
        const ts = Number.isFinite(tsNum) ? tsNum : undefined;
        return Number.isFinite(val) ? { value: val, ts } : null;
      }).filter(Boolean);

      if (!cancel) setPredData(norm);
    } catch {
      if (!cancel) setPredData([]);
    }
  };

  fetchIt();
  const r1 = setTimeout(fetchIt, 1200);
  const r2 = setTimeout(fetchIt, 2500);
  const t  = setInterval(fetchIt, 4000);
  return () => { cancel = true; clearTimeout(r1); clearTimeout(r2); clearInterval(t); };
}, [currentId, baseChart, allowPredFetch, refreshKey]);


  useEffect(() => {
    const onPipelineUpdated = () => { setAllowPredFetch(true); setRefreshKey(k => k + 1); };
    window.addEventListener("pipelineUpdated", onPipelineUpdated);
    return () => window.removeEventListener("pipelineUpdated", onPipelineUpdated);
  }, []);

  // ---- Merge determinista (azul 0..t, naranja 0+1..t+1) ----
  const merged = useMemo(() => {
    try {
      if (!baseChart.length) return [];

      // 1) Ordena y calcula stepMs por diffs (fallback 30 min)
      const ts = baseChart.map(p => p.t).filter(Number.isFinite).sort((a,b)=>a-b);
      if (ts.length === 0) return [];
      const diffs = [];
      for (let i = 1; i < ts.length; i++) {
        const d = ts[i] - ts[i - 1];
        if (d > 0) diffs.push(d);
      }
      const mid = Math.floor(diffs.length / 2);
      const stepMs = diffs.length
        ? (diffs.length % 2 ? diffs[mid] : Math.round((diffs[mid - 1] + diffs[mid]) / 2))
        : 30 * 60 * 1000;

      // 2) Predicciones: no nos fiamos del ts; se usan por índice
      const preds = Array.isArray(predData) ? predData.slice() : [];
      const n = Math.min(preds.length, ts.length); // queremos 0+1..t+1

      // 3) Mapa base con observados (0..t)
      const outMap = new Map(ts.map((t) => [t, { t, var: baseChart.find(p => p.t === t)?.var }]));

      // 4) Proyecta ŷ[i] en ts[i] + stepMs (0+1..t+1)
      const total = n || 1;
      for (let i = 0; i < n; i++) {
        const p = preds[i];
        const tTarget = ts[i] + (HORIZON_STEPS * stepMs);
        const row = outMap.get(tTarget) ?? { t: tTarget };
        row.prediction = p.value;
        row.pred_conf = Math.max(0.05, (i + 1) / total);
        outMap.set(tTarget, row);
      }

      // 5) Devuelve combinado ordenado
      return [...outMap.values()].sort((a,b)=>a.t - b.t);
    } catch (e) {
      console.error("[PredictionPanel] merge error", e);
      return [];
    }
  }, [baseChart, predData]);

  return (
    <div style={{ color: "white" }}>
      <h3>Uploaded + Predicción (sobrepuesto)</h3>
      <div style={{ fontSize: 12, opacity: .8, marginBottom: 8 }}>
        id actual: <code>{currentId || "(sin id)"}</code> · preds: {predData.length}
      </div>
      {merged.length === 0
        ? <p>No hay datos disponibles todavía.</p>
        : <CsvChart data={merged} /> /* var=azul [0..t], prediction=naranja [0+1..t+1] */
      }
    </div>
  );
}
