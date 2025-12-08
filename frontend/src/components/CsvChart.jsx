import React, { useMemo, useState } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
} from "recharts";

// AP1: Colores claros y distintivos para cada modelo
const MODEL_COLORS = {
  linear: "#10B981",      // verde esmeralda
  poly: "#8B5CF6",        // violeta
  alphabeta: "#EC4899",   // rosa
  kalman: "#6366F1",      // índigo
};
const DEFAULT_MODEL_COLORS = ["#10B981", "#6366F1", "#EC4899", "#F59E0B", "#8B5CF6"];

// AP1: Nombres legibles para leyenda
const MODEL_NAMES = {
  linear: "Model Linear",
  poly: "Model Poly",
  alphabeta: "Model AlphaBeta",
  kalman: "Model Kalman",
  var: "Real Traffic",
  prediction: "Adaptive Model (Selected)",
};

export default function CsvChart({ data = [], zoomRange = null }) {
  const norm = useMemo(() => {
    const toIso = (d) => {
      if (typeof d?.x === "string") return d.x;
      if (Number.isFinite(d?.t)) return new Date(d.t).toISOString().slice(0, 19) + "Z";
      return undefined;
    };

    let rows = (Array.isArray(data) ? data : [])
      .map((d) => {
        const x = toIso(d);
        if (!x) return null;

        const base = {
          x,
          var: Number.isFinite(d?.var) ? d.var : undefined,
          prediction: Number.isFinite(d?.prediction) ? d.prediction : undefined,
          chosen_model: d?.chosen_model || undefined,
        };

        // Copiar predicciones de modelos individuales
        for (const [k, v] of Object.entries(d)) {
          if (
            !["x", "t", "var", "prediction", "pred_conf", "chosen_model"].includes(k) &&
            Number.isFinite(v)
          ) {
            base[k] = v;
          }
        }

        return base;
      })
      .filter((d) => d && d.x && (Number.isFinite(d.var) || Number.isFinite(d.prediction)));

    // AP1: Aplicar zoom si está definido
    if (zoomRange && zoomRange.start !== undefined && zoomRange.end !== undefined) {
      rows = rows.slice(zoomRange.start, zoomRange.end);
    }

    return rows;
  }, [data, zoomRange]);

  const fmt = (s) => { try { return new Date(s).toLocaleString(); } catch { return String(s); } };

  if (!norm.length) {
    return (
      <div style={{ width: "100%", height: 320, color: "#ccc" }}>
        (no hay puntos para mostrar)
      </div>
    );
  }

  // Detectar qué modelos están presentes
  const keySet = new Set();
  for (const row of norm) {
    Object.keys(row).forEach((k) => keySet.add(k));
  }
  const modelKeys = [...keySet].filter(
    (k) => !["x", "var", "prediction", "pred_conf", "chosen_model"].includes(k)
  );

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
            formatter={(value, name, props) => {
              if (typeof value !== "number") return [undefined, name];
              const displayName = MODEL_NAMES[name] || name;
              // Mostrar modelo elegido si es la línea adaptativa
              if (name === "prediction" && props?.payload?.chosen_model) {
                return [value.toFixed(2), `${displayName} → ${props.payload.chosen_model}`];
              }
              return [value.toFixed(2), displayName];
            }}
          />
          <Legend 
            formatter={(value) => MODEL_NAMES[value] || value}
          />

          {/* AP1: Modelos base primero (líneas finas, detrás) */}
          {modelKeys.map((key, idx) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={key}
              strokeWidth={1.5}
              dot={false}
              connectNulls
              stroke={MODEL_COLORS[key] || DEFAULT_MODEL_COLORS[idx % 5]}
              opacity={0.7}
            />
          ))}

          {/* AP1: Real Traffic (azul, visible) */}
          <Line
            type="monotone"
            dataKey="var"
            name="var"
            stroke="#00A3FF"
            strokeWidth={2.5}
            dot={false}
            connectNulls
          />

          {/* AP1: Adaptive (naranja, encima, destaca) */}
          <Line
            type="monotone"
            dataKey="prediction"
            name="prediction"
            stroke="#FF7A00"
            strokeWidth={3}
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
