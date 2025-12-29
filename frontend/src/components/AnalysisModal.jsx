import React, { useState, useRef } from "react";
import {
  Upload,
  FileText,
  Send,
  X as CloseIcon,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Info,
  BarChart3,
  TrendingUp,
  Zap,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./AnalysisModal.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

/**
 * AnalysisModal: Modal para análisis personalizado con IA
 * - Preview del pipeline report
 * - Drag & drop para cargar Export Report (CSV con weights históricos)
 * - Botón para enviar a IA con contexto enriquecido
 */
export default function AnalysisModal({ isOpen, onClose, currentId = "Other" }) {
  const [pipelineReport, setPipelineReport] = useState(null);
  const [exportReport, setExportReport] = useState(null);
  const [exportFileName, setExportFileName] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  const [loadingReport, setLoadingReport] = useState(false);

  // Cargar pipeline report al abrir modal
  React.useEffect(() => {
    if (isOpen && !pipelineReport) {
      loadPipelineReport();
    }
  }, [isOpen]);

  // Cargar el pipeline report (datos del último run)
  const loadPipelineReport = async () => {
    setLoadingReport(true);
    try {
      // Obtener datos de series actuales
      const params = new URLSearchParams({
        id: currentId,
        hours: "999", // Todos los datos
      });

      const res = await fetch(`${API_BASE}/api/series?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to load series data");

      const data = await res.json();
      setPipelineReport(data);
    } catch (err) {
      console.error("Error loading pipeline report:", err);
      setPipelineReport({
        error: "Could not load pipeline report",
        message: err.message,
      });
    } finally {
      setLoadingReport(false);
    }
  };

  // Drag & drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      processCSVFile(files[0]);
    }
  };

  // Procesar CSV del Export Report
  const processCSVFile = async (file) => {
    if (!file.name.includes(".csv")) {
      alert("Please drop a CSV file");
      return;
    }

    try {
      const text = await file.text();
      setExportReport(text);
      setExportFileName(file.name);
    } catch (err) {
      console.error("Error reading file:", err);
      alert("Error reading CSV file");
    }
  };

  // Enviar análisis a IA con contexto enriquecido
  const handleAnalyzeWithAI = async () => {
    if (!pipelineReport) {
      alert("Pipeline report not loaded");
      return;
    }

    setAnalyzing(true);
    setAnalysisResult(null);

    try {
      const payload = {
        series_id: currentId,
        pipeline_report: pipelineReport,
        export_report: exportReport ? exportReport : null,
        export_filename: exportFileName || null,
      };

      const res = await fetch(`${API_BASE}/api/analyze_report_advanced/${currentId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setAnalysisResult(data.analysis);
    } catch (err) {
      console.error("Analysis error:", err);
      setAnalysisResult(`Error: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="analysis-modal-overlay" onClick={onClose}>
      <div className="analysis-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="analysis-modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <BarChart3 size={20} />
            <h2 style={{ margin: 0 }}>Advanced Report Analysis</h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "#fff",
              cursor: "pointer",
              fontSize: "20px",
            }}
          >
            <CloseIcon size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="analysis-modal-body">
          {/* Left Panel: Pipeline Report Preview */}
          <div className="analysis-panel">
            <h3 style={{ color: "#FF7A00", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <TrendingUp size={18} />
              Pipeline Execution Report
            </h3>

            {loadingReport ? (
              <div style={{ textAlign: "center", color: "#999" }}>
                <Loader2 size={16} className="spin" style={{ marginRight: "8px" }} />
                Loading report...
              </div>
            ) : pipelineReport?.error ? (
              <div
                style={{
                  background: "#3f1f1f",
                  border: "1px solid #8b3333",
                  padding: "12px",
                  borderRadius: "4px",
                  color: "#ff6b6b",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                {pipelineReport.message || pipelineReport.error}
              </div>
            ) : pipelineReport ? (
              <div
                style={{
                  background: "#1a1a1a",
                  border: "1px solid #FF7A00",
                  borderRadius: "6px",
                  padding: "16px",
                  maxHeight: "350px",
                  overflowY: "auto",
                  fontSize: "12px",
                  color: "#ccc",
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "12px",
                    marginBottom: "16px",
                  }}
                >
                  <div
                    style={{
                      background: "#0a0a0a",
                      padding: "10px",
                      borderRadius: "4px",
                      borderLeft: "3px solid #FF7A00",
                    }}
                  >
                    <div style={{ color: "#999", fontSize: "10px" }}>Series ID</div>
                    <div style={{ fontWeight: "bold", color: "#FF7A00" }}>
                      {pipelineReport.id}
                    </div>
                  </div>
                  <div
                    style={{
                      background: "#0a0a0a",
                      padding: "10px",
                      borderRadius: "4px",
                      borderLeft: "3px solid #10b981",
                    }}
                  >
                    <div style={{ color: "#999", fontSize: "10px" }}>Total Points</div>
                    <div style={{ fontWeight: "bold", color: "#10b981" }}>
                      {pipelineReport.total || 0}
                    </div>
                  </div>
                </div>

                {pipelineReport.points && pipelineReport.points.length > 0 && (
                  <>
                    <div
                      style={{
                        background: "#0a0a0a",
                        padding: "10px",
                        borderRadius: "4px",
                        marginBottom: "12px",
                        borderLeft: "3px solid #8b5cf6",
                      }}
                    >
                      <div style={{ color: "#999", fontSize: "10px", marginBottom: "4px" }}>
                        Time Range
                      </div>
                      <div style={{ fontSize: "11px", color: "#ccc" }}>
                        <div>{pipelineReport.points[0]?.timestamp}</div>
                        <div style={{ color: "#999", margin: "2px 0" }}>→</div>
                        <div>
                          {pipelineReport.points[pipelineReport.points.length - 1]?.timestamp}
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : null}
          </div>

          {/* Middle Panel: Export Report Upload */}
          <div className="analysis-panel">
            <h3 style={{ color: "#FF7A00", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Upload size={18} />
              Historical Context
            </h3>
            <p style={{ fontSize: "11px", color: "#999", marginBottom: "12px", lineHeight: "1.4" }}>
              Add or drag the report generated after running the agent with the Export Report button to provide better execution context and obtain more precise analysis of your processed data.
            </p>

            <div
              className={`drag-drop-zone ${dragActive ? "active" : ""}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              {exportReport ? (
                <div style={{ textAlign: "center" }}>
                  <CheckCircle size={28} style={{ color: "#10b981", marginBottom: "8px" }} />
                  <div style={{ fontSize: "12px", fontWeight: "bold" }}>File Loaded</div>
                  <div style={{ fontSize: "10px", color: "#999", marginTop: "4px", wordBreak: "break-all" }}>
                    {exportFileName}
                  </div>
                  <button
                    onClick={() => {
                      setExportReport(null);
                      setExportFileName("");
                    }}
                    style={{
                      marginTop: "8px",
                      background: "#333",
                      border: "1px solid #666",
                      color: "#fff",
                      padding: "4px 12px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      fontSize: "10px",
                    }}
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div style={{ textAlign: "center" }}>
                  <Upload size={28} style={{ color: "#666", marginBottom: "8px" }} />
                  <div style={{ fontSize: "11px" }}>Drop CSV file here</div>
                  <div style={{ fontSize: "9px", color: "#999", marginTop: "4px" }}>
                    or click to browse
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        processCSVFile(e.target.files[0]);
                      }
                    }}
                    style={{ display: "none" }}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      marginTop: "8px",
                      background: "#333",
                      border: "1px solid #666",
                      color: "#fff",
                      padding: "4px 12px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      fontSize: "10px",
                    }}
                  >
                    Browse Files
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Analysis Result */}
          <div className="analysis-panel">
            <h3 style={{ color: "#FF7A00", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Zap size={18} />
              AI Analysis Result
            </h3>

            {analyzing ? (
              <div style={{ textAlign: "center", color: "#999", paddingTop: "100px" }}>
                <Loader2 size={20} className="spin" style={{ marginRight: "8px" }} />
                <div>Analyzing with AI...</div>
              </div>
            ) : analysisResult ? (
              <div
                style={{
                  background: "#1a1a1a",
                  border: "1px solid #FF7A00",
                  borderRadius: "4px",
                  padding: "12px",
                  maxHeight: "100%",
                  overflowY: "auto",
                  fontSize: "12px",
                  color: "#ccc",
                }}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {analysisResult}
                </ReactMarkdown>
              </div>
            ) : (
              <div
                style={{
                  textAlign: "center",
                  color: "#999",
                  paddingTop: "120px",
                  fontSize: "12px",
                }}
              >
                <Info size={32} style={{ marginBottom: "8px", opacity: 0.5 }} />
                Click "Analyze with AI" to generate analysis
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="analysis-modal-footer">
          <button
            onClick={onClose}
            style={{
              background: "#333",
              border: "1px solid #666",
              color: "#fff",
              padding: "8px 16px",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "12px",
            }}
          >
            Close
          </button>
          <button
            onClick={handleAnalyzeWithAI}
            disabled={analyzing || !pipelineReport}
            style={{
              background: analyzing ? "#666" : "#FF7A00",
              border: "none",
              color: "#fff",
              padding: "8px 16px",
              borderRadius: "4px",
              cursor: analyzing ? "not-allowed" : "pointer",
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {analyzing ? (
              <>
                <Loader2 size={14} className="spin" /> Analyzing...
              </>
            ) : (
              <>
                <Zap size={14} /> Analyze with AI
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
