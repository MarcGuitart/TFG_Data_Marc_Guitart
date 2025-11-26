import React, { useEffect, useState } from "react";
import "./DataPipelineLiveViewer.css";
import Papa from "papaparse";
import CsvChart from "./CsvChart";
import MetricsPanel from "./MetricsPanel";

const API_BASE = "http://localhost:8081";
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

  const [rows, setRows] = useState([]);     
  const [ids, setIds] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [metricsCombined, setMetricsCombined] = useState(null);
  const [metricsModels, setMetricsModels] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState(null);

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

    // 1) sube el CSV al backend -> /app/data/uploaded.csv
    const up = await fetch(`${API_BASE}/api/upload_csv`, {
      method: "POST",
      body: formData,
    });
    if (!up.ok) {
      console.error("upload_csv failed", await up.text().catch(() => ""));
      alert("Falló /api/upload_csv");
      return;
    }

    // 2) dispara el pipeline usando uploaded.csv
    const res = await fetch(`${API_BASE}/api/run_window`, { method: "POST" });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      console.error("run_window failed", json);
      alert("Falló /api/run_window");
      return;
    }

    const loaderRows = json.loader_response?.rows ?? json.loader_rows ?? 0;
    const flushed    = json.rows_flushed ?? 0;
    alert(`Loader: ${loaderRows} filas | Predicciones (flush): ${flushed}`);

    const nextId = (selectedId && ids.includes(selectedId)) ? selectedId : (ids[0] || "");
    setSelectedId(nextId);
    if (nextId) emitSelection(nextId);
    window.dispatchEvent(new Event("pipelineUpdated"));
  } catch (e) {
    console.error(e);
    alert("Error al iniciar el pipeline");
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

  const [backendSeries, setBackendSeries] = useState(null);

async function loadBackendSeries() {
  if (!selectedId) return;
  const qs = encodeURIComponent(selectedId);
  const res = await fetch(`${API_BASE}/api/series?id=${qs}&hours=24`);
  if (!res.ok) {
    console.error("Error /api/series", await res.text().catch(() => ""));
    return;
  }
  const data = await res.json();
  console.log("[loadBackendSeries] Received data:", data);
  console.log("[loadBackendSeries] Points count:", data.points?.length ?? 0);
  setBackendSeries(data);
}

  // handleLoadMetrics: Carga métricas del backend
  const handleLoadMetrics = async () => {
    if (!selectedId) return;
    setMetricsLoading(true);
    setMetricsError(null);

    try {
      const qs = encodeURIComponent(selectedId);
      const [resCombined, resModels] = await Promise.all([
        fetch(`${API_BASE}/api/metrics/combined?id=${qs}&start=-3d`),
        fetch(`${API_BASE}/api/metrics/models?id=${qs}&start=-3d`)
      ]);

      if (!resCombined.ok) {
        throw new Error(`combined ${resCombined.status}`);
      }
      if (!resModels.ok) {
        throw new Error(`models ${resModels.status}`);
      }

      const dataCombined = await resCombined.json();
      const dataModels = await resModels.json();

      setMetricsCombined(dataCombined);
      setMetricsModels(dataModels);
    } catch (err) {
      console.error("Error loading metrics", err);
      setMetricsError(err.message || "Error loading metrics");
      setMetricsCombined(null);
      setMetricsModels(null);
    } finally {
      setMetricsLoading(false);
    }
  };

  // helper interno: intento automático de detectar columnas de tiempo y valor
  const autoDetectColumns = (rows) => {
    if (!rows.length) return { tsKey: null, varKey: null };

    const keys = Object.keys(rows[0]);
    const stats = keys.map((key) => {
      let dateScore = 0;
      let numScore = 0;
      let total = 0;

      for (const r of rows.slice(0, 50)) { // mira sólo primeras 50 filas
        const v = r[key];
        if (v == null || v === "") continue;
        total++;

        // ¿parece fecha?
        const d = new Date(String(v).trim());
        if (!Number.isNaN(d.getTime())) {
          dateScore++;
        }

        // ¿parece número?
        const n = toNum(v);
        if (typeof n === "number") {
          numScore++;
        }
      }

      return { key, dateScore, numScore, total };
    });

    // columna candidata a timestamp: la que tenga muchos parseos de fecha
    const bestDate = stats
      .filter(s => s.dateScore >= 3 && s.dateScore >= s.total * 0.6)
      .sort((a, b) => b.dateScore - a.dateScore)[0];

    // columna candidata a valor: la que tenga muchos numéricos
    const bestNum = stats
      .filter(s => s.numScore >= 3 && s.numScore >= s.total * 0.6)
      .sort((a, b) => b.numScore - a.numScore)[0];

    return {
      tsKey: bestDate?.key ?? null,
      varKey: bestNum?.key ?? null,
    };
  };

  const handleFileUpload = (ev) => {
  const file = ev.target.files?.[0];
  if (!file) return;
  setUploadError("");

  Papa.parse(file, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: true,
    complete: (res) => {
      try {
        const raw = Array.isArray(res.data) ? res.data : [];
        if (!raw.length) {
          setRows([]); setIds([]); setSelectedId("");
          setUploadError("CSV vacío.");
          return;
        }

        const headers = Object.keys(raw[0]).map(h => String(h).trim().toLowerCase());

        // intenta detectar ID
        let idKey = Object.keys(raw[0])[headers.indexOf("id")] ?? null;

        // timestamp flexible (primera pasada por nombre)
        let tsKey =
          Object.keys(raw[0])[headers.indexOf("timestamp")] ||
          Object.keys(raw[0])[headers.indexOf("ts")] ||
          Object.keys(raw[0])[headers.indexOf("time")] ||
          null;

        // valor flexible (primera pasada por nombre)
        let varKey =
          Object.keys(raw[0])[headers.indexOf("var")] ||
          Object.keys(raw[0])[headers.indexOf("value")] ||
          Object.keys(raw[0])[headers.indexOf("y")] ||
          Object.keys(raw[0])[headers.indexOf("val")] ||
          null;

        // 🔁 Si no hemos encontrado timestamp o var por nombre, intentamos autodetección
        if (!tsKey || !varKey) {
          const autodetected = autoDetectColumns(raw);
          tsKey = tsKey || autodetected.tsKey;
          varKey = varKey || autodetected.varKey;
        }

        if (!tsKey || !varKey) {
          setRows([]); setIds([]); setSelectedId("");
          setUploadError(
            `CSV no válido. No se han podido detectar columnas de tiempo y valor.\n` +
            `Cabeceras: ${Object.keys(raw[0]).join(", ")}`
          );
          return;
        }

        const norm = raw
          .map(r => {
            const id = idKey ? String(r[idKey]).trim() : "default";
            const ts = String(r[tsKey]).trim();
            const v  = toNum(r[varKey]);

            return (ts && typeof v === "number")
              ? { id, timestamp: ts, var: v }
              : null;
          })
          .filter(Boolean);

        if (!norm.length) {
          setRows([]); setIds([]); setSelectedId("");
          setUploadError("No hay filas válidas (timestamps o valores no parseables).");
          return;
        }

        setRows(norm);
        const uniqIds = [...new Set(norm.map(r => r.id))];
        setIds(uniqIds);

        const nextId = uniqIds.includes(selectedId) ? selectedId : uniqIds[0];
        setSelectedId(nextId);
        emitSelection(nextId, norm);
      } catch (e) {
        console.error(e);
        setUploadError("Error procesando el CSV.");
      }
    },
    error: (err) => {
      console.error(err);
      setUploadError("Error leyendo el archivo CSV.");
    },
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
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="viewer-container">
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

        <div className="section">
          <h2>Uploaded Data</h2>
          {rows.length === 0 ? (
            <p>No data uploaded yet.</p>
          ) : (
            <>
              {ids.length > 0 && (
                <div className="controls" style={{ marginBottom: 8 }}>
                  <select
                    value={selectedId}
                    onChange={(e) => setSelectedId(e.target.value)}
                  >
                    <option value="">Select ID…</option>
                    {ids.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </select>

                  <button onClick={loadBackendSeries} disabled={!selectedId}>
                    Load backend series (per-model)
                  </button>

                  <button
                    onClick={handleLoadMetrics}
                    disabled={!selectedId || metricsLoading}
                    style={{ marginLeft: "8px" }}
                  >
                    {metricsLoading ? "Loading metrics…" : "Load metrics"}
                  </button>
                </div>
              )}
              <CsvChart
                data={chartData
                  .map(d => ({ t: Date.parse(d.x), var: d.var }))
                  .filter(d => Number.isFinite(d.t))
                }
              />

              {backendSeries && (
                <>
                  <h3 style={{ color: "#00A3FF", marginTop: 20 }}>
                    📊 Backend Series (Per-Model Predictions)
                  </h3>
                  {backendSeries.points && backendSeries.points.length > 0 ? (
                    <>
                      <div style={{ 
                        fontSize: 13, 
                        color: "#999", 
                        marginBottom: 12,
                        padding: "8px 12px",
                        background: "#1a1a1a",
                        borderRadius: "6px",
                        border: "1px solid #333"
                      }}>
                        <div><strong>ID:</strong> {selectedId}</div>
                        <div><strong>Points:</strong> {backendSeries.points.length}</div>
                        <div><strong>Models:</strong> {Object.keys(backendSeries.models || {}).join(", ") || "ninguno"}</div>
                      </div>

                      {/* Gráfico combinado - TODOS los modelos juntos */}
                      <div style={{ marginBottom: 20 }}>
                        <h4 style={{ color: "#00A3FF", fontSize: 14, marginBottom: 8 }}>
                          🔀 Vista Combinada (Todos los Modelos)
                        </h4>
                        <p style={{ fontSize: 11, color: "#888", marginBottom: 8 }}>
                          💡 <em>Real</em> (blue) · <em>Combined Pred</em> (orange dashed) · <em>Models</em> (colored)
                        </p>
                        <CsvChart data={backendSeries.points} />
                      </div>

                      {/* AP2: Tabla de modelos elegidos */}
                      {backendSeries.chosen_models && backendSeries.chosen_models.length > 0 && (
                        <div style={{
                          marginTop: 20,
                          marginBottom: 20,
                          padding: "12px",
                          background: "#1a1a1a",
                          borderRadius: "8px",
                          border: "2px solid #00A3FF40"
                        }}>
                          <h4 style={{ color: "#00A3FF", fontSize: 14, marginBottom: 12 }}>
                            🎯 Selector Adaptativo - Modelo Elegido por Instante
                          </h4>
                          <p style={{ fontSize: 11, color: "#888", marginBottom: 12 }}>
                            Muestra qué modelo fue seleccionado en cada timestamp (modo adaptativo: elige el de menor error)
                          </p>
                          <div style={{ 
                            maxHeight: "200px", 
                            overflowY: "auto",
                            fontSize: 12,
                            fontFamily: "monospace"
                          }}>
                            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                              <thead style={{ position: "sticky", top: 0, background: "#1a1a1a" }}>
                                <tr>
                                  <th style={{ textAlign: "left", padding: "6px", borderBottom: "1px solid #333", color: "#00A3FF" }}>
                                    Timestamp
                                  </th>
                                  <th style={{ textAlign: "left", padding: "6px", borderBottom: "1px solid #333", color: "#00A3FF" }}>
                                    Modelo Elegido
                                  </th>
                                </tr>
                              </thead>
                              <tbody>
                                {backendSeries.chosen_models.slice(-20).reverse().map((c, idx) => {
                                  const modelColors = {
                                    'ab_fast': '#10B981',
                                    'linear_8': '#6366F1', 
                                    'poly2_12': '#EC4899',
                                  };
                                  const color = modelColors[c.model] || '#999';
                                  return (
                                    <tr key={idx}>
                                      <td style={{ padding: "4px 6px", borderBottom: "1px solid #222", color: "#ccc" }}>
                                        {new Date(c.t).toLocaleString()}
                                      </td>
                                      <td style={{ 
                                        padding: "4px 6px", 
                                        borderBottom: "1px solid #222",
                                        color: color,
                                        fontWeight: 600
                                      }}>
                                        {c.model}
                                      </td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                          <div style={{ marginTop: 8, fontSize: 11, color: "#666" }}>
                            Mostrando últimos 20 puntos · Total: {backendSeries.chosen_models.length}
                          </div>
                        </div>
                      )}

                      {/* AP3: Panel de Evolución de Pesos */}
                      {backendSeries.weights && Object.keys(backendSeries.weights).length > 0 && (
                        <div style={{ marginTop: 30 }}>
                          <h4 style={{ color: "#00A3FF", fontSize: 14, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                            <span>⚖️ Evolución de Pesos (AP3 - Sistema de Ranking)</span>
                          </h4>
                          <div style={{ 
                            padding: "16px", 
                            background: "#1a1a1a", 
                            borderRadius: "8px",
                            border: "1px solid #333"
                          }}>
                            {/* Gráfico de evolución de pesos */}
                            {(() => {
                              const modelColors = {
                                'ab_fast': '#10B981',
                                'linear_8': '#6366F1', 
                                'poly2_12': '#EC4899',
                              };

                              // Convertir weights a formato para CsvChart
                              const weightsData = [];
                              const allTimes = new Set();

                              // Recopilar todos los timestamps únicos
                              Object.entries(backendSeries.weights).forEach(([modelName, series]) => {
                                series.forEach(point => {
                                  allTimes.add(new Date(point.time).getTime());
                                });
                              });

                              // Crear puntos con todos los modelos
                              Array.from(allTimes).sort().forEach(timestamp => {
                                const point = {
                                  t: timestamp,
                                  x: new Date(timestamp).toISOString()
                                };
                                
                                Object.entries(backendSeries.weights).forEach(([modelName, series]) => {
                                  const matchingPoint = series.find(p => 
                                    new Date(p.time).getTime() === timestamp
                                  );
                                  if (matchingPoint) {
                                    point[modelName] = matchingPoint.weight;
                                  }
                                });

                                weightsData.push(point);
                              });

                              const weightsSeries = Object.keys(backendSeries.weights).map(modelName => ({
                                key: modelName,
                                label: modelName,
                                color: modelColors[modelName] || '#999',
                                yAxisId: 'weights'
                              }));

                              return weightsData.length > 0 ? (
                                <div>
                                  <CsvChart 
                                    data={weightsData} 
                                    series={weightsSeries}
                                    height={300}
                                    syncId="weights-sync"
                                  />
                                  <div style={{ marginTop: 12, padding: "12px", background: "#0a0a0a", borderRadius: "6px" }}>
                                    <div style={{ fontSize: 12, color: "#999", marginBottom: 8 }}>
                                      <strong style={{ color: "#00A3FF" }}>💡 Cómo funciona el sistema de pesos (AP3):</strong>
                                    </div>
                                    <ul style={{ fontSize: 11, color: "#888", margin: 0, paddingLeft: 20 }}>
                                      <li>En cada timestamp, se ordenan los modelos por error (menor error = mejor)</li>
                                      <li>Se restan 1 punto a todos los modelos (penalización base)</li>
                                      <li>Se asignan puntos según ranking: M puntos al mejor, M-1 al segundo, ..., 1 al peor</li>
                                      <li>Los pesos pueden ser negativos para crear contraste real</li>
                                      <li>Los modelos con pesos más altos han demostrado mejor rendimiento histórico</li>
                                    </ul>
                                    <div style={{ marginTop: 12, fontSize: 11, color: "#666" }}>
                                      <strong>Últimos pesos:</strong> {
                                        Object.entries(backendSeries.weights).map(([model, series]) => {
                                          const lastWeight = series[series.length - 1]?.weight || 0;
                                          const color = modelColors[model] || '#999';
                                          return (
                                            <span key={model} style={{ 
                                              marginLeft: 12,
                                              color: color,
                                              fontWeight: 600
                                            }}>
                                              {model}: {lastWeight.toFixed(1)}
                                            </span>
                                          );
                                        })
                                      }
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div style={{ color: "#666", fontSize: 12 }}>
                                  No hay datos de pesos disponibles
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                      )}

                      {/* Gráficos individuales - UN modelo por gráfico */}
                      <div style={{ marginTop: 30 }}>
                        <h4 style={{ color: "#00A3FF", fontSize: 14, marginBottom: 12 }}>
                          📈 Vista Individual por Modelo
                        </h4>
                        {Object.keys(backendSeries.models || {}).map((modelName, idx) => {
                          // Crear datos filtrados: solo Real + este modelo
                          const filteredData = backendSeries.points.map(p => ({
                            t: p.t,
                            x: new Date(p.t).toISOString(),
                            var: p.var,
                            [modelName]: p[modelName]
                          }));

                          const modelColors = {
                            'ab_fast': '#10B981',
                            'linear_8': '#6366F1', 
                            'poly2_12': '#EC4899',
                            'kalman': '#F59E0B',
                            'alphabeta': '#8B5CF6'
                          };

                          const color = modelColors[modelName] || '#999';

                          return (
                            <div key={modelName} style={{ 
                              marginBottom: 24,
                              padding: "12px",
                              background: "#1a1a1a",
                              borderRadius: "8px",
                              border: `2px solid ${color}40`
                            }}>
                              <h5 style={{ 
                                color: color, 
                                fontSize: 13, 
                                marginBottom: 8,
                                fontWeight: 600
                              }}>
                                {modelName.toUpperCase()}
                              </h5>
                              <CsvChart data={filteredData} />
                            </div>
                          );
                        })}
                      </div>
                    </>
                  ) : (
                    <p style={{ fontSize: 12, color: "#f66", padding: "12px", background: "#2a1a1a", borderRadius: "6px" }}>
                      ⚠️ No hay puntos disponibles. Asegúrate de haber ejecutado el pipeline primero y que el agente esté escribiendo datos a InfluxDB.
                    </p>
                  )}
                </>
              )}

              <pre className="scrollable" style={{ marginTop: 12 }}>
                {chartData.slice(0, 10).map((row, i) => (
                  <div key={i}>{JSON.stringify(row, null, 2)}</div>
                ))}
              </pre>
              <MetricsPanel
                combined={metricsCombined}
                models={metricsModels}
                loading={metricsLoading}
                error={metricsError}
                selectedId={selectedId}
              />
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
