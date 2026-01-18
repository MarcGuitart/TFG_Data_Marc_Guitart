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
export default function AP1GlobalChart({ data = [], rawData = [], forecastHorizon = 1 }) {
  // Use rawData (original points from backend with horizon field) if available, otherwise fallback to data
  const sourceData = rawData.length > 0 ? rawData : data;
  
  const processedData = useMemo(() => {
    const input = Array.isArray(sourceData) ? sourceData : [];
    // Don't need to process further - rawData already has the correct structure
    
    // For T+1 chart: create standard mapping (for compatibility)
    // For T+M chart: will be handled separately below
    
    const timestampMap = new Map();
    
    input.forEach((d) => {
      const x = d.x || d.t_decision || d.timestamp || (Number.isFinite(d?.t) ? new Date(d.t).toISOString() : undefined);
      if (!x) return;
      
      if (!timestampMap.has(x)) {
        timestampMap.set(x, { x });
      }
      
      const point = timestampMap.get(x);
      
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
    
    return Array.from(timestampMap.values())
      .filter((d) => d && d.x && (Number.isFinite(d.var) || Number.isFinite(d.prediction)));
  }, [sourceData]);

  // Calculate T+M data using horizon field if available in sourceData
  const horizonData = useMemo(() => {
    if (forecastHorizon <= 1) {
      return [];
    }
    
    // If we have rawData with horizon field, use it directly
    if (rawData.length > 0 && rawData[0]?.horizon !== undefined) {
      // rawData points already have horizon field - use them directly
      const result = [];
      const errors = [];
      const confidences = [];
      
      // Create a map of predictions by index (shifted)
      // The prediction in rawData[i] is actually for rawData[i+1]
      const predictionsByIndex = new Map();
      rawData.forEach((point, idx) => {
        if (Number.isFinite(point.prediction)) {
          // Predict for next point
          predictionsByIndex.set(idx + 1, point.prediction);
        }
      });
      
      // Process points STARTING FROM INDEX 1 (because index 0 has no previous prediction)
      for (let idx = 1; idx < rawData.length; idx++) {
        const point = rawData[idx];
        const pointHorizon = point.horizon || 1;
        
        if (pointHorizon === forecastHorizon) {
          // Get prediction that was made FOR this point (from previous point)
          const predictionAtT = predictionsByIndex.get(idx);
          const actualAtTplusM = Number.isFinite(point.var) ? point.var : undefined;
          
          // Use the CURRENT point's timestamp (T+M, where observation happened)
          const timestampForDisplay = point.t_decision || point.timestamp || point.x;
          
          // For the prediction line, shift it back by M*30 minutes to align visually
          // So they both appear at the same timestamp on the chart
          const shiftMillis = forecastHorizon * 30 * 60 * 1000;
          const shiftedTimestampForPrediction = new Date(new Date(timestampForDisplay).getTime() - shiftMillis).toISOString();
          
          const dataPoint = {
            x: timestampForDisplay, // Observation stays at T+M
            xPredictionShifted: shiftedTimestampForPrediction, // Prediction shifted back to align
            varAtT: undefined,
            predictionAtT,
            actualAtTplusM,
          };
          
          if (Number.isFinite(predictionAtT) && Number.isFinite(actualAtTplusM)) {
            const error = Math.abs(predictionAtT - actualAtTplusM);
            const errorRel = (error / Math.abs(actualAtTplusM)) * 100;
            const confidence = Math.max(0, Math.min(100, 100 - errorRel));
            
            errors.push(error);
            confidences.push(confidence);
            dataPoint.errorRel = errorRel;
            dataPoint.confidence = confidence;
          }
          
          result.push(dataPoint);
        }
      }
      
      // Calculate stats
      let avgError = 0, stdDev = 0, avgConfidence = 0;
      if (errors.length > 0) {
        avgError = errors.reduce((a, b) => a + b, 0) / errors.length;
        const variance = errors.reduce((a, e) => a + Math.pow(e - avgError, 2), 0) / errors.length;
        stdDev = Math.sqrt(variance);
      }
      if (confidences.length > 0) {
        avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;
      }
      
      result._avgError = avgError;
      result._stdDev = stdDev;
      result._avgConfidence = avgConfidence;
      
      return result;
    }
    
    // Fallback to processedData method (for backward compatibility with data prop)
    if (processedData.length < forecastHorizon + 1) {
      return [];
    }
    
    const result = [];
    const errors = [];
    const confidences = [];
    
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
        xTplusM: pointTplusM.x,
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
  }, [rawData, processedData, forecastHorizon]);

  // combinedChartData: Create separate entries for predictions (shifted) and observations (not shifted)
  const combinedChartData = useMemo(() => {
    if (horizonData.length === 0) return [];
    
    // Create combined data with both observation timestamps and shifted prediction timestamps
    const combined = [];
    
    horizonData.forEach((point) => {
      // Add observation at its original timestamp
      combined.push({
        x: point.x,
        actualAtTplusM: point.actualAtTplusM,
        predictionAtT: undefined,
        errorRel: point.errorRel,
        confidence: point.confidence,
      });
      
      // Add prediction at the shifted timestamp
      if (Number.isFinite(point.predictionAtT)) {
        combined.push({
          x: point.xPredictionShifted,
          actualAtTplusM: undefined,
          predictionAtT: point.predictionAtT,
          errorRel: point.errorRel,
          confidence: point.confidence,
        });
      }
    });
    
    // Sort by x timestamp to maintain chronological order
    combined.sort((a, b) => {
      const timeA = new Date(a.x).getTime();
      const timeB = new Date(b.x).getTime();
      return timeA - timeB;
    });
    
    console.log("[AP1GlobalChart] combinedChartData length:", combined.length);
    if (combined.length > 1) {
      console.log("[AP1GlobalChart] combinedChartData[0]:", {x: combined[0].x, pred: combined[0].predictionAtT, actual: combined[0].actualAtTplusM});
      console.log("[AP1GlobalChart] combinedChartData[1]:", {x: combined[1].x, pred: combined[1].predictionAtT, actual: combined[1].actualAtTplusM});
    }
    
    return combined;
  }, [horizonData]);

  const fmt = (s) => {
    try {
      return new Date(s).toLocaleString();
    } catch {
      return String(s);
    }
  };

  // For T+1 chart: create a combined dataset where predictions are shifted back by one step (30 minutes)
  // OR by forecastHorizon steps if that's what was selected
  const processedDataForChart = useMemo(() => {
    if (processedData.length === 0) return [];
    
    const combined = [];
    const shiftMillis = forecastHorizon * 30 * 60 * 1000; // Shift by horizon steps
    
    processedData.forEach((point, idx) => {
      // Add observation at its original timestamp
      combined.push({
        x: point.x,
        var: point.var,
        prediction: undefined,
        linear: undefined,
        poly: undefined,
        kalman: undefined,
        alphabeta: undefined,
        naive: undefined,
      });
      
      // Add prediction at shifted timestamp
      if (Number.isFinite(point.prediction)) {
        const shiftedTimestamp = new Date(new Date(point.x).getTime() - shiftMillis).toISOString();
        combined.push({
          x: shiftedTimestamp,
          var: undefined,
          prediction: point.prediction,
          linear: point.linear,
          poly: point.poly,
          kalman: point.kalman,
          alphabeta: point.alphabeta,
          naive: point.naive,
        });
      }
    });
    
    // Sort by timestamp
    combined.sort((a, b) => {
      const timeA = new Date(a.x).getTime();
      const timeB = new Date(b.x).getTime();
      return timeA - timeB;
    });
    
    return combined;
  }, [processedData, forecastHorizon]);

  if (!processedData.length) {
    return (
      <div style={{ width: "100%", height: 350, color: "#ccc", display: "flex", alignItems: "center" }}>
        <p style={{ margin: "auto" }}>(no data to display)</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%" }}>
      {/* T+1 or T+M Chart (depends on forecastHorizon) */}
      <div style={{ marginBottom: forecastHorizon > 1 ? 40 : 0 }}>
        <h3>Global View of the Complete Series (T+{forecastHorizon})</h3>
        <p style={{ fontSize: 12, color: "#ffffffff" }}>
          Real traffic (blue) vs Adaptive ensemble prediction (orange) and individual model predictions (semi-transparent)
        </p>

        <div style={{ width: "100%", height: 350 }}>
          <ResponsiveContainer>
            <ComposedChart data={processedDataForChart} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
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
