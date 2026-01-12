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
    const rawData = Array.isArray(data) ? data : [];
    
    // First pass: create a map with unique timestamps
    const timestampMap = new Map();
    
    rawData.forEach((d) => {
      const x = d.x || (Number.isFinite(d?.t) ? new Date(d.t).toISOString().slice(0, 19) + "Z" : undefined);
      if (!x) return;
      
      if (!timestampMap.has(x)) {
        timestampMap.set(x, { x });
      }
      
      const point = timestampMap.get(x);
      
      // Merge var and prediction at the same timestamp
      if (Number.isFinite(d?.var)) {
        point.var = d.var;
      }
      if (Number.isFinite(d?.prediction)) {
        point.prediction = d.prediction;
      }
      
      // Add all known models dynamically
      KNOWN_MODELS.forEach(model => {
        const dataKey = model === "naive" && d?.base ? "base" : model;
        if (Number.isFinite(d?.[dataKey])) {
          point[model] = d[dataKey];
        }
      });
    });
    
    // Second pass: convert map to array and filter
    return Array.from(timestampMap.values())
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
    
    // Calculate the time offset in milliseconds: M * 30 minutes
    const timeOffsetMs = forecastHorizon * 30 * 60 * 1000;
    
    for (let i = 0; i < processedData.length - forecastHorizon; i++) {
      const pointT = processedData[i];
      const pointTplusM = processedData[i + forecastHorizon];
      
      const actualAtTplusM = Number.isFinite(pointTplusM.var) ? pointTplusM.var : undefined;
      const predictionAtT = Number.isFinite(pointT.prediction) ? pointT.prediction : undefined;
      
      const point = {
        x: pointTplusM.x,
        varAtT: Number.isFinite(pointT.var) ? pointT.var : undefined,
        predictionAtT,
        actualAtTplusM,
        // Also store the timestamp from T for reference
        xT: pointT.x,
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

  // Create a combined dataset for chart: predictions are placed M steps earlier in the timeline
  const combinedChartData = useMemo(() => {
    if (horizonData.length === 0) return [];
    
    // Create array with the same length as horizonData
    const combined = horizonData.map(point => ({
      x: point.x,
      actualAtTplusM: point.actualAtTplusM,
      predictionAtT: undefined, // Will be filled by looking back M steps
      confidence: point.confidence,
      errorRel: point.errorRel,
    }));
    
    // Shift predictions further BACK: prediction made at point[i] appears at position [i - M*2]
    // This makes them more visually separated
    horizonData.forEach((point, i) => {
      const targetIndex = i - (forecastHorizon * 2);
      if (targetIndex >= 0) {
        combined[targetIndex].predictionAtT = point.predictionAtT;
      }
    });
    
    return combined;
  }, [horizonData, forecastHorizon]);

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
              <YAxis allowDataOverflow={false} width={50} tick={{ fill: "#ffffff" }} stroke="#ffffff" domain={[-0.5, 0.5]} />
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
                connectNulls={true}
              />

              {/* Adaptive Model (main, thicker line) */}
              <Line
                type="monotone"
                dataKey="prediction"
                name="prediction"
                stroke={MODEL_COLORS.prediction}
                strokeWidth={2.5}
                dot={false}
                connectNulls={true}
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
          <p style={{ fontSize: 12, color: "#ffffffff" }}>
            Shows all model predictions made at time T (for T+{forecastHorizon}) vs actual value at T+{forecastHorizon} (blue).
            This represents {forecastHorizon} steps ahead forecasting ({(forecastHorizon * 30) % 1440 === 0 ? Math.floor(forecastHorizon * 30 / 60) : forecastHorizon * 30} minutes).
            Shaded area shows average confidence bounds (±1 std dev, error={horizonData._avgError?.toFixed(2)}).
          </p>

          <div style={{ width: "100%", height: 350 }}>
            <ResponsiveContainer>
              <ComposedChart data={combinedChartData} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis
                  dataKey="x"
                  tickFormatter={(v) => (v ? new Date(v).toLocaleTimeString() : "")}
                  minTickGap={60}
                  tick={{ fill: "#ffffff" }}
                  stroke="#ffffff"
                  interval="preserveStartEnd"
                />
                <YAxis allowDataOverflow={false} width={50} tick={{ fill: "#ffffff" }} stroke="#ffffff" domain={[-0.5, 0.5]} />
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

                {/* Adaptive Prediction (shifted back M steps) */}
                <Line
                  type="monotone"
                  dataKey="predictionAtT"
                  name={`Prediction at T (shifted back ${forecastHorizon} steps)`}
                  stroke={MODEL_COLORS.prediction}
                  strokeWidth={2.5}
                  strokeDasharray="5 5"
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                />
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
