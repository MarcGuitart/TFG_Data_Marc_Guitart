import React, { useState } from "react";
import "./ControlHeader.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8081";

export default function ControlHeader({ onIdsUpdate }) {
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState("");

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
          className={`btn ${resetting ? "btn-disabled" : "btn-warning"}`}
          onClick={handleReset}
          disabled={uploading || running || exporting || resetting}
        >
          {resetting ? "⏳ Reseteando..." : "🔄 Reset Sistema"}
        </button>
      </div>

      {message && (
        <div className={`control-message ${message.startsWith("❌") ? "error" : "success"}`}>
          {message}
        </div>
      )}
    </div>
  );
}
