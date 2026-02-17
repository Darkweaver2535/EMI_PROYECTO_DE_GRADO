/**
 * Paletas de colores para gráficos
 * Sistema OSINT EMI - Sprint 4
 */

export const SENTIMENT_COLORS = {
  positive: '#4CAF50',
  negative: '#F44336',
  neutral: '#9E9E9E',
  positiveLight: '#81C784',
  negativeLight: '#E57373',
  neutralLight: '#BDBDBD',
};

export const ALERT_SEVERITY_COLORS = {
  critica: '#D32F2F',
  alta: '#F57C00',
  media: '#FBC02D',
  baja: '#388E3C',
};

export const ALERT_STATUS_COLORS = {
  nueva: '#2196F3',
  en_proceso: '#FF9800',
  resuelta: '#4CAF50',
  descartada: '#9E9E9E',
};

export const CHART_COLORS = {
  primary: '#1976D2',
  secondary: '#9C27B0',
  success: '#4CAF50',
  warning: '#FF9800',
  error: '#F44336',
  info: '#00BCD4',
};

export const CAREER_COLORS = [
  '#1976D2', // Azul
  '#388E3C', // Verde
  '#F57C00', // Naranja
  '#7B1FA2', // Púrpura
  '#00796B', // Teal
  '#C2185B', // Rosa
  '#5D4037', // Marrón
  '#455A64', // Gris azulado
];

export const COMPETITOR_COLORS: Record<string, string> = {
  'EMI': '#1976D2',
  'UMSA': '#F44336',
  'UCB': '#4CAF50',
  'UPSA': '#FF9800',
  'UNIVALLE': '#9C27B0',
};

export const HEATMAP_COLORS = {
  min: '#E3F2FD',
  low: '#90CAF9',
  medium: '#42A5F5',
  high: '#1976D2',
  max: '#0D47A1',
};

export const CORRELATION_COLORS = {
  strongPositive: '#1B5E20',
  positive: '#4CAF50',
  weakPositive: '#A5D6A7',
  neutral: '#FFFFFF',
  weakNegative: '#EF9A9A',
  negative: '#F44336',
  strongNegative: '#B71C1C',
};

export const getCorrelationColor = (value: number): string => {
  if (value >= 0.7) return CORRELATION_COLORS.strongPositive;
  if (value >= 0.4) return CORRELATION_COLORS.positive;
  if (value >= 0.2) return CORRELATION_COLORS.weakPositive;
  if (value >= -0.2) return CORRELATION_COLORS.neutral;
  if (value >= -0.4) return CORRELATION_COLORS.weakNegative;
  if (value >= -0.7) return CORRELATION_COLORS.negative;
  return CORRELATION_COLORS.strongNegative;
};

export const getHeatmapColor = (value: number, max: number): string => {
  const ratio = value / max;
  if (ratio >= 0.8) return HEATMAP_COLORS.max;
  if (ratio >= 0.6) return HEATMAP_COLORS.high;
  if (ratio >= 0.4) return HEATMAP_COLORS.medium;
  if (ratio >= 0.2) return HEATMAP_COLORS.low;
  return HEATMAP_COLORS.min;
};

export const getSentimentColor = (sentiment: string): string => {
  switch (sentiment.toLowerCase()) {
    case 'positivo':
    case 'positive':
      return SENTIMENT_COLORS.positive;
    case 'negativo':
    case 'negative':
      return SENTIMENT_COLORS.negative;
    default:
      return SENTIMENT_COLORS.neutral;
  }
};

export const getAlertSeverityColor = (severity: string): string => {
  return ALERT_SEVERITY_COLORS[severity as keyof typeof ALERT_SEVERITY_COLORS] || ALERT_SEVERITY_COLORS.baja;
};

export const THEME_COLORS = {
  light: {
    background: '#FAFAFA',
    paper: '#FFFFFF',
    text: {
      primary: '#212121',
      secondary: '#757575',
    },
    divider: '#E0E0E0',
  },
  dark: {
    background: '#121212',
    paper: '#1E1E1E',
    text: {
      primary: '#FFFFFF',
      secondary: '#B0B0B0',
    },
    divider: '#424242',
  },
};
