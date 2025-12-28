/**
 * Constantes compartidas para modelos predictivos
 */

// Lista de modelos predictivos activos (5 modelos)
export const KNOWN_MODELS = ["linear", "poly", "alphabeta", "kalman", "base"];

// Todos los modelos incluidos en visualización
export const ALL_MODELS = KNOWN_MODELS;

// Colores para cada modelo (mantener consistencia en todos los gráficos)
export const MODEL_COLORS = {
  // Modelos principales
  linear: "#3b82f6",      // azul
  poly: "#10b981",        // verde esmeralda
  alphabeta: "#ffea00ff",   // naranja/amber
  kalman: "#412f69ff",    // violeta
  
  // Modelo baseline
  base: "#c22727ff",      // gris (naive/persistencia)
  
  // Predicción final y valor real
  var: "#00A3FF",         // azul claro (tráfico real)
  prediction: "#FF7A00",  // naranja (ensemble adaptativo)
};

// Nombres legibles para leyendas
export const MODEL_NAMES = {
  linear: "Linear Regression",
  poly: "Polynomial Regression",
  alphabeta: "Alpha-Beta Filter",
  kalman: "Kalman Filter",
  base: "Naive",
  var: "Real Traffic",
  prediction: "Adaptive Ensemble",
};

// Colores por defecto (fallback)
export const DEFAULT_MODEL_COLORS = ["#3b82f6", "#10b981", "#ffea00ff", "#412f69ff", "#c22727ff", "#ec4899"];
