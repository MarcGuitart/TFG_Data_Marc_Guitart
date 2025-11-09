import React, { useEffect, useState } from "react";
import "./DataPipelineLiveViewer.css";
import Papa from "papaparse";
import CsvChart from "./CsvChart";

const endpoints = null; 

const keyFromTs = (raw) => {
  const s = String(raw).trim();
  const m = s.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/); // HH:MM[:SS]
  if (m) {
    const [_, H, M, S] = m;
    const now = new Date();
    const ms = Date.UTC(
      now.getUTCFullYear(),
      now.getUTCMonth(),
      now.getUTCDate(),
      Number(H), Number(M), Number(S || 0)
    );
    return new Date(ms).toISOString().slice(0, 19) + "Z";
  }
  const n = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})$/); // YYYY-MM-DD HH:MM:SS
  if (n) return new Date(`${n[1]}T${n[2]}Z`).toISOString().slice(0, 19) + "Z";
  const d = new Date(s);
  if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 19) + "Z";
  return s; // fallback
};

// Numérico robusto (soporta "1,23")
const toNum = (v) => {
  if (typeof v === "number") return v;
  const n = parseFloat(String(v).replace(",", "."));
  return Number.isNaN(n) ? undefined : n;
};

// Fecha robusta (soporta varios formatos)
const toDate = (v) => {
  if (v instanceof Date) return v;
  const d = new Date(String(v).trim());
  return !Number.isNaN(d.getTime()) ? d : undefined;
};



export default function DataPipelineLiveViewer() {
  const [kafkaInData, setKafkaInData] = useState([]);
  const [agentLogs, setAgentLogs] = useState([]);
  const [kafkaOutData, setKafkaOutData] = useState([]);

  const [rows, setRows] = useState([]);     // [{ id, timestamp, var }]
  const [ids, setIds] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [isRunning, setIsRunning] = useState(false);

  const emitSelection = (nextId, allRows) => {
    const slice = (allRows || rows).filter(r => r.id === nextId);
    window.dispatchEvent(new CustomEvent("seriesSelected",   { detail: { id: nextId } }));
    window.dispatchEvent(new CustomEvent("seriesDataUpdated",{ detail: { id: nextId, rows: slice } }));
    const normalized = slice
    .map(r => {
      const iso = keyFromTs(r.timestamp);
      const t   = Date.parse(iso);
      const v   = toNum(r.var);
      return Number.isFinite(t) && typeof v === "number" ? { x: iso, t, var: v } : null;
    })
    .filter(Boolean)
    .sort((a,b)=>a.t - b.t);
  window.dispatchEvent(new CustomEvent("seriesChartData", { detail: { id: nextId, points: normalized } }));
  };

  const triggerPipeline = async () => {
    if (isRunning) return;
    setIsRunning(true);
    try {
      const fileInput = document.querySelector('input[type="file"]');
      if (!fileInput?.files?.length) {
        alert("Por favor selecciona un CSV antes de ejecutar el agente.");
        return;
      }
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);

      const up = await fetch("http://localhost:8081/api/upload_csv", { method: "POST", body: formData });
      if (!up.ok) { alert("Falló /api/upload_csv"); return; }

      const res  = await fetch("http://localhost:8081/api/run_window", { method: "POST" });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) { alert("Falló /api/run_window"); return; }

      const loaderRows = json.loader_response?.rows ?? json.loader_rows ?? 0;
      const flushed    = json.rows_flushed ?? 0;
      alert(`Loader: ${loaderRows} filas | Predicciones (flush): ${flushed}`);

      // refrescar gráfico inferior (re-emitimos la base para el id actual)
      const nextId = (selectedId && ids.includes(selectedId)) ? selectedId : (ids[0] || "");
      setSelectedId(nextId);
      if (nextId) emitSelection(nextId);
      window.dispatchEvent(new Event("pipelineUpdated"));
    } catch (e) {
      console.error(e); alert("Error al iniciar el pipeline");
    } finally {
      setIsRunning(false);
    }
  };

  const toEpochMs = (x) => {
   if (x instanceof Date) return x.getTime();
   if (typeof x === "number") return x > 1e12 ? x : x * 1000; // sec->ms
   const d = new Date(String(x).trim());
   return d.getTime();
 };

  const handleFileUpload = (ev) => {
    const file = ev.target.files?.[0];
    if (!file) return;
    setUploadError("");

    Papa.parse(file, {
      header: true, skipEmptyLines: true, dynamicTyping: true,
      complete: (res) => {
        try {
          const raw = Array.isArray(res.data) ? res.data : [];
          if (!raw.length) { setRows([]); setIds([]); setSelectedId(""); setUploadError("CSV vacío."); return; }

          const headers = Object.keys(raw[0]).map(h => String(h).trim().toLowerCase());
          const idKey  = Object.keys(raw[0])[headers.indexOf("id")];
          const tsKey  = Object.keys(raw[0])[headers.indexOf("timestamp")];
          const varKey = Object.keys(raw[0])[headers.indexOf("var")];
          if (!idKey || !tsKey || !varKey) {
            setRows([]); setIds([]); setSelectedId("");
            setUploadError(`Faltan columnas (id,timestamp,var). Encontradas: ${Object.keys(raw[0]).join(", ")}`);
            return;
          }

          const norm = raw
            .filter(r => r[idKey] != null && r[tsKey] != null && r[varKey] != null)
            .map(r => ({
              id: String(r[idKey]).trim(),
              timestamp: String(r[tsKey]).trim(),
              var: toNum(r[varKey])
            }))
             .filter(r => typeof r.var === "number");

          if (!norm.length) { setRows([]); setIds([]); setSelectedId(""); setUploadError("No hay filas válidas."); return; }

          setRows(norm);
          const uniqIds = [...new Set(norm.map(r => r.id))];
          setIds(uniqIds);
          const nextId = uniqIds.includes(selectedId) ? selectedId : uniqIds[0];
          setSelectedId(nextId);
          // 💡 Enviamos al panel de abajo la base de datos (misma serie que “Uploaded Data”)
          emitSelection(nextId, norm);
        } catch (e) {
          console.error(e); setUploadError("Error procesando el CSV.");
        }
      },
      error: (err) => { console.error(err); setUploadError("Error leyendo el archivo CSV."); },
    });
};

