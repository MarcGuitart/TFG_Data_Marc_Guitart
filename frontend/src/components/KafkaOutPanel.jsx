import React, { useEffect, useState } from 'react';

export default function KafkaOutPanel() {
  const [rows, setRows] = useState([]);

  // Evidencia de Hardcoded sin variable de entorno

  useEffect(() => {
    const fetchProcessed = async () => {
      try {
        const res = await fetch('http://localhost:8082/flush');
        const json = await res.json();
        setRows(json.data || []);
      } catch (error) {
        console.error('Error fetching processed data:', error);
      }
    };

    fetchProcessed();
    const interval = setInterval(fetchProcessed, 3000); // actualiza cada 3s
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h3>Kafka Out</h3>
      <pre className="scrollable">
        {rows.length === 0 ? (
          <p>No hay datos todavía.</p>
        ) : (
          rows.slice(-10).map((row, idx) => (
            <div key={idx}>{JSON.stringify(row, null, 2)}</div>
          ))
        )}
      </pre>
    </div>
  );
}
