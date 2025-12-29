import React, { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
} from "recharts";
import { MODEL_COLORS, MODEL_NAMES, KNOWN_MODELS } from "../constants/models";

/**
 * AP1: Global chart of entire series with Real + Adaptive + All models.
 * Shows "overall performance view" across the entire period.
 * 
 * Props:
 * - data: array of points with {t, var, prediction, linear, poly, alphabeta, kalman, naive}
 */
export default function AP1GlobalChart({ data = [] }) {
  const processedData = useMemo(() => {
    return (Array.isArray(data) ? data : [])
      .map((d) => {
        const x = d.x || (Number.isFinite(d?.t) ? new Date(d.t).toISOString().slice(0, 19) + "Z" : undefined);
        if (!x) return null;

        const point = {
          x,
          var: Number.isFinite(d?.var) ? d.var : undefined,
          prediction: Number.isFinite(d?.prediction) ? d.prediction : undefined,
        };
        
        // Add all known models dynamically
        // Map "base" to "naive" if backend sends it
        KNOWN_MODELS.forEach(model => {
          const dataKey = model === "naive" && d?.base ? "base" : model;
          if (Number.isFinite(d?.[dataKey])) {
            point[model] = d[dataKey];
          }
        });
        
        return point;
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
        <p style={{ margin: "auto" }}>(no data to display)</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", marginBottom: 20 }}>
      <h3>Global View of the Complete Series</h3>
      <p style={{ fontSize: 12, color: "#ffffffff" }}>
        Real traffic (blue) vs Adaptive ensemble prediction (orange) and individual model predictions (semi-transparent)
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

            {/* Adaptive Model (main, thicker line) */}
            <Line
              type="monotone"
              dataKey="prediction"
              name="prediction"
              stroke={MODEL_COLORS.prediction}
              strokeWidth={2.5}
              dot={false}
              connectNulls
            />

            {/* Individual models (thin semi-transparent lines) */}
            {KNOWN_MODELS.map((modelName) => (
              <Line
                key={modelName}
                type="monotone"
                dataKey={modelName}
                name={modelName}
                stroke={MODEL_COLORS[modelName] || "#6b7280"}
                strokeWidth={1}
                strokeOpacity={0.6}
                dot={false}
                connectNulls
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