const chartData = selectedId
    ? rows
        .filter(r => r.id === selectedId)
        .map(r => ({ x: keyFromTs(r.timestamp), var: toNum(r.var) }))
        .filter(d => d.x && typeof d.var === "number")
        .sort((a, b) => a.x.localeCompare(b.x))
    : [];

  // 🔔 Enviar al PredictionPanel la MISMA serie que pinta arriba, ya normalizada
  useEffect(() => {
      if (!chartData.length) return;
      const points = chartData
        .map(d => ({ t: Date.parse(d.x), var: d.var }))
        .filter(p => Number.isFinite(p.t));
      window.dispatchEvent(new CustomEvent("seriesChartData", { detail: { points } }));
  }, [chartData]);



  const fetchData = async () => {
    try {
      setKafkaInData([]);
      setAgentLogs([]);
      setKafkaOutData([]);
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="viewer-container">
      <h1>Data Pipeline Live Viewer</h1>

      <div className="viewer-grid">
        <Section title="Kafka In" data={kafkaInData}>
          <div style={{ marginTop: 8 }}>
            <input type="file" accept=".csv" onChange={handleFileUpload} />
            {uploadError && (
              <div style={{ color: "#f66", marginTop: 6, fontSize: 12 }}>{uploadError}</div>
            )}
            <button onClick={triggerPipeline} className="start-button" disabled={isRunning}>
              {isRunning ? "Procesando…" : "🚀 Ejecutar agente"}
            </button>
          </div>
        </Section>

        <Section title="Agent Logs" data={agentLogs} />
        <Section title="Kafka Out" data={kafkaOutData} />

        <div className="section">
          <h2>Uploaded Data</h2>
          {rows.length === 0 ? (
            <p>No data uploaded yet.</p>
          ) : (
            <>
              {ids.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <label style={{ marginRight: 8 }}>Series (id):</label>
                  <select
                    value={selectedId}
                    onChange={(e) => {
                      const nextId = e.target.value;
                      setSelectedId(nextId);
                      emitSelection(nextId);
                    }}
                  >
                    {ids.map((id) => (
                      <option key={id} value={id}>{id}</option>
                    ))}
                  </select>
                </div>
              )}
              <CsvChart
                data={chartData
                  .map(d => ({ t: Date.parse(d.x), var: d.var }))
                  .filter(d => Number.isFinite(d.t))
                }
              />
              <pre className="scrollable" style={{ marginTop: 12 }}>
                {chartData.slice(0, 10).map((row, i) => (
                  <div key={i}>{JSON.stringify(row, null, 2)}</div>
                ))}
              </pre>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, data, children }) {
  return (
    <div className="section">
      <h2>{title}</h2>
      <pre className="scrollable">
        {Array.isArray(data) && data.length > 0
          ? data.slice(-10).map((item, idx) => <div key={idx}>{JSON.stringify(item, null, 2)}</div>)
          : null}
      </pre>
      {children}
    </div>
  );
}
