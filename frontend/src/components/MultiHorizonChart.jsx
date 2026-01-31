import React from 'react';
import { ComposedChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const MultiHorizonChart = ({ horizonData = [], selectedHorizon = 1, avgConfidence = null, avgErrorRel = null }) => {
  if (!horizonData || horizonData.length === 0) {
    return (
      <div className="multi-horizon-container" style={{ padding: '20px', textAlign: 'center' }}>
        <p style={{ color: '#666' }}>No hay datos disponibles para este horizonte</p>
      </div>
    );
  }

  // Preparar datos para el gráfico
  const chartData = horizonData.map((point, index) => ({
    index: index,
    time: point.time_t_plus_h ? new Date(point.time_t_plus_h).toLocaleTimeString() : `T+${index}`,
    groundTruth: parseFloat(point.ground_truth_t_plus_h) || parseFloat(point.var),
    prediction: parseFloat(point.prediction_t) || parseFloat(point.prediction),
    confidence: parseFloat(point.confidence) || 0,
    errorRel: parseFloat(point.error_rel) || 0,
  }));

  // Función para obtener color según confianza
  const getConfidenceColor = (confidence) => {
    if (confidence >= 80) return '#4CAF50'; // Verde
    if (confidence >= 75) return '#FF9800'; // Naranja
    return '#F44336'; // Rojo
  };

  const confidenceColor = avgConfidence ? getConfidenceColor(avgConfidence) : '#999';
  const minutesAhead = selectedHorizon * 30; // Aproximado basado en ventanas de 30 min

  return (
    <div className="multi-horizon-container">
      {/* Encabezado */}
      <div style={{ marginBottom: '20px', textAlign: 'center' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '24px', fontWeight: 'bold' }}>
          T+{selectedHorizon} Pronóstico
        </h3>
        <p style={{ margin: '0', color: '#666', fontSize: '14px' }}>
          Predicción {minutesAhead} minutos en adelanto
        </p>
      </div>

      {/* Grid de estadísticas */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px',
      }}>
        <div style={{
          padding: '15px',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center',
          borderLeft: `4px solid ${confidenceColor}`,
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Confianza Media</div>
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: confidenceColor }}>
            {avgConfidence !== null ? avgConfidence.toFixed(1) : '--'}%
          </div>
        </div>

        <div style={{
          padding: '15px',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center',
          borderLeft: '4px solid #2196F3',
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Error Medio</div>
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#2196F3' }}>
            {avgErrorRel !== null ? avgErrorRel.toFixed(1) : '--'}%
          </div>
        </div>

        <div style={{
          padding: '15px',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px',
          textAlign: 'center',
          borderLeft: '4px solid #9C27B0',
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Predicciones</div>
          <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#9C27B0' }}>
            {horizonData.length}
          </div>
        </div>
      </div>

      {/* Gráfico principal */}
      <div style={{ marginBottom: '30px', backgroundColor: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <h4 style={{ margin: '0 0 15px 0', color: '#333' }}>Valores Reales vs Predicciones</h4>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
            <XAxis 
              dataKey="index" 
              type="number"
              tick={{ fontSize: 12 }}
            />
            <YAxis 
              label={{ value: 'Valor', angle: -90, position: 'insideLeft' }}
              tick={{ fontSize: 12 }}
            />
            <Tooltip 
              formatter={(value) => value.toFixed(4)}
              labelFormatter={(label) => `Punto ${label}`}
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '4px' }}
            />
            <Legend 
              verticalAlign="top"
              height={36}
              wrapperStyle={{ paddingBottom: '10px' }}
            />
            <Line 
              type="monotone" 
              dataKey="groundTruth" 
              stroke="#2196F3" 
              strokeWidth={2}
              name="Valor Real"
              dot={{ r: 3 }}
              isAnimationActive={true}
            />
            <Line 
              type="monotone" 
              dataKey="prediction" 
              stroke="#FF9800" 
              strokeWidth={2}
              strokeDasharray="5 5"
              name={`Predicción T+${selectedHorizon}`}
              dot={{ r: 3 }}
              isAnimationActive={true}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Detalles de las primeras 20 predicciones */}
      {chartData.length > 0 && (
        <div style={{ marginBottom: '30px', backgroundColor: '#fff', padding: '15px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h4 style={{ margin: '0 0 15px 0', color: '#333' }}>Detalles de Predicciones (Primeras 20)</h4>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
            gap: '10px',
            maxHeight: '500px',
            overflowY: 'auto',
          }}>
            {chartData.slice(0, 20).map((point, idx) => (
              <div 
                key={idx}
                style={{
                  padding: '10px',
                  backgroundColor: '#f9f9f9',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>Punto {point.index}</div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ color: '#666' }}>Tiempo:</span> {point.time}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ color: '#666' }}>Real:</span> {point.groundTruth.toFixed(4)}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ color: '#666' }}>Predicción:</span> {point.prediction.toFixed(4)}
                </div>
                <div style={{ marginBottom: '3px' }}>
                  <span style={{ color: '#666' }}>Confianza:</span> 
                  <span style={{ 
                    color: getConfidenceColor(point.confidence),
                    fontWeight: 'bold',
                    marginLeft: '5px'
                  }}>
                    {point.confidence.toFixed(1)}%
                  </span>
                </div>
                <div>
                  <span style={{ color: '#666' }}>Error:</span> 
                  <span style={{ color: '#F44336', fontWeight: 'bold', marginLeft: '5px' }}>
                    {point.errorRel.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Explicación educativa */}
      <div style={{
        backgroundColor: '#E8F5E9',
        padding: '15px',
        borderRadius: '8px',
        borderLeft: '4px solid #4CAF50',
        fontSize: '13px',
        color: '#2E7D32',
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>ℹ️ Cómo interpretar este gráfico:</div>
        <ul style={{ margin: '0', paddingLeft: '20px' }}>
          <li>La línea azul sólida muestra los <strong>valores reales</strong> en el momento T+{selectedHorizon}</li>
          <li>La línea naranja punteada muestra nuestras <strong>predicciones</strong> para T+{selectedHorizon}</li>
          <li>La <strong>confianza</strong> (verde ≥80%, naranja 75-80%, rojo &lt;75%) indica qué tan seguro está el modelo</li>
          <li>El <strong>error</strong> es la diferencia porcentual entre el valor real y predicho</li>
          <li>Cada punto representa una predicción independiente hecha en un momento anterior</li>
        </ul>
      </div>
    </div>
  );
};

export default MultiHorizonChart;
