import React, { useState } from "react";
import KafkaInUploader from "./KafkaInUploader";
import CsvChart from "./CsvChart"; 

export default function KafkaInPanel() {
  const [csvData, setCsvData] = useState([]);

  return (
    <div>
      <h3>Kafka In</h3>
      <KafkaInUploader onDataLoaded={setCsvData} />
      {csvData.length === 0 ? (
        <p style={{ color: "white" }}>No hay datos cargados.</p>
      ) : (
        <>
          <CsvChart data={csvData} />
          <table style={{ color: "white", fontSize: "14px" }}>
            <thead>
              <tr>
                {Object.keys(csvData[0]).map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {csvData.map((row, idx) => (
                <tr key={idx}>
                  {Object.values(row).map((val, i) => (
                    <td key={i}>{val}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
