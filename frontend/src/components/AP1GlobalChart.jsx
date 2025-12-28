import React, { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
} from "recharts";
import { MODEL_COLORS, MODEL_NAMES, KNOWN_MODELS } from "../constants/models";

/**
 * AP1: Gráfica GLOBAL de toda la serie con Real + Adaptativo + Todos los modelos.
 * Muestra "visión general del rendimiento" en todo el periodo.
 * 
 * Props:
 * - data: array de puntos con {t, var, prediction, linear, poly, alphabeta, kalman, base}
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
        
        // Añadir todos los modelos conocidos dinámicamente
        KNOWN_MODELS.forEach(model => {
          if (Number.isFinite(d?.[model])) {
            point[model] = d[model];
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
