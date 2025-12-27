import React, { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
} from "recharts";

const MODEL_NAMES = {
  var: "Real Traffic",
  prediction: "Adaptive Model",
  linear: "Linear Model",
  poly: "Polynomial Model",
  alphabeta: "Alpha-Beta Model",
  kalman: "Kalman Model",
};

const MODEL_COLORS = {
  var: "#00A3FF",
  prediction: "#FF7A00",
  linear: "#3b82f6",
  poly: "#10b981",
  alphabeta: "#f59e0b",
  kalman: "#6743bbff",
};

/**
 * AP1: Gráfica GLOBAL de toda la serie con Real + Adaptativo + Todos los modelos.
 * Muestra "visión general del rendimiento" en todo el periodo.
 * 
 * Props:
 * - data: array de puntos con {t, var, prediction, linear, poly, alphabeta, kalman}
 */
export default function AP1GlobalChart({ data = [] }) {
  const processedData = useMemo(() => {
    return (Array.isArray(data) ? data : [])
      .map((d) => {
        const x = d.x || (Number.isFinite(d?.t) ? new Date(d.t).toISOString().slice(0, 19) + "Z" : undefined);
        if (!x) return null;

        return {
          x,
          var: Number.isFinite(d?.var) ? d.var : undefined,
          prediction: Number.isFinite(d?.prediction) ? d.prediction : undefined,
          linear: Number.isFinite(d?.linear) ? d.linear : undefined,
          poly: Number.isFinite(d?.poly) ? d.poly : undefined,
          alphabeta: Number.isFinite(d?.alphabeta) ? d.alphabeta : undefined,
          kalman: Number.isFinite(d?.kalman) ? d.kalman : undefined,
        };
      })
      .filter((d) => d && d.x && (Number.isFinite(d.var) || Number.isFinite(d.prediction)));
  }, [data]);

  const fmt = (s) => {
    try {
      return new Date(s).toLocaleString();
    } catch {
      return String(s);
    }
  };

  if (!processedData.length) {
    return (
      <div style={{ width: "100%", height: 350, color: "#ccc", display: "flex", alignItems: "center" }}>
        <p style={{ margin: "auto" }}>(no hay datos para mostrar)</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", marginBottom: 20 }}>
      <h3>Global View of the Complete Series</h3>
      <p style={{ fontSize: 12, color: "#ffffffff" }}>
      </p>

      <div style={{ width: "100%", height: 350 }}>
        <ResponsiveContainer>
          <ComposedChart data={processedData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey="x"
              tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
              minTickGap={60}
              tick={{ fill: "#ffffff" }}
              stroke="#ffffff"
              interval="preserveStartEnd"
            />
            <YAxis allowDataOverflow width={50} tick={{ fill: "#ffffff" }} stroke="#ffffff" />
            <Tooltip
              labelFormatter={(v) => fmt(v)}
              formatter={(value) => {
                if (typeof value !== "number") return [undefined];
                return value.toFixed(2);
              }}
            />
            <Legend formatter={(value) => MODEL_NAMES[value] || value} />

            {/* Real Traffic */}
            <Line
              type="monotone"
              dataKey="var"
              name="var"
              stroke={MODEL_COLORS.var}
              strokeWidth={2}
              dot={false}
              connectNulls
            />

            {/* Adaptive Model (principal, más gruesa) */}
            <Line
              type="monotone"
              dataKey="prediction"
              name="prediction"
              stroke={MODEL_COLORS.prediction}
              strokeWidth={2.5}
              dot={false}
              connectNulls
            />

            {/* Modelos individuales (líneas finas semi-transparentes) */}
            <Line
              type="monotone"
              dataKey="linear"
              name="linear"
              stroke={MODEL_COLORS.linear}
              strokeWidth={1}
              strokeOpacity={0.6}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="poly"
              name="poly"
              stroke={MODEL_COLORS.poly}
              strokeWidth={1}
              strokeOpacity={0.6}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="alphabeta"
              name="alphabeta"
              stroke={MODEL_COLORS.alphabeta}
              strokeWidth={1}
              strokeOpacity={0.6}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="kalman"
              name="kalman"
              stroke={MODEL_COLORS.kalman}
              strokeWidth={1}
              strokeOpacity={0.6}
              dot={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
