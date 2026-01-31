import React, { useState, useRef, useCallback } from 'react';
import ControlHeader from './components/ControlHeader';
import PredictionPanel from "./components/PredictionPanel";
import './App.css';

export default function App() {
  const predictionPanelRef = useRef(null);
  const [analyticsData, setAnalyticsData] = useState({
    selectorData: [],
    viewMode: "full",
    demoPoints: [],
  });

  // Callback cuando se ejecuta pipeline → notificar a PredictionPanel
  const handleIdsUpdate = useCallback(() => {
    // Forzar refresh del PredictionPanel
    if (predictionPanelRef.current?.refreshData) {
      predictionPanelRef.current.refreshData();
    }
  }, []);

  // Callback para actualizar datos de análisis desde PredictionPanel (memoizado para evitar ciclo infinito)
  const handleAnalyticsDataUpdate = useCallback((data) => {
    setAnalyticsData(data);
  }, []);

  return (
    <div className="app-container">
      <ControlHeader 
        onIdsUpdate={handleIdsUpdate}
        analyticsData={analyticsData}
      />
      <PredictionPanel 
        ref={predictionPanelRef}
        onAnalyticsDataUpdate={handleAnalyticsDataUpdate}
      />
    </div>
  );
}
