import React, { useEffect, useState } from "react";
import CsvChart from "./CsvChart";

export default function PredictionPanel() {
  const [series, setSeries] = useState([]);

  useEffect(() => {
    const fetchSeries = async () => {
      try {
        const res = await fetch("http://localhost:8081/api/series");
        const json = await res.json();

        // Combina var + prediction en un solo dataset por timestamp
        const map = {};
        for (const v of json.var || [])
          map[v.ts] = { timestamp: v.ts, var: v.value };
        for (const p of json.prediction || []) {
          if (!map[p.ts]) map[p.ts] = { timestamp: p.ts };
          map[p.ts].prediction = p.value;
        }

        setSeries(
          Object.values(map).sort((a, b) =>
            a.timestamp.localeCompare(b.timestamp)
          )
        );
      } catch (err) {
        console.error("Error fetching /api/series:", err);
      }
    };

    fetchSeries();
    const t = setInterval(fetchSeries, 5000);

    // 🔥 refresca cuando el pipeline se ejecuta desde el otro panel
    const onPipelineUpdated = () => fetchSeries();
    window.addEventListener("pipelineUpdated", onPipelineUpdated);

    return () => {
      clearInterval(t);
      window.removeEventListener("pipelineUpdated", onPipelineUpdated);
    };
  }, []);

  // 🧠 render del panel
  return (
    <div style={{ color: "white", marginTop: "2rem" }}>
      <h3>Influx Series (var + prediction)</h3>
      {series.length === 0 ? (
        <p>No hay datos disponibles todavía.</p>
      ) : (
        <CsvChart data={series} />
      )}
    </div>
  );
}
