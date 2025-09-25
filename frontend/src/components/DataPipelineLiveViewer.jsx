import React, { useEffect, useState } from "react";
import "./DataPipelineLiveViewer.css";
import Papa from "papaparse";
import CsvChart from "./CsvChart";

const endpoints = {
  kafkaIn: "http://localhost:8081/kafka/in",
  agent: "http://localhost:8081/agent",
  kafkaOut: "http://localhost:8081/kafka/out",
};

const triggerPipeline = async () => {
  try {
    const res = await fetch('http://localhost:8081/start', { method: 'POST' });
    const json = await res.json();
    alert(`Datos enviados: ${json.sent}`);
  } catch (err) {
    alert("Error al iniciar el pipeline");
    console.error(err);
  }
};


export default function DataPipelineLiveViewer() {
  const [kafkaInData, setKafkaInData] = useState([]);
  const [agentLogs, setAgentLogs] = useState([]);
  const [kafkaOutData, setKafkaOutData] = useState([]);
  

  // CSV subido y estado de selección
  const [rows, setRows] = useState([]);     // [{ id, timestamp, var }]
  const [ids, setIds] = useState([]);       // ['unit_01', ...]
  const [selectedId, setSelectedId] = useState("");
  const [uploadError, setUploadError] = useState("");

  // --- CSV UPLOAD: formato estricto id,timestamp,var (case-insensitive) ---
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
            setRows([]);
            setIds([]);
            setSelectedId("");
            setUploadError("CSV vacío o sin filas válidas.");
            return;
          }

          // Normaliza headers
          const headers = Object.keys(raw[0]);
          const findKey = (name) =>
            headers.find((h) => String(h).trim().toLowerCase() === name);

          const idKey = findKey("id");
          const tsKey = findKey("timestamp");
          const varKey = findKey("var");

          if (!idKey || !tsKey || !varKey) {
            setRows([]);
            setIds([]);
            setSelectedId("");
            setUploadError(
              `Faltan columnas. Requeridas: id, timestamp, var. Encontradas: ${headers.join(", ")}`
            );
            return;
          }

          // Normaliza filas
          const norm = raw
            .filter((r) => r[idKey] != null && r[tsKey] != null && r[varKey] != null)
            .map((r) => ({
              id: String(r[idKey]).trim(),
              timestamp: String(r[tsKey]).trim(),
              var: Number(r[varKey]),
            }))
            .filter((r) => !Number.isNaN(r.var));

          if (!norm.length) {
            setRows([]);
            setIds([]);
            setSelectedId("");
            setUploadError("No hay filas válidas tras normalizar.");
            return;
          }

          setRows(norm);

          const uniqIds = [...new Set(norm.map((r) => r.id))];
          setIds(uniqIds);
          setSelectedId((prev) => (prev && uniqIds.includes(prev) ? prev : uniqIds[0]));
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

  // Datos para el chart: filtra por id seleccionado
  const chartData = selectedId ? rows.filter((r) => r.id === selectedId) : [];

  // Backend (placeholder mientras no esté encendido)
  const fetchData = async () => {
    try {
      const safeFetch = (u) =>
        fetch(u).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
      const [inJson, agentJson, outJson] = await Promise.all([
        safeFetch(endpoints.kafkaIn),
        safeFetch(endpoints.agent),
        safeFetch(endpoints.kafkaOut),
      ]);
      setKafkaInData(inJson.messages || []);
      setAgentLogs(agentJson.logs || []);
      setKafkaOutData(outJson.messages || []);
    } catch {
      /* silenciar temporalmente */
    }
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
              <div style={{ color: "#f66", marginTop: 6, fontSize: 12 }}>
                {uploadError}
              </div>
            )}
            <button onClick={triggerPipeline} className="start-button">
              🚀 Ejecutar agente
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
                    onChange={(e) => setSelectedId(e.target.value)}
                  >
                    {ids.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <CsvChart data={chartData} /> {/* espera {timestamp, var} */}
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
          ? data.slice(-10).map((item, idx) => (
              <div key={idx}>{JSON.stringify(item, null, 2)}</div>
            ))
          : null}
      </pre>
      {children}
    </div>
  );
}
