import React, { useMemo } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts";
import { MODEL_COLORS, MODEL_NAMES } from "../constants/models";

/**
 * Weight Evolution Chart: Muestra cómo evolucionan los pesos de los modelos a lo largo del tiempo
 * 
 * Props:
 * - data: array de puntos con {t, weight_linear, weight_poly, weight_alphabeta, weight_kalman, weight_base, weight_hyper}
 */
export default function WeightEvolutionChart({ data = [] }) {
  const processedData = useMemo(() => {
    return (Array.isArray(data) ? data : [])
      .map((d, idx) => {
        const x = d.x || (Number.isFinite(d?.t) ? new Date(d.t).toISOString().slice(0, 19) + "Z" : undefined);
        if (!x) return null;

        return {
          x,
          idx,
          weight_linear: Number.isFinite(d?.weight_linear) ? d.weight_linear : 0,
          weight_poly: Number.isFinite(d?.weight_poly) ? d.weight_poly : 0,
          weight_alphabeta: Number.isFinite(d?.weight_alphabeta) ? d.weight_alphabeta : 0,
          weight_kalman: Number.isFinite(d?.weight_kalman) ? d.weight_kalman : 0,
          weight_base: Number.isFinite(d?.weight_base) ? d.weight_base : 0,
          weight_hyper: Number.isFinite(d?.weight_hyper) ? d.weight_hyper : 0,
        };
      })
      .filter((d) => d && d.x);
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
      <div style={{ width: "100%", height: 400, color: "#ccc", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p>(no weight data available)</p>
      </div>
    );
  }

  // Calcular estadísticas de dominancia
  const dominanceStats = useMemo(() => {
    const models = ["linear", "poly", "alphabeta", "kalman", "base", "hyper"];
    const counts = {};
    models.forEach(m => counts[m] = 0);

    processedData.forEach(point => {
      let maxWeight = -Infinity;
      let dominant = null;
      
      models.forEach(model => {
        const weight = point[`weight_${model}`] || 0;
        if (weight > maxWeight) {
          maxWeight = weight;
          dominant = model;
        }
      });
      
      if (dominant) {
        counts[dominant]++;
      }
    });

    const total = processedData.length;
    return models.map(model => ({
      model,
      count: counts[model],
      percentage: total > 0 ? ((counts[model] / total) * 100).toFixed(1) : 0
    })).sort((a, b) => b.count - a.count);
  }, [processedData]);

  return (
    <div style={{ width: "100%", marginBottom: 20 }}>
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 18, marginBottom: 8 }}>Weight Evolution Over Time</h3>
        <p style={{ fontSize: 12, color: "#aaa", marginBottom: 12 }}>
          This stacked area chart shows how the ensemble weights adapt dynamically based on each model's performance.
          Higher weight indicates more influence in the final prediction.
        </p>
      </div>

      {/* Dominance Statistics */}
      <div style={{ 
        background: "#1a1a1a", 
        padding: 16, 
        borderRadius: 6, 
        border: "1px solid #333", 
        marginBottom: 16 
      }}>
        <h4 style={{ fontSize: 14, marginBottom: 12, color: "#FF7A00" }}>
          Model Dominance (periods where each model had highest weight)
        </h4>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
          {dominanceStats.map(({ model, count, percentage }) => (
            <div key={model} style={{ 
              background: "#2a2a2a", 
              padding: "10px 12px", 
              borderRadius: 4,
              borderLeft: `3px solid ${MODEL_COLORS[model]}` 
            }}>
              <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
                {MODEL_NAMES[model] || model}
              </div>
              <div style={{ fontSize: 18, fontWeight: "bold", color: MODEL_COLORS[model] }}>
                {percentage}%
              </div>
              <div style={{ fontSize: 10, opacity: 0.6 }}>
                {count} points
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stacked Area Chart */}
      <div style={{ width: "100%", height: 400, background: "#1a1a1a", borderRadius: 8, padding: "8px 0" }}>
        <ResponsiveContainer>
          <AreaChart data={processedData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <defs>
              <linearGradient id="colorLinear" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={MODEL_COLORS.linear} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={MODEL_COLORS.linear} stopOpacity={0.3}/>
              </linearGradient>
              <linearGradient id="colorPoly" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={MODEL_COLORS.poly} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={MODEL_COLORS.poly} stopOpacity={0.3}/>
              </linearGradient>
              <linearGradient id="colorAlphaBeta" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={MODEL_COLORS.alphabeta} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={MODEL_COLORS.alphabeta} stopOpacity={0.3}/>
              </linearGradient>
              <linearGradient id="colorKalman" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={MODEL_COLORS.kalman} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={MODEL_COLORS.kalman} stopOpacity={0.3}/>
              </linearGradient>
              <linearGradient id="colorBase" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={MODEL_COLORS.base} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={MODEL_COLORS.base} stopOpacity={0.3}/>
              </linearGradient>
              <linearGradient id="colorHyper" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={MODEL_COLORS.hyper} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={MODEL_COLORS.hyper} stopOpacity={0.3}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey="x"
              tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
              minTickGap={60}
              tick={{ fill: "#ffffff", fontSize: 10 }}
              stroke="#ffffff"
              interval="preserveStartEnd"
            />
            <YAxis 
              allowDataOverflow 
              width={50} 
              tick={{ fill: "#ffffff", fontSize: 10 }} 
              stroke="#ffffff"
              label={{ value: 'Weight', angle: -90, position: 'insideLeft', fill: '#ffffff' }}
            />
            <Tooltip
              labelFormatter={(v) => fmt(v)}
              formatter={(value, name) => {
                const modelName = name.replace('weight_', '');
                return [value.toFixed(3), MODEL_NAMES[modelName] || modelName];
              }}
              contentStyle={{ background: "#222", border: "1px solid #444", borderRadius: 4 }}
            />
            <Legend 
              formatter={(value) => {
                const modelName = value.replace('weight_', '');
                return MODEL_NAMES[modelName] || modelName;
              }}
            />

            {/* Stacked Areas */}
            <Area
              type="monotone"
              dataKey="weight_linear"
              stackId="1"
              stroke={MODEL_COLORS.linear}
              fill="url(#colorLinear)"
              name="weight_linear"
            />
            <Area
              type="monotone"
              dataKey="weight_poly"
              stackId="1"
              stroke={MODEL_COLORS.poly}
              fill="url(#colorPoly)"
              name="weight_poly"
            />
            <Area
              type="monotone"
              dataKey="weight_alphabeta"
              stackId="1"
              stroke={MODEL_COLORS.alphabeta}
              fill="url(#colorAlphaBeta)"
              name="weight_alphabeta"
            />
            <Area
              type="monotone"
              dataKey="weight_kalman"
              stackId="1"
              stroke={MODEL_COLORS.kalman}
              fill="url(#colorKalman)"
              name="weight_kalman"
            />
            <Area
              type="monotone"
              dataKey="weight_base"
              stackId="1"
              stroke={MODEL_COLORS.base}
              fill="url(#colorBase)"
              name="weight_base"
            />
            <Area
              type="monotone"
              dataKey="weight_hyper"
              stackId="1"
              stroke={MODEL_COLORS.hyper}
              fill="url(#colorHyper)"
              name="weight_hyper"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Interpretation Help */}
      <div style={{ 
        background: "#0a0a0a", 
        padding: 12, 
        borderRadius: 4, 
        border: "1px solid #333", 
        marginTop: 12,
        fontSize: 11,
        color: "#aaa"
      }}>
        <strong>💡 Interpretation:</strong> The system continuously adjusts weights based on recent performance. 
        When a model consistently predicts accurately, its weight increases (more influence). 
        Poor predictions decrease weights. The sum of all weights always equals 1.0 (100%).
      </div>
    </div>
  );
}
