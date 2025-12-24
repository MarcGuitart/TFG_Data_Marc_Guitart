import React, { useState, useEffect, useRef, useCallback } from "react";
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
} from "recharts";
import "./LivePredictionChart.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

// Estados del pipeline
const STATUS = {
  IDLE: "idle",
  RUNNING: "running",
  FINISHED: "finished",
  ERROR: "error",
};

export default function LivePredictionChart({ selectedId, isRunning }) {
  const [data, setData] = useState([]);
  const [stats, setStats] = useState({
    totalPoints: 0,
    processedPoints: 0,
    progress: 0,
    avgError: 0,
    status: STATUS.IDLE,
  });
  const [windowSize, setWindowSize] = useState(50);
  const [autoScroll, setAutoScroll] = useState(true);
  const pollIntervalRef = useRef(null);
  const lastCountRef = useRef(0);
  const stableCountRef = useRef(0);

  // Reset cuando cambia el ID seleccionado
  useEffect(() => {
    setData([]);
    setStats({
      totalPoints: 0,
      processedPoints: 0,
      progress: 0,
      avgError: 0,
      status: STATUS.IDLE,
    });
    lastCountRef.current = 0;
    stableCountRef.current = 0;
  }, [selectedId]);

  // Función para obtener datos en tiempo real
  const fetchLiveData = useCallback(async () => {
    if (!selectedId) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/series?id=${encodeURIComponent(selectedId)}&start=-1d`
      );
      if (!res.ok) {
        setStats(prev => ({ ...prev, status: STATUS.ERROR }));
        return;
      }

      const jsonData = await res.json();
      
      // Normalizar datos: soporta tanto "data" como "points" (ANTES del early return)
      const rawData = jsonData.data || jsonData.points || [];
      if (!Array.isArray(rawData) || rawData.length === 0) {
        console.warn("LivePredictionChart: sin datos o formato inválido", jsonData);
        return;
      }

      // Transformar datos para la gráfica
      const chartData = rawData.map((point, idx) => {
        const error =
          point.var && point.yhat
            ? Math.abs(point.var - point.yhat)
            : null;

        return {
          index: idx,
          time: point.timestamp || `T${idx}`,
          actual: point.var || null,
          predicted: point.yhat || null,
          kalman: point.hyper_models?.kalman || null,
          linear: point.hyper_models?.linear || null,
          poly: point.hyper_models?.poly || null,
          alphabeta: point.hyper_models?.alphabeta || null,
          error: error,
          chosen: point.chosen_model || "-",
          errorAbs: point.chosen_error_abs || null,
          errorRel: point.chosen_error_rel || null, // Ya viene en % desde backend
        };
      });

      // Calcular estadísticas
      const processedPoints = chartData.length;
      const totalPoints = jsonData.total || processedPoints;
      const progress = totalPoints > 0 ? (processedPoints / totalPoints) * 100 : 0;
      const errors = chartData
        .map((p) => p.error)
        .filter((e) => e !== null);
      const avgError =
        errors.length > 0
          ? errors.reduce((a, b) => a + b) / errors.length
          : 0;

      // Detectar estado: si el conteo no cambia en 3 polls consecutivos, está terminado
      if (processedPoints === lastCountRef.current) {
        stableCountRef.current += 1;
      } else {
        stableCountRef.current = 0;
      }
      lastCountRef.current = processedPoints;

      // Determinar estado del pipeline
      let status;
      if (!isRunning && processedPoints === 0) {
        status = STATUS.IDLE;
      } else if (isRunning && stableCountRef.current < 3) {
        status = STATUS.RUNNING;
      } else if (processedPoints > 0 && (stableCountRef.current >= 3 || progress >= 99.9)) {
        status = STATUS.FINISHED;
      } else {
        status = isRunning ? STATUS.RUNNING : STATUS.IDLE;
      }

      setData(chartData);
      setStats({
        totalPoints,
        processedPoints,
        progress,
        avgError: avgError.toFixed(4),
        status,
      });
    } catch (err) {
      console.error("Error fetching live data:", err);
      setStats(prev => ({ ...prev, status: STATUS.ERROR }));
    }
  }, [selectedId, isRunning]);

  // Polling controlado
  useEffect(() => {
    // Limpiar intervalo anterior
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    if (isRunning || stats.status === STATUS.RUNNING) {
      // Fetch inmediato
      fetchLiveData();
      // Polling cada 1 segundo
      pollIntervalRef.current = setInterval(fetchLiveData, 1000);
    } else if (selectedId) {
      // Fetch único cuando no está corriendo pero hay ID
      fetchLiveData();
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [selectedId, isRunning, fetchLiveData]);

  // Ventana dinámica: mostrar solo los últimos N puntos
  const displayData = autoScroll
    ? data.slice(Math.max(0, data.length - windowSize))
    : data;

  // Formatear números
  const formatNumber = (val) => {
    if (val === null || val === undefined) return "-";
    return typeof val === "number" ? val.toFixed(2) : val;
  };

  return (
    <div className="live-prediction-chart-container">
      <div className="live-header">
        <h3>🎯 Predicción en Tiempo Real</h3>
        <div className="live-controls">
          <label>
            Window Size:
            <input
              type="range"
              min="10"
              max="200"
              step="10"
              value={windowSize}
              onChange={(e) => setWindowSize(parseInt(e.target.value))}
            />
            <span>{windowSize} puntos</span>
          </label>
          <label>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto Scroll
          </label>
        </div>
      </div>

      {/* Barra de progreso */}
      <div className="live-progress">
        <div className="progress-info">
          <span className="progress-text">
            {stats.processedPoints} / {stats.totalPoints} puntos procesados
          </span>
          <span className="progress-percent">
            {stats.progress.toFixed(1)}%
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${stats.progress}%` }}
          />
        </div>
        <div className="progress-stats">
          <span>
            Status:{" "}
            <strong
              className={`status-badge status-${stats.status}`}
            >
              {stats.status === STATUS.IDLE && "⏸️ En espera"}
              {stats.status === STATUS.RUNNING && "▶️ EN DIRECTO"}
              {stats.status === STATUS.FINISHED && "✅ Completado"}
              {stats.status === STATUS.ERROR && "❌ Error"}
            </strong>
          </span>
          <span>
            Error Promedio: <strong>{stats.avgError}</strong>
          </span>
        </div>
      </div>

      {/* Gráfica */}
      <div className="live-chart-wrapper">
        {displayData.length === 0 ? (
          <div className="live-empty">
            <p>Esperando datos...</p>
            <p className="text-small">Carga un CSV y ejecuta el pipeline para ver las predicciones en tiempo real</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={displayData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="index"
                stroke="#6b7280"
                tick={{ fontSize: 12 }}
                interval={Math.floor(displayData.length / 10)}
              />
              <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#ffffff",
                  border: "1px solid #e5e7eb",
                  borderRadius: "6px",
                  padding: "10px",
                }}
                formatter={(value) => formatNumber(value)}
                labelFormatter={(label) => `Punto ${label}`}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                height={30}
              />

              {/* Serie Real */}
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#ef4444"
                strokeWidth={2.5}
                dot={false}
                name="Real"
                isAnimationActive={false}
              />

              {/* Predicción Adaptativa */}
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#f59e0b"
                strokeWidth={2.5}
                dot={false}
                name="Predicción Adaptativa"
                isAnimationActive={false}
                strokeDasharray="5 5"
              />

              {/* Modelos Individuales */}
              <Line
                type="monotone"
                dataKey="kalman"
                stroke="#3b82f6"
                strokeWidth={1}
                dot={false}
                name="Kalman"
                isAnimationActive={false}
                opacity={0.6}
              />
              <Line
                type="monotone"
                dataKey="linear"
                stroke="#10b981"
                strokeWidth={1}
                dot={false}
                name="Linear"
                isAnimationActive={false}
                opacity={0.6}
              />
              <Line
                type="monotone"
                dataKey="poly"
                stroke="#8b5cf6"
                strokeWidth={1}
                dot={false}
                name="Polynomial"
                isAnimationActive={false}
                opacity={0.6}
              />
              <Line
                type="monotone"
                dataKey="alphabeta"
                stroke="#ec4899"
                strokeWidth={1}
                dot={false}
                name="AlphaBeta"
                isAnimationActive={false}
                opacity={0.6}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Tabla de últimos puntos */}
      <div className="live-table-wrapper">
        <h4>Últimos Puntos Procesados</h4>
        <div className="live-table-scroll">
          <table className="live-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Real</th>
                <th>Predicción</th>
                <th>Error</th>
                <th>Modelo Elegido</th>
                <th>Error %</th>
              </tr>
            </thead>
            <tbody>
              {displayData.slice(-10).map((point) => {
                // errorRel ya viene en % desde backend (con clamp ±100%)
                const errorRelValue = point.errorRel || 0;
                const errorRelAbs = Math.abs(errorRelValue);
                
                // Colores por severidad
                let errorRelClass = "";
                if (errorRelAbs > 50) errorRelClass = "table-error-critical";
                else if (errorRelAbs > 20) errorRelClass = "table-error-high";
                else if (errorRelAbs > 10) errorRelClass = "table-error-medium";
                
                return (
                  <tr key={point.index}>
                    <td className="table-index">{point.index}</td>
                    <td>{formatNumber(point.actual)}</td>
                    <td className="table-bold">{formatNumber(point.predicted)}</td>
                    <td className={point.error > 0.1 ? "table-error-high" : ""}>
                      {formatNumber(point.error)}
                    </td>
                    <td className="table-model">{point.chosen}</td>
                    <td className={errorRelClass}>
                      {point.errorRel ? errorRelValue.toFixed(2) : "-"}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Leyenda de colores */}
      <div className="live-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: "#ef4444" }} />
          <span>Serie Real</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: "#f59e0b" }} />
          <span>Predicción Adaptativa</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: "#3b82f6" }} />
          <span>Kalman</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: "#10b981" }} />
          <span>Linear</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: "#8b5cf6" }} />
          <span>Polynomial</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: "#ec4899" }} />
          <span>AlphaBeta</span>
        </div>
      </div>
    </div>
  );
}
