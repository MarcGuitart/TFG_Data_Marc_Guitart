import React, { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
} from "recharts";

const MODEL_NAMES = {
  var: "Real Traffic",
  prediction: "Adaptive Model",
};

/**
 * AP1: Gráfica GLOBAL de toda la serie con Real + Adaptativo.
 * Muestra "visión general del rendimiento" en todo el periodo.
 * 
 * Props:
 * - data: array de puntos con {t, var, prediction}
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
      <h3>AP1: Vista global de la serie completa</h3>
      <p style={{ fontSize: 12, color: "#666" }}>
        Línea azul: valor real observado. Línea naranja: predicción del modelo adaptativo.
      </p>

      <div style={{ width: "100%", height: 350 }}>
        <ResponsiveContainer>
          <ComposedChart data={processedData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey="x"
              tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
              minTickGap={60}
              interval="preserveStartEnd"
            />
            <YAxis allowDataOverflow width={50} />
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
              stroke="#00A3FF"
              strokeWidth={2}
              dot={false}
              connectNulls
            />

            {/* Adaptive */}
            <Line
              type="monotone"
              dataKey="prediction"
              name="prediction"
              stroke="#FF7A00"
              strokeWidth={2.5}
              dot={false}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
