import React from "react";
import Papa from "papaparse";

export default function KafkaInUploader({ onDataLoaded }) {
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: ({ data }) => {
        // normaliza: timestamp->ISO, value->number
        const rows = data
          .filter(r => r.timestamp && r.value)
          .map(r => ({
            timestamp: new Date(r.timestamp).toISOString(),
            value: Number(r.value)
          }));
        onDataLoaded(rows);
      },
      error: (err) => console.error("CSV parse error:", err),
    });
  };

  return (
    <div style={{ marginTop: 12 }}>
      <label
        htmlFor="csv-file"
        style={{
          padding: "8px 12px",
          borderRadius: 8,
          background: "#2f81f7",
          color: "white",
          cursor: "pointer",
          fontWeight: 600,
        }}
      >
        Seleccionar CSV
      </label>
      <input
        id="csv-file"
        type="file"
        accept=".csv"
        onChange={handleFileUpload}
        style={{ display: "none" }}
      />
    </div>
  );
}
