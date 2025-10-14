import React from 'react';
import PredictionPanel from "./components/PredictionPanel";
import DataPipelineLiveViewer from './components/DataPipelineLiveViewer';

export default function App() {
  return (
    <>
      <DataPipelineLiveViewer />
      <PredictionPanel />
    </>
  );
}
