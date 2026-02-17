/**
 * Componente SentimentPieChart
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Box, Typography, Paper, useTheme } from '@mui/material';
import { SentimentDistribution } from '../../types';
import { SENTIMENT_COLORS, PIE_CHART_CONFIG } from '../../utils';

interface SentimentPieChartProps {
  data: SentimentDistribution;
  title?: string;
  height?: number;
  showLegend?: boolean;
  showLabels?: boolean;
  id?: string;
}

interface ChartData {
  name: string;
  value: number;
  color: string;
  percentage: number;
}

const SentimentPieChart: React.FC<SentimentPieChartProps> = ({
  data,
  title,
  height = 300,
  showLegend = true,
  showLabels = true,
  id = 'sentiment-pie-chart',
}) => {
  const theme = useTheme();

  const total = data.positive + data.negative + data.neutral || 1;
  
  const chartData: ChartData[] = [
    {
      name: 'Positivo',
      value: data.positive,
      color: SENTIMENT_COLORS.positive,
      percentage: (data.positive / total) * 100,
    },
    {
      name: 'Negativo',
      value: data.negative,
      color: SENTIMENT_COLORS.negative,
      percentage: (data.negative / total) * 100,
    },
    {
      name: 'Neutro',
      value: data.neutral,
      color: SENTIMENT_COLORS.neutral,
      percentage: (data.neutral / total) * 100,
    },
  ].filter(item => item.value > 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <Paper
          elevation={3}
          sx={{
            p: 1.5,
            backgroundColor: theme.palette.background.paper,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                backgroundColor: item.color,
              }}
            />
            <Typography variant="subtitle2">{item.name}</Typography>
          </Box>
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            Cantidad: {item.value.toLocaleString()}
          </Typography>
          <Typography variant="body2">
            Porcentaje: {item.percentage.toFixed(1)}%
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  const renderCustomLabel = ({ name, percentage }: ChartData) => {
    if (percentage < 5) return null;
    return `${percentage.toFixed(0)}%`;
  };

  if (chartData.length === 0) {
    return (
      <Box
        id={id}
        sx={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Typography color="text.secondary">
          No hay datos disponibles
        </Typography>
      </Box>
    );
  }

  return (
    <Box id={id}>
      {title && (
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
          {title}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={PIE_CHART_CONFIG.innerRadius}
            outerRadius={PIE_CHART_CONFIG.outerRadius}
            paddingAngle={PIE_CHART_CONFIG.paddingAngle}
            dataKey="value"
            label={showLabels ? renderCustomLabel : false}
            labelLine={showLabels}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color}
                stroke={theme.palette.background.paper}
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          {showLegend && (
            <Legend
              formatter={(value) => (
                <span style={{ color: theme.palette.text.primary }}>
                  {value}
                </span>
              )}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default SentimentPieChart;
