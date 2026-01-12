import React, { useState, useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid,
  ReferenceArea,
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
  prediction: "Adaptive (selected)",
};

/**
 * AP1: Componente de visualización con dos gráficas:
 * 1. Vista GLOBAL (arriba) - toda la serie, permite seleccionar rango
 * 2. Vista ZOOM (abajo) - detalle del rango seleccionado
 */
export default function AP1Chart({ data = [] }) {
  // Rango de zoom (índices)
  const [zoomStart, setZoomStart] = useState(null);
  const [zoomEnd, setZoomEnd] = useState(null);
  const [selecting, setSelecting] = useState(false);
  const [tempEnd, setTempEnd] = useState(null);

  // Normalizar datos
  const norm = useMemo(() => {
    const toIso = (d) => {
      // Use t_decision for predictions (when they were made)
      if (d?.t_decision) return d.t_decision;
      if (typeof d?.x === "string") return d.x;
      if (Number.isFinite(d?.t)) return new Date(d.t).toISOString().slice(0, 19) + "Z";
      return undefined;
    };

    return (Array.isArray(data) ? data : [])
      .map((d, idx) => {
        const x = toIso(d);
        if (!x) return null;

        const base = {
          x,
          idx,
          var: Number.isFinite(d?.var) ? d.var : undefined,
          prediction: Number.isFinite(d?.prediction) ? d.prediction : undefined,
          chosen_model: d?.chosen_model || undefined,
          horizon: d?.horizon || 1,
        };

        // Copiar predicciones de modelos individuales
        for (const [k, v] of Object.entries(d)) {
          if (
            !["x", "t", "t_decision", "var", "prediction", "pred_conf", "chosen_model", "horizon"].includes(k) &&
            Number.isFinite(v)
          ) {
            base[k] = v;
          }
        }

        return base;
      })
      .filter((d) => d && d.x && (Number.isFinite(d.var) || Number.isFinite(d.prediction)));
  }, [data]);

  // Detectar qué modelos están presentes
  const modelKeys = useMemo(() => {
    const keySet = new Set();
    for (const row of norm) {
      Object.keys(row).forEach((k) => keySet.add(k));
    }
    return [...keySet].filter(
      (k) => !["x", "idx", "var", "prediction", "pred_conf", "chosen_model", "horizon", "t_decision"].includes(k)
    );
  }, [norm]);

  // Datos del zoom
  const zoomedData = useMemo(() => {
    if (zoomStart === null || zoomEnd === null) {
      // Default: mostrar un tramo inicial de 50 puntos
      return norm.slice(0, Math.min(50, norm.length));
    }
    const start = Math.min(zoomStart, zoomEnd);
    const end = Math.max(zoomStart, zoomEnd);
    return norm.slice(start, end + 1);
  }, [norm, zoomStart, zoomEnd]);

  // Detectar cambios de modelo en el zoom para destacar
  const modelChanges = useMemo(() => {
    const changes = [];
    for (let i = 1; i < zoomedData.length; i++) {
      const prev = zoomedData[i - 1]?.chosen_model;
      const curr = zoomedData[i]?.chosen_model;
      if (prev && curr && prev !== curr) {
        changes.push({
          idx: i,
          from: prev,
          to: curr,
          x: zoomedData[i].x,
        });
      }
    }
    return changes;
  }, [zoomedData]);

  const fmt = (s) => { try { return new Date(s).toLocaleString(); } catch { return String(s); } };

  if (!norm.length) {
    return (
      <div style={{ padding: 20, color: "#ccc" }}>
        (no hay puntos para mostrar)
      </div>
    );
  }

  // Handlers para selección de rango en la gráfica global
  const handleMouseDown = (e) => {
    if (e?.activeTooltipIndex !== undefined) {
      setZoomStart(e.activeTooltipIndex);
      setSelecting(true);
    }
  };

  const handleMouseMove = (e) => {
    if (selecting && e?.activeTooltipIndex !== undefined) {
      setTempEnd(e.activeTooltipIndex);
    }
  };

  const handleMouseUp = (e) => {
    if (selecting) {
      if (e?.activeTooltipIndex !== undefined) {
        setZoomEnd(e.activeTooltipIndex);
      } else if (tempEnd !== null) {
        setZoomEnd(tempEnd);
      }
      setSelecting(false);
      setTempEnd(null);
    }
  };

  const resetZoom = () => {
    setZoomStart(null);
    setZoomEnd(null);
  };

  return (
    <div style={{ color: "#f0f0f0" }}>
      {/* GLOBAL VIEW */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h4 style={{ margin: 0 }}>Vista Global ({norm.length} puntos)</h4>
          <span style={{ fontSize: 12, opacity: 0.7 }}>
            Arrastra para seleccionar rango de zoom
          </span>
        </div>
        <div style={{ width: "100%", height: 150, background: "#ffffffff", borderRadius: 8, padding: "8px 0" }}>
          <ResponsiveContainer>
            <ComposedChart
              data={norm}
              margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis
                dataKey="x"
                tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString().slice(0, 5) : "")}
                tick={{ fontSize: 10, fill: "#ffffff" }}
                stroke="#ffffff"
                interval="preserveStartEnd"
              />
              <YAxis hide />

              {/* Real Traffic - línea fina azul */}
              <Line
                type="monotone"
                dataKey="var"
                stroke="#00A3FF"
                strokeWidth={1}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />

              {/* Adaptive - línea naranja */}
              <Line
                type="monotone"
                dataKey="prediction"
                stroke="#FF7A00"
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />

              {/* Área de selección */}
              {selecting && zoomStart !== null && tempEnd !== null && (
                <ReferenceArea
                  x1={norm[Math.min(zoomStart, tempEnd)]?.x}
                  x2={norm[Math.max(zoomStart, tempEnd)]?.x}
                  strokeOpacity={0.3}
                  fill="#00A3FF"
                  fillOpacity={0.2}
                />
              )}

              {/* Área seleccionada (persistente) */}
              {!selecting && zoomStart !== null && zoomEnd !== null && (
                <ReferenceArea
                  x1={norm[Math.min(zoomStart, zoomEnd)]?.x}
                  x2={norm[Math.max(zoomStart, zoomEnd)]?.x}
                  strokeOpacity={0.5}
                  fill="#00A3FF"
                  fillOpacity={0.15}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ZOOM VIEW */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h4 style={{ margin: 0 }}>
            Vista Detallada 
            {zoomStart !== null && zoomEnd !== null && (
              <span style={{ fontWeight: 400, fontSize: 14, marginLeft: 8 }}>
                (puntos {Math.min(zoomStart, zoomEnd) + 1} - {Math.max(zoomStart, zoomEnd) + 1})
              </span>
            )}
          </h4>
          {(zoomStart !== null || zoomEnd !== null) && (
            <button
              onClick={resetZoom}
              style={{
                padding: "4px 12px",
                background: "#ffffffff",
                border: "1px solid #ffffffff",
                borderRadius: 4,
                color: "#fff",
                cursor: "pointer",
                fontSize: 12,
              }}
            >
              Reset Zoom
            </button>
          )}
        </div>

        {/* Info de cambios de modelo detectados */}
        {modelChanges.length > 0 && (
          <div style={{ 
            background: "#2a2a2a", 
            padding: "8px 12px", 
            borderRadius: 6, 
            marginBottom: 12,
            fontSize: 12 
          }}>
            <strong>🔄 Cambios de modelo detectados:</strong>
            {modelChanges.slice(0, 5).map((c, i) => (
              <span key={i} style={{ marginLeft: 12 }}>
                <span style={{ color: MODEL_COLORS[c.from] || "#ccc" }}>{c.from}</span>
                {" → "}
                <span style={{ color: MODEL_COLORS[c.to] || "#ccc" }}>{c.to}</span>
              </span>
            ))}
            {modelChanges.length > 5 && <span style={{ opacity: 0.6 }}> (+{modelChanges.length - 5} más)</span>}
          </div>
        )}

        <div style={{ width: "100%", height: 320, background: "#1a1a1a", borderRadius: 8, padding: "8px 0" }}>
          <ResponsiveContainer>
            <ComposedChart data={zoomedData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis
                dataKey="x"
                tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
                minTickGap={40}
                tick={{ fill: "#ffffff" }}
                stroke="#ffffff"
                interval="preserveStartEnd"
              />
              <YAxis allowDataOverflow width={50} tick={{ fill: "#ffffff" }} stroke="#ffffff" />
              <Tooltip
                labelFormatter={(v) => fmt(v)}
                formatter={(value, name, props) => {
                  if (typeof value !== "number") return [undefined, name];
                  const displayName = MODEL_NAMES[name] || `Model ${name}`;
                  // Mostrar modelo elegido si es la línea adaptativa
                  if (name === "prediction" && props?.payload?.chosen_model) {
                    return [value.toFixed(2), `${displayName} → ${props.payload.chosen_model}`];
                  }
                  return [value.toFixed(2), displayName];
                }}
                contentStyle={{ background: "#222", border: "1px solid #444" }}
              />
              <Legend 
                formatter={(value) => MODEL_NAMES[value] || `Model ${value}`}
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
                  opacity={0.8}
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
      </div>
    </div>
  );
}
