import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./ControlHeader.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

export default function ControlHeader({ onIdsUpdate }) {
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);

  // Upload CSV
  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessage("⏳ Subiendo archivo...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/api/upload_csv`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      setMessage(`✅ Archivo subido: ${file.name}`);
      console.log("Upload response:", data);
    } catch (err) {
      setMessage(`❌ Error: ${err.message}`);
      console.error("Upload error:", err);
    } finally {
      setUploading(false);
      // Reset file input
      e.target.value = "";
    }
  };

  // Run pipeline
  const handleRun = async () => {
    setRunning(true);
    setMessage("⏳ Ejecutando pipeline...");

    try {
      const res = await fetch(`${API_BASE}/api/run_window`, {
        method: "POST",
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      
      // Extraer rows del response correcto
      const rows = data.loader_response?.rows || data.rows_flushed || 0;
      const uniqueIds = data.loader_response?.unique_ids || [];
      
      setMessage(`✅ Pipeline ejecutado: ${rows} filas procesadas`);
      console.log("Run response:", data);
      console.log("IDs detectados:", uniqueIds);

      // Emitir evento con el primer ID detectado
      if (uniqueIds.length > 0) {
        const firstId = uniqueIds[0];
        console.log("Emitiendo seriesSelected con ID:", firstId);
        
        // Guardar ID actual en localStorage para el botón Export
        window.localStorage.setItem('currentSeriesId', firstId);
        
        window.dispatchEvent(
          new CustomEvent("seriesSelected", {
            detail: { id: firstId, rows: rows }
          })
        );
      }

      // Notificar refresh tras 2 segundos
      setTimeout(() => {
        if (onIdsUpdate) onIdsUpdate();
      }, 2000);
    } catch (err) {
      setMessage(`❌ Error: ${err.message}`);
      console.error("Run error:", err);
    } finally {
      setRunning(false);
    }
  };

  // Export Report (CSV with weights history)
  const handleExport = async () => {
    setExporting(true);
    setMessage("⏳ Generando reporte...");

    try {
      // Obtener el ID actual desde el evento seriesSelected o usar "Other"
      const currentId = window.localStorage.getItem('currentSeriesId') || "Other";
      
      // Descargar directamente desde el orchestrator (tiene CORS habilitado)
      const downloadUrl = `${API_BASE}/api/download_weights/${currentId}`;
      
      // Crear link de descarga
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `weights_history_${currentId}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setMessage(`✅ Reporte exportado: weights_history_${currentId}.csv`);
    } catch (err) {
      setMessage(`❌ Error exportando: ${err.message}`);
      console.error("Export error:", err);
    } finally {
      setExporting(false);
    }
  };

  // Analyze Report with AI
  const handleAnalyze = async () => {
    setAnalyzing(true);
    setMessage("🤖 Analizando datos con IA...");
    setAnalysisResult(null);

    try {
      const currentId = window.localStorage.getItem('currentSeriesId') || "Other";
      
      // Llamar al endpoint del backend que hará el análisis con IA
      const res = await fetch(`${API_BASE}/api/analyze_report/${currentId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setAnalysisResult(data.analysis);
      setMessage("✅ Análisis completado");
    } catch (err) {
      setMessage(`❌ Error analizando: ${err.message}`);
      console.error("Analysis error:", err);
    } finally {
      setAnalyzing(false);
    }
  };

  // Reset System (limpiar pesos e historial)
  const handleReset = async () => {
    // Confirmar antes de resetear
    const confirmed = window.confirm(
      "⚠️ Esto limpiará:\n" +
      "- Todos los pesos acumulados\n" +
      "- Historial de predicciones\n" +
      "- Datos de deduplicación\n\n" +
      "¿Estás seguro?"
    );
    
    if (!confirmed) return;
    
    setResetting(true);
    setMessage("⏳ Reseteando sistema...");

    try {
      const res = await fetch(`${API_BASE}/api/reset_system`, {
        method: "POST",
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      console.log("Reset response:", data);
      
      if (data.status === "success") {
        setMessage(`✅ Sistema reseteado. Listo para nuevo experimento.`);
      } else {
        setMessage(`⚠️ Reseteo parcial. Revisa la consola.`);
        console.warn("Reset details:", data.details);
      }
    } catch (err) {
      setMessage(`❌ Error reseteando: ${err.message}`);
      console.error("Reset error:", err);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="control-header">
      <div className="control-section">
        <h2>🎯 Control Panel</h2>
      </div>

      <div className="control-section">
        <label className="upload-btn">
          <input
            type="file"
            accept=".csv"
            onChange={handleUpload}
            disabled={uploading || running}
            style={{ display: "none" }}
          />
          <span className={`btn ${uploading ? "btn-disabled" : "btn-primary"}`}>
            {uploading ? "⏳ Subiendo..." : "📁 Cargar CSV"}
          </span>
        </label>

        <button
          className={`btn ${running ? "btn-disabled" : "btn-success"}`}
          onClick={handleRun}
          disabled={uploading || running}
        >
          {running ? "⏳ Procesando..." : "🚀 Ejecutar Pipeline"}
        </button>

        <button
          className={`btn ${exporting ? "btn-disabled" : "btn-info"}`}
          onClick={handleExport}
          disabled={uploading || running || exporting}
        >
          {exporting ? "⏳ Exportando..." : "📊 Exportar Reporte"}
        </button>

        <button
          className={`btn ${analyzing ? "btn-disabled" : "btn-info"}`}
          onClick={handleAnalyze}
          disabled={uploading || running || analyzing}
          style={{ background: analyzing ? "#666" : "#9333ea" }}
        >
          {analyzing ? "🤖 Analizando..." : "🤖 Analizar con IA"}
        </button>

        <button
          className={`btn ${resetting ? "btn-disabled" : "btn-warning"}`}
          onClick={handleReset}
          disabled={uploading || running || exporting || resetting}
        >
          {resetting ? "⏳ Reseteando..." : "🔄 Reset System"}
        </button>
      </div>

      {message && (
        <div className={`control-message ${message.startsWith("❌") ? "error" : "success"}`}>
          {message}
        </div>
      )}

      {/* AI Analysis Modal - Professional Design with Markdown */}
      {analysisResult && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.92)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10000,
            padding: "20px",
            backdropFilter: "blur(4px)",
          }}
          onClick={() => setAnalysisResult(null)}
        >
          <div
            style={{
              background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
              border: "2px solid #3b82f6",
              borderRadius: 16,
              padding: "0",
              maxWidth: "900px",
              width: "100%",
              maxHeight: "85vh",
              overflow: "hidden",
              color: "#fff",
              boxShadow: "0 25px 80px rgba(59, 130, 246, 0.3), 0 0 0 1px rgba(59, 130, 246, 0.1)",
              display: "flex",
              flexDirection: "column",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{ 
              padding: "24px 32px",
              borderBottom: "1px solid rgba(59, 130, 246, 0.3)",
              background: "rgba(59, 130, 246, 0.08)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}>
              <div>
                <h2 style={{ 
                  margin: 0, 
                  color: "#fff", 
                  fontSize: 26,
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  gap: "12px"
                }}>
                  <span style={{ fontSize: 32 }}>🤖</span>
                  AI Analysis Report
                </h2>
                <p style={{ 
                  margin: "8px 0 0 0", 
                  color: "#60a5fa", 
                  fontSize: 13,
                  fontWeight: 400
                }}>
                  Automated analysis of ensemble performance
                </p>
              </div>
              <button
                onClick={() => setAnalysisResult(null)}
                style={{
                  background: "rgba(255, 255, 255, 0.1)",
                  border: "1px solid rgba(255, 255, 255, 0.2)",
                  color: "#fff",
                  fontSize: 24,
                  cursor: "pointer",
                  padding: "8px 14px",
                  borderRadius: 8,
                  transition: "all 0.2s",
                  fontWeight: "bold",
                }}
                onMouseOver={(e) => {
                  e.target.style.background = "rgba(255, 255, 255, 0.2)";
                }}
                onMouseOut={(e) => {
                  e.target.style.background = "rgba(255, 255, 255, 0.1)";
                }}
              >
                ×
              </button>
            </div>

            {/* Content with Markdown rendering */}
            <div
              style={{
                flex: 1,
                overflow: "auto",
                padding: "32px",
                background: "#0a0a0a",
              }}
            >
              <div
                className="markdown-content"
                style={{
                  lineHeight: 1.8,
                  fontSize: 15,
                  color: "#e5e5e5",
                }}
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({node, ...props}) => <h1 style={{ 
                      color: '#fff', 
                      fontSize: 28, 
                      marginTop: 24, 
                      marginBottom: 16,
                      fontWeight: 700,
                      borderBottom: "2px solid #3b82f6",
                      paddingBottom: 8
                    }} {...props} />,
                    h2: ({node, ...props}) => <h2 style={{ 
                      color: '#60a5fa', 
                      fontSize: 22, 
                      marginTop: 28, 
                      marginBottom: 14,
                      fontWeight: 600,
                      display: "flex",
                      alignItems: "center",
                      gap: 8
                    }} {...props} />,
                    h3: ({node, ...props}) => <h3 style={{ 
                      color: '#93c5fd', 
                      fontSize: 18, 
                      marginTop: 20, 
                      marginBottom: 10,
                      fontWeight: 600
                    }} {...props} />,
                    p: ({node, ...props}) => <p style={{ 
                      marginBottom: 16, 
                      color: '#d4d4d4',
                      lineHeight: 1.8
                    }} {...props} />,
                    ul: ({node, ...props}) => <ul style={{ 
                      marginLeft: 24, 
                      marginBottom: 16,
                      listStyleType: 'disc',
                      color: '#d4d4d4'
                    }} {...props} />,
                    ol: ({node, ...props}) => <ol style={{ 
                      marginLeft: 24, 
                      marginBottom: 16,
                      color: '#d4d4d4'
                    }} {...props} />,
                    li: ({node, ...props}) => <li style={{ 
                      marginBottom: 8,
                      paddingLeft: 4,
                      color: '#d4d4d4'
                    }} {...props} />,
                    strong: ({node, ...props}) => <strong style={{ 
                      color: '#fff', 
                      fontWeight: 700 
                    }} {...props} />,
                    em: ({node, ...props}) => <em style={{ 
                      color: '#a78bfa', 
                      fontStyle: 'italic' 
                    }} {...props} />,
                    code: ({node, inline, ...props}) => inline ? (
                      <code style={{ 
                        background: 'rgba(59, 130, 246, 0.15)', 
                        padding: '2px 6px', 
                        borderRadius: 4, 
                        color: '#60a5fa',
                        fontSize: 13,
                        fontFamily: 'monospace'
                      }} {...props} />
                    ) : (
                      <code style={{ 
                        display: 'block', 
                        background: 'rgba(0, 0, 0, 0.5)', 
                        padding: 16, 
                        borderRadius: 8, 
                        marginBottom: 16,
                        color: '#60a5fa',
                        fontSize: 13,
                        fontFamily: 'monospace',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        overflowX: 'auto'
                      }} {...props} />
                    ),
                    blockquote: ({node, ...props}) => <blockquote style={{
                      borderLeft: '4px solid #3b82f6',
                      paddingLeft: 16,
                      marginLeft: 0,
                      marginBottom: 16,
                      color: '#60a5fa',
                      fontStyle: 'italic',
                      background: 'rgba(59, 130, 246, 0.08)',
                      padding: '12px 16px',
                      borderRadius: 4
                    }} {...props} />,
                  }}
                >
                  {analysisResult}
                </ReactMarkdown>
              </div>
            </div>

            {/* Footer */}
            <div style={{ 
              padding: "20px 32px",
              borderTop: "1px solid rgba(59, 130, 246, 0.3)",
              background: "rgba(59, 130, 246, 0.05)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}>
              <p style={{ 
                margin: 0, 
                color: "#888", 
                fontSize: 12 
              }}>
                💡 This analysis was generated using AI and should be validated by domain experts.
              </p>
              <button
                onClick={() => setAnalysisResult(null)}
                style={{
                  background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
                  border: "none",
                  color: "#fff",
                  padding: "12px 28px",
                  borderRadius: 8,
                  cursor: "pointer",
                  fontSize: 14,
                  fontWeight: 600,
                  boxShadow: "0 4px 12px rgba(59, 130, 246, 0.4)",
                  transition: "all 0.2s",
                }}
                onMouseOver={(e) => {
                  e.target.style.transform = "translateY(-2px)";
                  e.target.style.boxShadow = "0 6px 16px rgba(59, 130, 246, 0.5)";
                }}
                onMouseOut={(e) => {
                  e.target.style.transform = "translateY(0)";
                  e.target.style.boxShadow = "0 4px 12px rgba(59, 130, 246, 0.4)";
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
