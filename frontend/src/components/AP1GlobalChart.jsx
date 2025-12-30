import React, { useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, XAxis, YAxis, Tooltip, Legend, Line, CartesianGrid, Area,
} from "recharts";
import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import { MODEL_COLORS, MODEL_NAMES, KNOWN_MODELS } from "../constants/models";

/**
 * AP1: Global chart of entire series with Real + Adaptive + All models.
 * Shows "overall performance view" across the entire period.
 * 
 * Props:
 * - data: array of points with {t, var, prediction, linear, poly, alphabeta, kalman, naive}
 * - forecastHorizon: number (T+M) representing steps ahead to forecast
 */
export default function AP1GlobalChart({ data = [], forecastHorizon = 1 }) {
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

  // Calculate T+M data: for each point, use its prediction as "T" and look ahead M steps for actual value
  // Include all models and calculate confidence bounds
  const horizonData = useMemo(() => {
    if (forecastHorizon <= 1 || processedData.length < forecastHorizon + 1) {
      return [];
    }
    
    const result = [];
    const errors = []; // Collect all errors for confidence calculation
    const confidences = []; // Collect all confidences
    
    for (let i = 0; i < processedData.length - forecastHorizon; i++) {
      const pointT = processedData[i];
      const pointTplusM = processedData[i + forecastHorizon];
      
      const actualAtTplusM = Number.isFinite(pointTplusM.var) ? pointTplusM.var : undefined;
      const predictionAtT = Number.isFinite(pointT.prediction) ? pointT.prediction : undefined;
      
      const point = {
        x: pointT.x,
        varAtT: Number.isFinite(pointT.var) ? pointT.var : undefined,
        predictionAtT,
        actualAtTplusM,
      };
      
      // Add all individual models at T
      KNOWN_MODELS.forEach(model => {
        const dataKey = model === "naive" && pointT?.base ? "base" : model;
        if (Number.isFinite(pointT?.[dataKey])) {
          point[`${model}_T`] = pointT[dataKey];
        }
      });
      
      // Calculate error and confidence for this point if we have both prediction and actual
      if (Number.isFinite(predictionAtT) && Number.isFinite(actualAtTplusM)) {
        const error = Math.abs(predictionAtT - actualAtTplusM);
        const errorRel = (error / Math.abs(actualAtTplusM)) * 100; // percentage
        const confidence = Math.max(0, Math.min(100, 100 - errorRel));
        
        errors.push(error);
        confidences.push(confidence);
        point.errorRel = errorRel;
        point.confidence = confidence;
      }
      
      result.push(point);
    }
    
    // Calculate average error and confidence bounds (±1 std dev)
    let avgError = 0;
    let stdDev = 0;
    let avgConfidence = 0;
    
    if (errors.length > 0) {
      avgError = errors.reduce((a, b) => a + b, 0) / errors.length;
      const variance = errors.reduce((a, e) => a + Math.pow(e - avgError, 2), 0) / errors.length;
      stdDev = Math.sqrt(variance);
    }
    
    if (confidences.length > 0) {
      avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
    }
    
    // Add bounds to each point
    result.forEach(point => {
      point.confidenceUpper = (point.predictionAtT ?? point.actualAtTplusM) + stdDev;
      point.confidenceLower = (point.predictionAtT ?? point.actualAtTplusM) - stdDev;
    });
    
    // Store stats for later display
    result._avgError = avgError;
    result._stdDev = stdDev;
    result._avgConfidence = avgConfidence;
    
    return result;
  }, [processedData, forecastHorizon]);

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
    <div style={{ width: "100%" }}>
      {/* T+1 Chart (Standard) */}
      <div style={{ marginBottom: forecastHorizon > 1 ? 40 : 0 }}>
        <h3>Global View of the Complete Series (T+1 Standard)</h3>
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

      {/* T+M Chart (when forecastHorizon > 1) */}
      {forecastHorizon > 1 && horizonData.length > 0 && (
        <div>
          <h3 style={{ marginTop: 40 }}>Prediction Horizon T+{forecastHorizon}</h3>
          <p style={{ fontSize: 12, color: "#aaa" }}>
            Shows all model predictions made at time T (for T+{forecastHorizon}) vs actual value at T+{forecastHorizon} (blue).
            This represents {forecastHorizon} steps ahead forecasting ({(forecastHorizon * 30) % 1440 === 0 ? Math.floor(forecastHorizon * 30 / 60) : forecastHorizon * 30} minutes).
            Shaded area shows average confidence bounds (±1 std dev, error={horizonData._avgError?.toFixed(2)}).
          </p>

          <div style={{ width: "100%", height: 350 }}>
            <ResponsiveContainer>
              <ComposedChart data={horizonData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
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
                <Legend />

                {/* Actual value at T+M */}
                <Line
                  type="monotone"
                  dataKey="actualAtTplusM"
                  name={`Actual at T+${forecastHorizon}`}
                  stroke={MODEL_COLORS.var}
                  strokeWidth={2.5}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />

                {/* Adaptive Prediction made at T */}
                <Line
                  type="monotone"
                  dataKey="predictionAtT"
                  name={`Adaptive Prediction at T`}
                  stroke={MODEL_COLORS.prediction}
                  strokeWidth={2.5}
                  strokeDasharray="5 5"
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />

                {/* Individual models at T (thin semi-transparent lines) */}
                {KNOWN_MODELS.map((modelName) => (
                  <Line
                    key={`${modelName}_T`}
                    type="monotone"
                    dataKey={`${modelName}_T`}
                    name={`${modelName} at T`}
                    stroke={MODEL_COLORS[modelName] || "#6b7280"}
                    strokeWidth={1}
                    strokeOpacity={0.5}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Confidence Score Card for T+M */}
          <div style={{ marginTop: 24 }}>
            <div style={{ 
              background: "linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)", 
              padding: 20, 
              borderRadius: 6, 
              border: `2px solid ${horizonData._avgConfidence >= 85 ? "#10b981" : horizonData._avgConfidence >= 75 ? "#f59e0b" : "#ef4444"}`,
              maxWidth: 500
            }}>
              <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
                Prediction Confidence at T+{forecastHorizon}
                <span style={{ marginLeft: 8, fontSize: 9, opacity: 0.6 }}>
                  (1 - Mean Relative Error)
                </span>
              </div>
              <div style={{ 
                fontSize: 32, 
                fontWeight: "bold", 
                color: horizonData._avgConfidence >= 85 ? "#10b981" : horizonData._avgConfidence >= 75 ? "#f59e0b" : "#ef4444",
                fontFamily: "monospace"
              }}>
                {horizonData._avgConfidence.toFixed(2)}%
              </div>
              <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4, display: 'flex', alignItems: 'center', gap: '6px' }}>
                {horizonData._avgConfidence >= 85 ? (
                  <><CheckCircle size={14} style={{ color: '#10b981' }} /> Excellent accuracy</>
                ) : horizonData._avgConfidence >= 75 ? (
                  <><AlertTriangle size={14} style={{ color: '#f59e0b' }} /> Acceptable accuracy</>
                ) : (
                  <><XCircle size={14} style={{ color: '#ef4444' }} /> Low accuracy</>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
