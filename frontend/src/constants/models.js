/**
 * Constantes compartidas para modelos predictivos
 */

// Lista de modelos predictivos conocidos
export const KNOWN_MODELS = ["linear", "poly", "alphabeta", "kalman", "base", "hyper"];

// Colores para cada modelo (mantener consistencia en todos los gráficos)
export const MODEL_COLORS = {
  // Modelos principales
  linear: "#3b82f6",      // azul
  poly: "#10b981",        // verde esmeralda
  alphabeta: "#f59e0b",   // naranja/amber
  kalman: "#8b5cf6",      // violeta
  
  // Modelos baseline
  base: "#6b7280",        // gris (naive/persistencia)
  hyper: "#ec4899",       // rosa/magenta (media móvil)
  
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
  base: "Naive (Persistence)",
  hyper: "Moving Average",
  var: "Real Traffic",
  prediction: "Adaptive Ensemble",
};

// Colores por defecto (fallback)
export const DEFAULT_MODEL_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#6b7280", "#ec4899"];
