/**
 * Configuraciones predeterminadas para gráficos
 * Sistema OSINT EMI - Sprint 4
 */

import { SENTIMENT_COLORS, CHART_COLORS } from './colorSchemes';

export const LINE_CHART_CONFIG = {
  margin: { top: 20, right: 30, left: 20, bottom: 20 },
  strokeWidth: 2,
  dotSize: 4,
  activeDotSize: 6,
  animationDuration: 500,
  grid: {
    strokeDasharray: '3 3',
    stroke: '#E0E0E0',
  },
  dot: { r: 4 },
  activeDot: { r: 6 },
};

export const BAR_CHART_CONFIG = {
  margin: { top: 20, right: 30, left: 20, bottom: 60 },
  barSize: 40,
  radius: [4, 4, 0, 0],
  barRadius: [4, 4, 0, 0],
  animationDuration: 500,
};

export const PIE_CHART_CONFIG = {
  innerRadius: 60,
  outerRadius: 100,
  paddingAngle: 2,
  cornerRadius: 4,
  labelLine: false,
  animationDuration: 500,
};

export const RADAR_CHART_CONFIG = {
  margin: { top: 20, right: 30, left: 20, bottom: 20 },
  outerRadius: 120,
  fill: '#1976D2',
  fillOpacity: 0.6,
  stroke: '#1976D2',
  strokeWidth: 2,
  animationDuration: 500,
};

export const TOOLTIP_CONFIG = {
  contentStyle: {
    backgroundColor: '#FFFFFF',
    border: '1px solid #E0E0E0',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
    padding: '12px',
  },
  itemStyle: {
    padding: '4px 0',
  },
  labelStyle: {
    fontWeight: 'bold' as const,
    marginBottom: '8px',
  },
};

export const LEGEND_CONFIG = {
  verticalAlign: 'bottom' as const,
  height: 36,
  iconType: 'circle' as const,
  iconSize: 10,
  formatter: (value: string) => {
    const labels: Record<string, string> = {
      positive: 'Positivo',
      negative: 'Negativo',
      neutral: 'Neutral',
    };
    return labels[value] || value;
  },
};

export const SENTIMENT_CHART_SERIES = [
  {
    dataKey: 'positive',
    name: 'Positivo',
    stroke: SENTIMENT_COLORS.positive,
    fill: SENTIMENT_COLORS.positive,
  },
  {
    dataKey: 'negative',
    name: 'Negativo',
    stroke: SENTIMENT_COLORS.negative,
    fill: SENTIMENT_COLORS.negative,
  },
  {
    dataKey: 'neutral',
    name: 'Neutral',
    stroke: SENTIMENT_COLORS.neutral,
    fill: SENTIMENT_COLORS.neutral,
  },
];

export const DEFAULT_AXIS_CONFIG = {
  xAxis: {
    tick: { fill: '#666666', fontSize: 12 },
    tickLine: { stroke: '#E0E0E0' },
    axisLine: { stroke: '#E0E0E0' },
  },
  yAxis: {
    tick: { fill: '#666666', fontSize: 12 },
    tickLine: { stroke: '#E0E0E0' },
    axisLine: { stroke: '#E0E0E0' },
    width: 60,
  },
};

export const RESPONSIVE_CONTAINER_CONFIG = {
  width: '100%',
  height: 300,
  minWidth: 300,
};

export const WORDCLOUD_CONFIG = {
  fontSizes: [14, 60] as [number, number],
  fontFamily: 'Roboto, sans-serif',
  fontWeight: 'bold' as const,
  padding: 2,
  rotations: 2,
  rotationAngles: [0, 0] as [number, number],
  spiral: 'archimedean' as const,
  transitionDuration: 500,
};

export const HEATMAP_CONFIG = {
  cellSize: 30,
  cellGap: 2,
  cellRadius: 4,
};

export const getChartColor = (index: number): string => {
  const colors = Object.values(CHART_COLORS);
  return colors[index % colors.length];
};

export const formatChartValue = (
  value: number,
  type: 'percent' | 'number' | 'currency' = 'number'
): string => {
  switch (type) {
    case 'percent':
      return `${value.toFixed(1)}%`;
    case 'currency':
      return `Bs. ${value.toLocaleString('es-BO')}`;
    default:
      return value.toLocaleString('es-BO');
  }
};

export const formatAxisTick = (value: unknown): string => {
  if (typeof value === 'number') {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  }
  return String(value);
};
