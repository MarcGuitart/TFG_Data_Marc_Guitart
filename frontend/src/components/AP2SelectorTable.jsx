import React, { useMemo, useState } from "react";

/**
 * AP2: Adaptive Selector Table with:
 * - Timestamp
 * - Selected model
 * - Relative error (%)
 * - Absolute error
 * 
 * Props:
 * - data: array of {t, chosen_model, error_rel, error_abs, y_real, y_pred}
 * - onRowHover: callback when user hovers over a row
 */

// Helper: format relative error with visual clamp
const formatErrorRel = (val) => {
  if (val == null || val === undefined) return "—";
  const num = parseFloat(val);
  if (!isFinite(num)) return "⚠️ N/A";
  // Visual clamp to avoid showing absurd values
  if (Math.abs(num) > 100) {
    return num > 0 ? ">100%" : "<-100%";
  }
  return `${num.toFixed(2)}%`;
};

// Helper: color for relative error
const getErrorRelColor = (val) => {
  if (val == null || !isFinite(val)) return "#999";
  const absVal = Math.abs(val);
  if (absVal > 50) return "#FF4444";  // Strong red
  if (absVal > 20) return "#FF6B6B";  // Red
  if (absVal > 10) return "#FFD93D";  // Yellow
  return "#4ECDC4";  // Green
};

export default function AP2SelectorTable({ data = [], onRowHover, maxRows = 1000 }) {
  const [sortConfig, setSortConfig] = useState({ key: "t", direction: "asc" });
  const [filterModel, setFilterModel] = useState(null);

  const processedData = useMemo(() => {
    let rows = Array.isArray(data) ? data.slice(0, maxRows) : [];
    
    // Filter by model if selected
    if (filterModel) {
      rows = rows.filter((r) => r.chosen_model === filterModel);
    }
    
    // Sort
    rows.sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
    
    return rows;
  }, [data, sortConfig, filterModel, maxRows]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === "asc" ? "desc" : "asc",
    }));
  };

  const uniqueModels = useMemo(() => {
    const models = new Set();
    (Array.isArray(data) ? data : []).forEach((r) => {
      if (r.chosen_model) models.add(r.chosen_model);
    });
    return Array.from(models).sort();
  }, [data]);

  const formatTime = (t) => {
    try {
      return new Date(t).toLocaleString();
    } catch {
      return String(t);
    }
  };

  const sortArrow = (key) => {
    if (sortConfig.key !== key) return " ↕";
    return sortConfig.direction === "asc" ? " ↑" : " ↓";
  };

  if (!processedData.length) {
    return (
      <div style={{ width: "100%", marginTop: 20 }}>
        <h3>Adaptive Selector Table</h3>
        <p style={{ color: "#ccc" }}>(no data)</p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", marginTop: 20, marginBottom: 20 }}>
      <h3>Adaptive Selector Table</h3>
      <p style={{ fontSize: 12, color: "#ffffffff", marginBottom: 10 }}>
        Each row shows the selected model, its point error (in % and absolute value) for each timestamp.
      </p>

      {/* Filters */}
      <div style={{ marginBottom: 15, display: "flex", gap: 10, alignItems: "center" }}>
        <label style={{ fontSize: 12 }}>Filter by model:</label>
        <select
          value={filterModel || ""}
          onChange={(e) => setFilterModel(e.target.value || null)}
          style={{ padding: "5px", fontSize: 12 }}
        >
          <option value="">All</option>
          {uniqueModels.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <span style={{ fontSize: 11, color: "#999" }}>
          Showing {processedData.length} of {data.length} rows
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 12,
            backgroundColor: "#1e1e1e",
            color: "#e0e0e0",
          }}
        >
          <thead style={{ backgroundColor: "#2d2d2d", borderBottom: "2px solid #444" }}>
            <tr>
              <th
                onClick={() => handleSort("t")}
                style={{
                  padding: "10px",
                  textAlign: "left",
                  cursor: "pointer",
                  userSelect: "none",
                  borderRight: "1px solid #444",
                }}
              >
                Timestamp {sortArrow("t")}
              </th>
              <th
                onClick={() => handleSort("chosen_model")}
                style={{
                  padding: "10px",
                  textAlign: "left",
                  cursor: "pointer",
                  userSelect: "none",
                  borderRight: "1px solid #444",
                }}
              >
                Model {sortArrow("chosen_model")}
              </th>
              <th
                onClick={() => handleSort("error_rel")}
                style={{
                  padding: "10px",
                  textAlign: "right",
                  cursor: "pointer",
                  userSelect: "none",
                  borderRight: "1px solid #444",
                }}
              >
                Error (%) {sortArrow("error_rel")}
              </th>
              <th
                onClick={() => handleSort("error_abs")}
                style={{
                  padding: "10px",
                  textAlign: "right",
                  cursor: "pointer",
                  userSelect: "none",
                  borderRight: "1px solid #444",
                }}
              >
                Abs. Error {sortArrow("error_abs")}
              </th>
              <th style={{ padding: "10px", textAlign: "right", borderRight: "1px solid #444" }}>
                Real
              </th>
              <th style={{ padding: "10px", textAlign: "right" }}>
                Predicted
              </th>
            </tr>
          </thead>
          <tbody>
            {processedData.map((row, idx) => (
              <tr
                key={idx}
                onMouseEnter={() => onRowHover && onRowHover(row)}
                onMouseLeave={() => onRowHover && onRowHover(null)}
                style={{
                  backgroundColor: idx % 2 === 0 ? "#252525" : "#1e1e1e",
                  borderBottom: "1px solid #333",
                  cursor: "pointer",
                  transition: "background-color 0.2s",
                }}
                onMouseOver={(e) => (e.currentTarget.style.backgroundColor = "#333")}
                onMouseOut={(e) => (e.currentTarget.style.backgroundColor = idx % 2 === 0 ? "#252525" : "#1e1e1e")}
              >
                <td style={{ padding: "8px", borderRight: "1px solid #333" }}>
                  {formatTime(row.t)}
                </td>
                <td style={{ padding: "8px", borderRight: "1px solid #333", fontWeight: "bold", color: "#00D9FF" }}>
                  {row.chosen_model}
                </td>
                <td
                  style={{
                    padding: "8px",
                    textAlign: "right",
                    borderRight: "1px solid #333",
                    color: getErrorRelColor(row.error_rel),
                    fontWeight: Math.abs(row.error_rel) > 50 ? "bold" : "normal",
                  }}
                >
                  {formatErrorRel(row.error_rel)}
                </td>
                <td
                  style={{
                    padding: "8px",
                    textAlign: "right",
                    borderRight: "1px solid #333",
                    color: row.error_abs != null ? "#FFD93D" : "#999",
                  }}
                >
                  {row.error_abs != null ? row.error_abs.toFixed(4) : "—"}
                </td>
                <td style={{ padding: "8px", textAlign: "right", borderRight: "1px solid #333" }}>
                  {row.y_real != null ? row.y_real.toFixed(2) : "—"}
                </td>
                <td style={{ padding: "8px", textAlign: "right" }}>
                  {row.y_pred != null ? row.y_pred.toFixed(2) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
