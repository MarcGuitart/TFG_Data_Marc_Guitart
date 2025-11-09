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
        var: Number.isFinite(d?.var) ? d.var : undefined,
        prediction: Number.isFinite(d?.prediction) ? d.prediction : undefined,
        pred_conf: Number.isFinite(d?.pred_conf) ? d.pred_conf : undefined,
      }))
      .filter(d => d.x && (Number.isFinite(d.var) || Number.isFinite(d.prediction)));
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
          <XAxis
            dataKey="x"
            tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
            minTickGap={40}
            interval="preserveStartEnd"
          />
          <YAxis allowDataOverflow width={50} />
          <Tooltip
            labelFormatter={(v) => fmt(v)}
            formatter={(value, name) => [
              typeof value === "number" ? value : undefined,
              name === "var" ? "Real" : name === "prediction" ? "Pred" : name
            ]}
          />
          <Legend />
          {/* Observados (azul) 0..t */}
          <Line
            type="monotone"
            dataKey="var"
            name="Real"
            stroke="#00A3FF"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          {/* Predicciones (naranja, discontinua) 0+1..t+1 */}
          <Line
            type="monotone"
            dataKey="prediction"
            name="Pred"
            stroke="#FF7A00"
            strokeWidth={2}
            dot={false}
            connectNulls
            strokeDasharray="5 5"
          />
          {/* Puntos de predicción con opacidad por pred_conf */}
          <Line
            dataKey="prediction"
            name="Pred (pts)"
            stroke="none"
            isAnimationActive={false}
            dot={(props) => {
              const { cx, cy, payload } = props;
              const alpha = Math.max(0.15, Math.min(1, Number(payload?.pred_conf ?? 0.6)));
              return <circle cx={cx} cy={cy} r={3} fill="#FF7A00" fillOpacity={alpha} />;
            }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
