import React from 'react';
export class ErrorBoundary extends React.Component {
  state = { hasError: false, err: null };
  static getDerivedStateFromError(err){ return { hasError: true, err }; }
  componentDidCatch(err, info){ console.error("[UI] ErrorBoundary", err, info); }
  render(){ return this.state.hasError ? <pre style={{color:'#f66'}}>{String(this.state.err)}</pre> : this.props.children; }
}

<ErrorBoundary>
  <DataPipelineLiveViewer />
  <PredictionPanel />
</ErrorBoundary>
