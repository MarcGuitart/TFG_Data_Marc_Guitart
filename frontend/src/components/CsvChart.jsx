import React, { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
} from "recharts";

// Acepta data con { x: ISO } o { t: epoch_ms }, y homogeneiza a { x: ISO }
export default function CsvChart({ data = [] }) {
  const norm = useMemo(() => {
    const toIso = (d) => {
      if (typeof d?.x === "string") return d.x;
      if (Number.isFinite(d?.t)) return new Date(d.t).toISOString().slice(0, 19) + "Z";
      return undefined;
    };
    return (Array.isArray(data) ? data : [])
      .map(d => ({
        x: toIso(d),
        var: typeof d?.var === "number" ? d.var : undefined,
        prediction: typeof d?.prediction === "number" ? d.prediction : undefined,
        pred_conf: typeof d?.pred_conf === "number" ? d.pred_conf : undefined,
      }))
      .filter(d => d.x && (typeof d.var === "number" || typeof d.prediction === "number"));
  }, [data]);

  const fmt = (s) => { try { return new Date(s).toLocaleString(); } catch { return String(s); } };

  if (!norm.length) {
    return <div style={{ width: "100%", height: 320, color: "#ccc" }}>
      (no hay puntos para mostrar)
    </div>;
  }

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer>
        <ComposedChart data={norm} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
          <XAxis dataKey="x" tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
                 minTickGap={40} interval="preserveStartEnd" />
          <YAxis allowDataOverflow width={50} />
          <Tooltip labelFormatter={(v) => fmt(v)}
                   formatter={(value, name) => [value, name === "var" ? "Real" : name === "prediction" ? "Pred" : name]} />
          <Legend />
          <Line type="monotone" dataKey="var" name="Real" stroke="#00A3FF" strokeWidth={2} dot={false} connectNulls />
          <Line type="monotone" dataKey="prediction" name="Pred" stroke="#FF7A00" strokeWidth={2} dot={false} connectNulls />
          <Line
            dataKey="prediction" name="Pred (pts)" stroke="none"
            dot={{ r: 3, fill: "#FF7A00", fillOpacity: (e) => (typeof e?.pred_conf === "number" ? Math.max(0.15, e.pred_conf) : 0.6) }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
