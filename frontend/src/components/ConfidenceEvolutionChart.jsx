import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from "recharts";
import { TrendingUp, TrendingDown, Info } from 'lucide-react';

/**
 * ConfidenceEvolutionChart
 * 
 * Shows how the prediction confidence/accuracy evolves over time as more data arrives.
 * Displays:
 * - Overall Accuracy Score (100% - MAPE) evolution
 * - Cumulative accuracy (rolling average)
 * - Confidence bands (excellent ≥85%, acceptable 75-85%, low <75%)
 * - Trend to see if the system is improving or degrading
 * 
 * Props:
 * - data: points with error_rel_mean (for T+1 standard)
 * - forecastHorizon: T+M value
 * - horizonData: points for T+M calculation (optional, from AP1GlobalChart)
 */
const ConfidenceEvolutionChart = ({ data, forecastHorizon = 1, horizonData = [] }) => {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Filter data by forecastHorizon if horizon field exists
    const filteredData = data.filter(point => {
      // If horizon field doesn't exist, include all points (backward compatibility)
      if (point.horizon === undefined) return true;
      // Otherwise, only include points matching the selected horizon
      return point.horizon === forecastHorizon;
    });

    // Calculate cumulative accuracy for each point of the selected horizon
    // NOTE: error_rel_mean comes from backend as PERCENTAGE (0-100), not as ratio (0-1)
    const processed = [];
    let cumulativeErrorSum = 0;
    let validCount = 0;

    filteredData.forEach((point, idx) => {
      // error_rel_mean is already MAPE in percentage (0-100%)
      const mapePercentage = point.error_rel_mean;
      
      // Calculate point accuracy (100% - MAPE%), clamped to [0, 100]
      const pointAccuracy = mapePercentage != null 
        ? Math.max(0, Math.min(100, 100 - mapePercentage))
        : null;

      // Update cumulative accuracy
      if (pointAccuracy != null && mapePercentage != null) {
        cumulativeErrorSum += mapePercentage;
        validCount += 1;
        // Cumulative MAPE is average of all MAPE values
        const cumulativeMAPE = cumulativeErrorSum / validCount;
        // Cumulative accuracy clamped to [0, 100]
        const cumulativeAccuracy = Math.max(0, Math.min(100, 100 - cumulativeMAPE));

        processed.push({
          index: idx + 1,
          t: point.t,
          pointAccuracy: parseFloat(pointAccuracy.toFixed(2)),
          cumulativeAccuracy: parseFloat(cumulativeAccuracy.toFixed(2)),
        });
      }
    });

    // Apply smoothing to cumulative accuracy using a 5-point moving average
    // This reduces visual abruptness when single points have very low accuracy
    const smoothingWindow = Math.min(5, Math.ceil(processed.length / 10));
    if (processed.length > 1 && smoothingWindow > 1) {
      for (let i = 0; i < processed.length; i++) {
        const start = Math.max(0, i - Math.floor(smoothingWindow / 2));
        const end = Math.min(processed.length, i + Math.floor(smoothingWindow / 2) + 1);
        const window = processed.slice(start, end);
        const smoothedAccuracy = window.reduce((sum, p) => sum + p.cumulativeAccuracy, 0) / window.length;
        processed[i].cumulativeAccuracySmoothed = parseFloat(smoothedAccuracy.toFixed(2));
        
        // Also calculate moving average of point accuracy (rolling window)
        const movingAvgAccuracy = window.reduce((sum, p) => sum + p.pointAccuracy, 0) / window.length;
        processed[i].movingAverageAccuracy = parseFloat(movingAvgAccuracy.toFixed(2));
        
        // Calculate average confidence (mean of all accuracies from start to current point)
        const allPointsUpToNow = processed.slice(0, i + 1);
        const avgConfidence = allPointsUpToNow.reduce((sum, p) => sum + p.pointAccuracy, 0) / allPointsUpToNow.length;
        processed[i].averageConfidence = parseFloat(avgConfidence.toFixed(2));
      }
    } else {
      // If not enough data points for smoothing, use original values
      processed.forEach((p, i) => {
        p.cumulativeAccuracySmoothed = p.cumulativeAccuracy;
        p.movingAverageAccuracy = p.pointAccuracy;
        // Average confidence up to this point
        const allPointsUpToNow = processed.slice(0, i + 1);
        const avgConfidence = allPointsUpToNow.reduce((sum, pt) => sum + pt.pointAccuracy, 0) / allPointsUpToNow.length;
        p.averageConfidence = parseFloat(avgConfidence.toFixed(2));
      });
    }

    return processed;
  }, [data, forecastHorizon]);

  // Calculate T+M confidence evolution data
  // horizonData already contains correct T vs T+M comparison from AP1GlobalChart
  const horizonProcessedData = useMemo(() => {
    if (forecastHorizon <= 1 || !horizonData || horizonData.length === 0) return [];

    const processed = [];

    // horizonData has predictions at T compared with actual values at T+M
    horizonData.forEach((point, idx) => {
      const actualValue = point.actualAtTplusM || point.varAtT;
      const predictionValue = point.predictionAtT;
      
      if (Number.isFinite(actualValue) && Number.isFinite(predictionValue)) {
        const errorAbs = Math.abs(predictionValue - actualValue);
        const errorRel = (errorAbs / Math.abs(actualValue)) * 100;
        const pointAccuracy = Math.max(0, Math.min(100, 100 - errorRel));

        processed.push({
          index: idx + 1,
          pointAccuracy: parseFloat(pointAccuracy.toFixed(2)),
        });
      }
    });

    // Apply smoothing (moving average) to pointAccuracy
    const smoothingWindow = Math.min(5, Math.ceil(processed.length / 10));
    if (processed.length > 1 && smoothingWindow > 1) {
      for (let i = 0; i < processed.length; i++) {
        const start = Math.max(0, i - Math.floor(smoothingWindow / 2));
        const end = Math.min(processed.length, i + Math.floor(smoothingWindow / 2) + 1);
        const window = processed.slice(start, end);
        const smoothedAccuracy = window.reduce((sum, p) => sum + p.pointAccuracy, 0) / window.length;
        processed[i].movingAverageAccuracy = parseFloat(smoothedAccuracy.toFixed(2));
      }
    } else {
      processed.forEach(p => p.movingAverageAccuracy = p.pointAccuracy);
    }

    return processed;
  }, [forecastHorizon, horizonData]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (processedData.length === 0) return null;

    // Calculate average accuracy as mean of average confidences
    const avgConfidences = processedData.map(p => p.averageConfidence);
    const avgAccuracyDirect = avgConfidences.reduce((sum, acc) => sum + acc, 0) / avgConfidences.length;

    const firstHalf = processedData.slice(0, Math.floor(processedData.length / 2));
    const secondHalf = processedData.slice(Math.floor(processedData.length / 2));

    const avgFirst = firstHalf.reduce((sum, p) => sum + p.averageConfidence, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((sum, p) => sum + p.averageConfidence, 0) / secondHalf.length;
    const trend = avgSecond - avgFirst;

    const final = processedData[processedData.length - 1];
    const initial = processedData[0];

    return {
      initial: initial.averageConfidence,
      final: final.averageConfidence,
      trend: trend,
      improvement: final.averageConfidence - initial.averageConfidence,
      avgAccuracy: avgAccuracyDirect, // Use direct average of average confidences
    };
  }, [processedData]);

  // Calculate statistics for T+M
  const horizonStats = useMemo(() => {
    if (horizonProcessedData.length === 0) return null;

    // Calculate average accuracy as mean of individual point accuracies
    // This matches how AP1GlobalChart calculates avgConfidence
    const pointAccuracies = horizonProcessedData.map(p => p.pointAccuracy);
    const avgAccuracyDirect = pointAccuracies.reduce((sum, acc) => sum + acc, 0) / pointAccuracies.length;

    const firstHalf = horizonProcessedData.slice(0, Math.floor(horizonProcessedData.length / 2));
    const secondHalf = horizonProcessedData.slice(Math.floor(horizonProcessedData.length / 2));

    const avgFirst = firstHalf.reduce((sum, p) => sum + p.pointAccuracy, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((sum, p) => sum + p.pointAccuracy, 0) / secondHalf.length;
    const trend = avgSecond - avgFirst;

    const final = horizonProcessedData[horizonProcessedData.length - 1];
    const initial = horizonProcessedData[0];

    return {
      initial: initial.pointAccuracy,
      final: final.pointAccuracy,
      trend: trend,
      improvement: final.pointAccuracy - initial.pointAccuracy,
      avgAccuracy: avgAccuracyDirect, // Use direct average of point accuracies
    };
  }, [horizonProcessedData]);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            background: "rgba(0, 0, 0, 0.95)",
            border: "1px solid #555",
            borderRadius: 6,
            padding: 12,
            fontSize: 12,
          }}
        >
          <div style={{ marginBottom: 8, fontWeight: "bold", color: "#FF7A00" }}>
            Point #{data.index} 
          </div>
          <div style={{ color: "#60a5fa", marginBottom: 4 }}>
            <strong>Point Accuracy:</strong> {data.pointAccuracy}%
          </div>
          <div style={{ color: "#10b981", marginBottom: 4 }}>
            <strong>Average Confidence:</strong> {data.averageConfidence}%
          </div>
        </div>
      );
    }
    return null;
  };

  if (processedData.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#888" }}>
        No data available to show confidence evolution
      </div>
    );
  }

  return (
    <div style={{ width: "100%", padding: "16px 0" }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 18, marginBottom: 8, color: "#fff", display: 'flex', alignItems: 'center', gap: '8px' }}>
          <TrendingUp size={22} />
          Confidence Evolution Over Time (T+{forecastHorizon})
        </h3>
        <p style={{ fontSize: 13, color: "#ffffffff", marginBottom: 16 }}>
          Shows how the system's prediction accuracy evolves as more data arrives for T+{forecastHorizon} horizon. 
        </p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 12,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              background: "#1a1a1a",
              padding: 16,
              borderRadius: 6,
              border: "1px solid #333",
            }}
          >
            <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
              Initial Accuracy
            </div>
            <div
              style={{
                fontSize: 24,
                fontWeight: "bold",
                color: stats.initial >= 85 ? "#10b981" : stats.initial >= 75 ? "#f59e0b" : "#ef4444",
              }}
            >
              {stats.initial.toFixed(2)}%
            </div>
          </div>

          <div
            style={{
              background: "#1a1a1a",
              padding: 16,
              borderRadius: 6,
              border: "1px solid #333",
            }}
          >
            <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
              Final Accuracy
            </div>
            <div
              style={{
                fontSize: 24,
                fontWeight: "bold",
                color: stats.final >= 85 ? "#10b981" : stats.final >= 75 ? "#f59e0b" : "#ef4444",
              }}
            >
              {stats.final.toFixed(2)}%
            </div>
          </div>

          <div
            style={{
              background: "#1a1a1a",
              padding: 16,
              borderRadius: 6,
              border: "1px solid #333",
            }}
          >
            <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
              Overall Trend
            </div>
            <div
              style={{
                fontSize: 24,
                fontWeight: "bold",
                color: stats.trend >= 0 ? "#10b981" : "#ef4444",
              }}
            >
              {stats.trend >= 0 ? "↗" : "↘"} {Math.abs(stats.trend).toFixed(2)}%
            </div>
            <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4, display: 'flex', alignItems: 'center', gap: '4px' }}>
              {stats.trend >= 0 ? <TrendingUp size={14} style={{ color: '#10b981' }} /> : <TrendingDown size={14} style={{ color: '#ef4444' }} />} 
              {stats.trend >= 0 ? "Improving" : "Degrading"}
            </div>
          </div>

          <div
            style={{
              background: "#1a1a1a",
              padding: 16,
              borderRadius: 6,
              border: "1px solid #333",
            }}
          >
            <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
              Improvement
            </div>
            <div
              style={{
                fontSize: 24,
                fontWeight: "bold",
                color: stats.improvement >= 0 ? "#10b981" : "#ef4444",
              }}
            >
              {stats.improvement >= 0 ? "+" : ""}{stats.improvement.toFixed(2)}%
            </div>
            <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4 }}>
              From start to end
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div style={{ background: "#1a1a1a", padding: 16, borderRadius: 6, border: "1px solid #333" }}>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={processedData} margin={{ top: 10, right: 30, left: 60, bottom: 80 }}>
            <defs>
              <linearGradient id="excellentZone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="acceptableZone" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="index"
              stroke="#ffffff"
              tick={{ fill: "#ffffff" }}
              label={{ value: "Data Points", position: "bottom", offset: 10, fill: "#ffffff", fontSize: 12 }}
            />
            <YAxis
              stroke="#ffffff"
              tick={{ fill: "#ffffff" }}
              domain={[0, 100]}
              type="number"
              label={{ value: "Accuracy (%)", angle: -90, position: "left", offset: 10, fill: "#ffffff", fontSize: 12 }}
              ticks={[0, 25, 50, 75, 100]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ color: "#ffffff", paddingTop: "30px" }} verticalAlign="bottom" height={36} />

            {/* Confidence Bands */}
            <ReferenceLine y={85} stroke="#10b981" strokeDasharray="5 5" strokeWidth={2} />
            <ReferenceLine y={75} stroke="#f59e0b" strokeDasharray="5 5" strokeWidth={2} />

            {/* Lines */}
            <Line
              type="monotone"
              dataKey="pointAccuracy"
              stroke="#60a5fa"
              strokeWidth={1.5}
              dot={false}
              name="Point Accuracy"
              opacity={0.4}
            />
            <Line
              type="monotone"
              dataKey="averageConfidence"
              stroke="#10b981"
              strokeWidth={3}
              dot={false}
              name="Average Confidence"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Interpretation Help */}
      <div
        style={{
          marginTop: 16,
          padding: 16,
          background: "linear-gradient(135deg, #1a1a1a 0%, #252525 100%)",
          border: "1px solid #333",
          borderRadius: 6,
          fontSize: 12,
          color: "#aaa",
        }}
      >
        <div style={{ marginBottom: 12, fontWeight: "bold", color: "#FF7A00", display: 'flex', alignItems: 'center', gap: '8px', fontSize: 13 }}>
          <Info size={16} />
          How to Interpret This Chart
        </div>
        <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
          <li>
            <strong style={{ color: "#60a5fa" }}>Point Accuracy (light blue):</strong> Individual
            accuracy at each data point (more volatile)
          </li>
          <li>
            <strong style={{ color: "#10b981" }}>Average Confidence (green):</strong> Overall average
            accuracy from the beginning to current point (shows long-term trend)
          </li>
          <li>
            <strong style={{ color: "#10b981" }}>Green zone (≥85%):</strong> Excellent prediction
            accuracy
          </li>
          <li>
            <strong style={{ color: "#f59e0b" }}>Orange zone (75-85%):</strong> Acceptable prediction
            accuracy
          </li>
          <li>
            <strong style={{ color: "#ef4444" }}>Below 75%:</strong> Low accuracy, system may need
            adjustment
          </li>
        </ul>
        <div style={{ marginTop: 12, fontSize: 11, opacity: 0.7, fontStyle: "italic" }}>
          A stabilizing or upward-trending average confidence line indicates the system is learning
          and improving over time. The green line shows if the overall performance is increasing or decreasing.
        </div>
      </div>
    </div>
  );
};

export default ConfidenceEvolutionChart;
