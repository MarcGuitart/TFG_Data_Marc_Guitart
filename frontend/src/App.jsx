import React, { useState, useRef } from 'react';
import ControlHeader from './components/ControlHeader';
import PredictionPanel from "./components/PredictionPanel";
import './App.css';

export default function App() {
  const predictionPanelRef = useRef(null);

  // Callback cuando se ejecuta pipeline → notificar a PredictionPanel
  const handleIdsUpdate = () => {
    // Forzar refresh del PredictionPanel
    if (predictionPanelRef.current?.refreshData) {
      predictionPanelRef.current.refreshData();
    }
  };

  return (
    <div className="app-container">
      <ControlHeader onIdsUpdate={handleIdsUpdate} />
      <PredictionPanel ref={predictionPanelRef} />
    </div>
  );
}
