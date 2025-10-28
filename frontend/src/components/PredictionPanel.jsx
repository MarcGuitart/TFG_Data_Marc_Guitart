import React, { useEffect, useMemo, useState } from "react";
import CsvChart from "./CsvChart";

const HORIZON_STEPS = 1;      // T+1
const MIN_TOL_MS = 250;

export default function PredictionPanel() {
  const [baseChart, setBaseChart] = useState([]);              // [{t:number, var:number}]
  const [currentId, setCurrentId] = useState("");
  const [predData, setPredData] = useState([]);                // [{value:number}] o [{ts:..., value:...}]
  const [allowPredFetch, setAllowPredFetch] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // === Eventos desde el panel superior ===
  useEffect(() => {
    const onSel = (e) => setCurrentId(e.detail?.id || "");
    const onChart = (e) => {
      const pts = Array.isArray(e.detail?.points) ? e.detail.points : [];
      // Esperamos {t, var}
      const norm = pts
        .filter(p => Number.isFinite(p?.t) && typeof p?.var === "number")
        .sort((a,b)=>a.t - b.t);
      setBaseChart(norm);
      setAllowPredFetch(false);
    };
    const onDataUpdated = () => setAllowPredFetch(false);

    window.addEventListener("seriesSelected", onSel);
    window.addEventListener("seriesChartData", onChart);
    window.addEventListener("seriesDataUpdated", onDataUpdated);
    return () => {
      window.removeEventListener("seriesSelected", onSel);
      window.removeEventListener("seriesChartData", onChart);
      window.removeEventListener("seriesDataUpdated", onDataUpdated);
    };
  }, []);

  // === Traer predicciones crudas (pero NO confiar en sus ts) ===
  useEffect(() => {
    let cancel = false;
    const fetchIt = async () => {
      if (!currentId || baseChart.length === 0 || !allowPredFetch) { setPredData([]); return; }
      try {
        const params = new URLSearchParams({ id: currentId, unit: currentId, hours: String(48) });
        const r = await fetch(`http://localhost:8081/api/series?${params.toString()}`);
        const j = await r.json().catch(()=> ({}));
        const predArr = Array.isArray(j?.prediction) ? j.prediction
                      : Array.isArray(j?.predictions) ? j.predictions : [];
        const norm = predArr.map((p) => {
          const val = (typeof p?.value === "number") ? p.value
                    : (typeof p?.yhat  === "number") ? p.yhat
                    : (typeof p?.var   === "number") ? p.var
                    : parseFloat(String(p?.yhat ?? p?.var ?? p?.value ?? "").replace(",", "."));
          return Number.isFinite(val) ? { value: val, ts: Date.parse(String(p?.ts ?? p?.timestamp ?? p?.time ?? p?.t ?? "")) } : null;
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

  // Disparado desde el pipeline
  useEffect(() => {
    const onPipelineUpdated = () => { setAllowPredFetch(true); setRefreshKey(k => k + 1); };
    window.addEventListener("pipelineUpdated", onPipelineUpdated);
    return () => window.removeEventListener("pipelineUpdated", onPipelineUpdated);
  }, []);

  // === Alineación determinista: Uploaded (azul) + Predicción (naranja en T+1, T+2, …) ===
  const merged = useMemo(() => {
    if (!baseChart.length) return [];

    // 1) Step = mediana de diferencias
    const ts = baseChart.map(p => p.t).filter(Number.isFinite).sort((a,b)=>a-b);
    const diffs = [];
    for (let i=1;i<ts.length;i++) { const d = ts[i]-ts[i-1]; if (d>0) diffs.push(d); }
    diffs.sort((a,b)=>a-b);
    const mid = Math.floor(diffs.length/2);
    const stepMs = diffs.length ? (diffs.length%2 ? diffs[mid] : Math.round((diffs[mid-1]+diffs[mid])/2))
                                : 30*60*1000; // fallback 30min
    console.log("[Overlay] stepMs:", stepMs, "lastBase(UTC):", new Date(lastBase).toISOString(),
    "firstPredProjected:", new Date(lastBase + (HORIZON_STEPS)*stepMs).toISOString());

    const tolMs = Math.max(MIN_TOL_MS, Math.floor(stepMs/2));

    // 2) Rejilla base
    const lastBase = ts[ts.length-1];

    // 3) Proyectar predicciones por índice a partir de T+1
    const predsSorted = [...predData].sort((a,b)=>{
      // si j.ts viene bien, respeta orden temporal; si no, al menos queda estable
      if (Number.isFinite(a.ts) && Number.isFinite(b.ts)) return a.ts-b.ts;
      return 0;
    });

    // 4) Construir salida (seed con Uploaded)
    const outMap = new Map(ts.map(t => [t, { t, var: baseChart.find(p=>p.t===t)?.var }]));

    // 5) Colocar preds en t = lastBase + (i+HORIZON_STEPS)*step
    const total = predsSorted.length || 1;
    predsSorted.forEach((p, i) => {
      const tTarget = lastBase + (i + HORIZON_STEPS) * stepMs;
      // Snap a rejilla (por si el consumidor quiere exactitud estricta de multiples de step)
      // Aquí la rejilla es trivial: ya usamos lastBase + k*step
      const pred_conf = Math.max(0.05, (i+1)/total);
      const row = outMap.get(tTarget) ?? { t: tTarget };
      row.prediction = p.value;
      row.pred_conf = pred_conf;
      outMap.set(tTarget, row);
    });

    // 6) Rellenar huecos intermedios (si quieres línea continua en el eje temporal)
    // (Opcional: no extrapolamos, solo devolvemos puntos conocidos)
    return [...outMap.values()].sort((a,b)=>a.t-b.t);
  }, [baseChart, predData]);

  return (
    <div style={{ color: "white" }}>
      <h3>Uploaded + Predicción (sobrepuesto)</h3>
      <div style={{ fontSize: 12, opacity: .8, marginBottom: 8 }}>
        id actual: <code>{currentId || "(sin id)"}</code> · preds: {predData.length}
      </div>
      {merged.length === 0
        ? <p>No hay datos disponibles todavía.</p>
        : <CsvChart data={merged} />
      }
    </div>
  );
}
