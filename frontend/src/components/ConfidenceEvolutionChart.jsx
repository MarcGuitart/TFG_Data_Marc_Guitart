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

/**
 * ConfidenceEvolutionChart
 * 
 * Shows how the prediction confidence/accuracy evolves over time as more data arrives.
 * Displays:
 * - Overall Accuracy Score (100% - MAPE) evolution
 * - Cumulative accuracy (rolling average)
 * - Confidence bands (excellent ≥85%, acceptable 75-85%, low <75%)
 * - Trend to see if the system is improving or degrading
 */
const ConfidenceEvolutionChart = ({ data }) => {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Calculate cumulative accuracy for each point
    const processed = [];
    let cumulativeErrorSum = 0;
    let validCount = 0;

    data.forEach((point, idx) => {
      // Calculate point accuracy (100% - error_rel_mean which is MAPE)
      const pointAccuracy = point.error_rel_mean != null 
        ? 100 - point.error_rel_mean 
        : null;

      // Update cumulative accuracy
      if (pointAccuracy != null) {
        cumulativeErrorSum += point.error_rel_mean;
        validCount += 1;
        const cumulativeAccuracy = 100 - (cumulativeErrorSum / validCount);

        processed.push({
          index: idx + 1,
          t: point.t,
          pointAccuracy: parseFloat(pointAccuracy.toFixed(2)),
          cumulativeAccuracy: parseFloat(cumulativeAccuracy.toFixed(2)),
        });
      }
    });

    return processed;
  }, [data]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (processedData.length === 0) return null;

    const firstHalf = processedData.slice(0, Math.floor(processedData.length / 2));
    const secondHalf = processedData.slice(Math.floor(processedData.length / 2));

    const avgFirst = firstHalf.reduce((sum, p) => sum + p.cumulativeAccuracy, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((sum, p) => sum + p.cumulativeAccuracy, 0) / secondHalf.length;
    const trend = avgSecond - avgFirst;

    const final = processedData[processedData.length - 1];
    const initial = processedData[0];

    return {
      initial: initial.cumulativeAccuracy,
      final: final.cumulativeAccuracy,
      trend: trend,
      improvement: final.cumulativeAccuracy - initial.cumulativeAccuracy,
      avgAccuracy: processedData.reduce((sum, p) => sum + p.cumulativeAccuracy, 0) / processedData.length,
    };
  }, [processedData]);

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
            Point #{data.index} (t={data.t})
          </div>
          <div style={{ color: "#60a5fa", marginBottom: 4 }}>
            <strong>Point Accuracy:</strong> {data.pointAccuracy}%
          </div>
          <div style={{ color: "#10b981", marginBottom: 4 }}>
            <strong>Cumulative Accuracy:</strong> {data.cumulativeAccuracy}%
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
        <h3 style={{ fontSize: 18, marginBottom: 8, color: "#fff" }}>
          📈 Confidence Evolution Over Time
        </h3>
        <p style={{ fontSize: 13, color: "#aaa", marginBottom: 16 }}>
          Shows how the system's prediction accuracy evolves as more data arrives. 
          The cumulative accuracy represents the overall performance up to each point.
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
            <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4 }}>
              {stats.trend >= 0 ? "📈 Improving" : "📉 Degrading"}
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
          <ComposedChart data={processedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
              label={{ value: "Data Points", position: "insideBottom", offset: -5, fill: "#ffffff" }}
            />
            <YAxis
              stroke="#ffffff"
              tick={{ fill: "#ffffff" }}
              domain={[0, 100]}
              label={{ value: "Accuracy (%)", angle: -90, position: "insideLeft", fill: "#ffffff" }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ color: "#ffffff" }} />

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
              dataKey="cumulativeAccuracy"
              stroke="#10b981"
              strokeWidth={3}
              dot={false}
              name="Cumulative Accuracy"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Interpretation Help */}
      <div
        style={{
          marginTop: 16,
          padding: 16,
          background: "#1a1a1a",
          border: "1px solid #333",
          borderRadius: 6,
          fontSize: 12,
          color: "#aaa",
        }}
      >
        <div style={{ marginBottom: 8, fontWeight: "bold", color: "#FF7A00" }}>
          📊 How to Interpret This Chart:
        </div>
        <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.8 }}>
          <li>
            <strong style={{ color: "#60a5fa" }}>Point Accuracy (light blue):</strong> Individual
            accuracy at each data point (more volatile)
          </li>
          <li>
            <strong style={{ color: "#10b981" }}>Cumulative Accuracy (green):</strong> Overall
            accuracy from the beginning to current point (stabilizes over time)
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
          💡 A stabilizing cumulative accuracy line indicates the system has "learned" the data
          patterns. An upward trend shows the adaptive ensemble is improving over time.
        </div>
      </div>
    </div>
  );
};

export default ConfidenceEvolutionChart;
