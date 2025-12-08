import React, { useMemo, useState, useCallback } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid, ReferenceDot,
} from "recharts";

const MODEL_COLORS = {
  linear: "#10B981",
  poly: "#8B5CF6",
  alphabeta: "#EC4899",
  kalman: "#6366F1",
};

const MODEL_NAMES = {
  linear: "Model Linear",
  poly: "Model Poly",
  alphabeta: "Model AlphaBeta",
  kalman: "Model Kalman",
  var: "Real Traffic",
  prediction: "Adaptive Model",
};

/**
 * AP1: Gráfica con zoom en una ventana de ~30-40 puntos para ver cómo 
 * el modelo adaptativo salta entre modelos base.
 * 
 * Props:
 * - data: array de puntos con {t, var, prediction, chosen_model, linear, poly, ...}
 * - startIdx: índice inicial del zoom (default 0)
 * - windowSize: número de puntos a mostrar (default 40)
 * - onZoomChange: callback cuando el usuario cambia la ventana
 */
export default function AP1PerModelChart({ data = [], startIdx = 0, windowSize = 40, onZoomChange }) {
  const [localStartIdx, setLocalStartIdx] = useState(startIdx);
  
  const processedData = useMemo(() => {
    const rows = (Array.isArray(data) ? data : [])
      .map((d) => {
        const x = d.x || (Number.isFinite(d?.t) ? new Date(d.t).toISOString().slice(0, 19) + "Z" : undefined);
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

    // Aplicar zoom: ventana móvil
    const endIdx = Math.min(localStartIdx + windowSize, rows.length);
    return rows.slice(localStartIdx, endIdx);
  }, [data, localStartIdx, windowSize]);

  const fmt = (s) => {
    try {
      return new Date(s).toLocaleString();
    } catch {
      return String(s);
    }
  };

  if (!processedData.length) {
    return (
      <div style={{ width: "100%", height: 400, color: "#ccc", display: "flex", alignItems: "center" }}>
        <p style={{ margin: "auto" }}>(no hay puntos para mostrar)</p>
      </div>
    );
  }

  // Detectar qué modelos están presentes
  const keySet = new Set();
  for (const row of processedData) {
    Object.keys(row).forEach((k) => keySet.add(k));
  }
  const modelKeys = [...keySet].filter(
    (k) => !["x", "var", "prediction", "chosen_model"].includes(k)
  );

  const handleZoomNext = () => {
    const newIdx = Math.min(localStartIdx + 10, Math.max(0, data.length - windowSize));
    setLocalStartIdx(newIdx);
    if (onZoomChange) onZoomChange(newIdx);
  };

  const handleZoomPrev = () => {
    const newIdx = Math.max(0, localStartIdx - 10);
    setLocalStartIdx(newIdx);
    if (onZoomChange) onZoomChange(newIdx);
  };

  const handleSliderChange = (e) => {
    const newIdx = Math.max(0, Math.min(parseInt(e.target.value), data.length - windowSize));
    setLocalStartIdx(newIdx);
    if (onZoomChange) onZoomChange(newIdx);
  };

  const maxSlider = Math.max(0, data.length - windowSize);
  const sliderValue = Math.min(localStartIdx, maxSlider);

  return (
    <div style={{ width: "100%", marginBottom: 20 }}>
      <h3>AP1: Zoom de modelos adaptativos (~{windowSize} puntos)</h3>
      <p style={{ fontSize: 12, color: "#666" }}>
        Observa cómo el modelo adaptativo (naranja gruesa) salta entre modelos base (colores claros)
      </p>

      <div style={{ marginBottom: 15, display: "flex", gap: 10, alignItems: "center" }}>
        <button onClick={handleZoomPrev} style={{ padding: "5px 10px" }}>← Anterior</button>
        <input
          type="range"
          min="0"
          max={maxSlider}
          value={sliderValue}
          onChange={handleSliderChange}
          style={{ flex: 1 }}
        />
        <button onClick={handleZoomNext} style={{ padding: "5px 10px" }}>Siguiente →</button>
        <span style={{ fontSize: 12, color: "#666" }}>
          Puntos {localStartIdx + 1}–{Math.min(localStartIdx + windowSize, data.length)} de {data.length}
        </span>
      </div>

      <div style={{ width: "100%", height: 380 }}>
        <ResponsiveContainer>
          <ComposedChart data={processedData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
            <XAxis
              dataKey="x"
              tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
              minTickGap={20}
              interval="preserveStartEnd"
            />
            <YAxis allowDataOverflow width={50} />
            <Tooltip
              labelFormatter={(v) => fmt(v)}
              formatter={(value, name) => {
                if (typeof value !== "number") return [undefined, name];
                return [value.toFixed(2), MODEL_NAMES[name] || name];
              }}
            />
            <Legend formatter={(value) => MODEL_NAMES[value] || value} />

            {/* Modelos base */}
            {modelKeys.map((key, idx) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                name={key}
                strokeWidth={1.5}
                dot={false}
                connectNulls
                stroke={MODEL_COLORS[key]}
                opacity={0.6}
              />
            ))}

            {/* Real Traffic */}
            <Line
              type="monotone"
              dataKey="var"
              name="var"
              stroke="#00A3FF"
              strokeWidth={2.5}
              dot={false}
              connectNulls
            />

            {/* Adaptive */}
            <Line
              type="monotone"
              dataKey="prediction"
              name="prediction"
              stroke="#FF7A00"
              strokeWidth={3.5}
              dot={false}
              connectNulls
            />

            {/* Mostrar dónde cambia el modelo elegido */}
            {processedData.map((row, idx) => {
              if (idx === 0 || row.chosen_model === processedData[idx - 1]?.chosen_model) {
                return null;
              }
              return (
                <ReferenceDot
                  key={`switch-${idx}`}
                  x={row.x}
                  y={row.prediction}
                  r={4}
                  fill="#FF0000"
                  opacity={0.5}
                  label={{ value: "Switch", position: "top", fill: "#FF0000", fontSize: 10 }}
                />
              );
            })}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
