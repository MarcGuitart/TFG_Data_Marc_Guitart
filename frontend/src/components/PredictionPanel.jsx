import React, { useEffect, useState } from "react";
import CsvChart from "./CsvChart";

export default function PredictionPanel() {
  const [series, setSeries] = useState([]);

  useEffect(() => {
    const fetchSeries = async () => {
      try {
        const res = await fetch("http://localhost:8081/api/series");
        const json = await res.json();

        // Combinar var + prediction por timestamp
        const map = {};
        for (const v of json.var || []) {
          map[v.ts] = { timestamp: v.ts, var: v.value };
        }
        for (const p of json.prediction || []) {
          if (!map[p.ts]) map[p.ts] = { timestamp: p.ts };
          map[p.ts].prediction = p.value;
        }

        setSeries(Object.values(map).sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
      } catch (err) {
        console.error("Error fetching /api/series:", err);
      }
    };
    fetchSeries();
    const t = setInterval(fetchSeries, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{ color: "white" }}>
      <h3>Influx Series (var + prediction)</h3>
      <CsvChart data={series} />
    </div>
  );
}
