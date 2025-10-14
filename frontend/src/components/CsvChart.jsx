import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function CsvChart({ data }) {
  // Normalización robusta
  const safe = Array.isArray(data)
    ? data
        .filter(
          (d) =>
            d.timestamp &&
            (typeof d.var === "number" || typeof d.prediction === "number")
        )
        .map((d) => ({
          ...d,
          ts_num: new Date(d.timestamp).getTime(), // eje X continuo
          label: new Date(d.timestamp).toLocaleTimeString("es-ES", {
            hour: "2-digit",
            minute: "2-digit",
          }),
        }))
        .sort((a, b) => a.ts_num - b.ts_num)
    : [];

  return (
    <div
      style={{
        width: "100%",
        height: 240,
        background: "#0d0f13",
        borderRadius: 8,
        padding: 8,
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={safe}>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10 }}
            minTickGap={20}
            stroke="#888"
          />
          <YAxis
            tick={{ fontSize: 10 }}
            domain={["auto", "auto"]}
            stroke="#888"
          />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="var"
            stroke="#00b7ff"
            strokeWidth={2}
            dot={false}
            connectNulls={true}
            name="Dato observado"
          />
          <Line
            type="monotone"
            dataKey="prediction"
            stroke="#ffaa00"
            strokeWidth={2}
            strokeDasharray="4 2"
            dot={false}
            connectNulls={true}
            name="Predicción"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
