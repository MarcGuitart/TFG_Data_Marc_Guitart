import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function CsvChart({ data }) {
  // data: [{ timestamp, var }]
  const safe = Array.isArray(data)
    ? data.filter(
        (d) => d.timestamp != null && typeof d.var === "number" && !Number.isNaN(d.var)
      )
    : [];

  return (
    <div style={{ width: "100%", height: 220, background: "#0d0f13", borderRadius: 8, padding: 8 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={safe}>
          <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} minTickGap={20} />
          <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
          <Tooltip />
          <Line type="monotone" dataKey="var" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
