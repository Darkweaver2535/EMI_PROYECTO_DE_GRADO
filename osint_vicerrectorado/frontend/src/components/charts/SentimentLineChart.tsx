/**
 * Componente SentimentLineChart
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Box, Typography, Paper, useTheme } from '@mui/material';
import { SentimentData } from '../../types';
import { SENTIMENT_COLORS, LINE_CHART_CONFIG } from '../../utils';
import { formatDateDisplay } from '../../utils';

interface SentimentLineChartProps {
  data: SentimentData[];
  title?: string;
  height?: number;
  showLegend?: boolean;
  id?: string;
}

const SentimentLineChart: React.FC<SentimentLineChartProps> = ({
  data,
  title = 'Tendencia de Sentimientos',
  height = 350,
  showLegend = true,
  id = 'sentiment-line-chart',
}) => {
  const theme = useTheme();

  const formatXAxis = (value: string) => {
    return formatDateDisplay(value, 'short');
  };

  const formatTooltipValue = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Paper
          elevation={3}
          sx={{
            p: 1.5,
            backgroundColor: theme.palette.background.paper,
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            {formatDateDisplay(label)}
          </Typography>
          {payload.map((entry: any, index: number) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                mt: 0.5,
              }}
            >
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: entry.color,
                }}
              />
              <Typography variant="body2">
                {entry.name}: {formatTooltipValue(entry.value)}
              </Typography>
            </Box>
          ))}
        </Paper>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
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
        <LineChart
          data={data}
          margin={LINE_CHART_CONFIG.margin}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={theme.palette.divider}
          />
          <XAxis
            dataKey="date"
            tickFormatter={formatXAxis}
            tick={{ fontSize: 12 }}
            stroke={theme.palette.text.secondary}
          />
          <YAxis
            tickFormatter={(value) => `${value}%`}
            tick={{ fontSize: 12 }}
            stroke={theme.palette.text.secondary}
            domain={[0, 100]}
          />
          <Tooltip content={<CustomTooltip />} />
          {showLegend && (
            <Legend
              wrapperStyle={{ paddingTop: 16 }}
              formatter={(value) => (
                <span style={{ color: theme.palette.text.primary }}>
                  {value}
                </span>
              )}
            />
          )}
          <Line
            type="monotone"
            dataKey="positive"
            name="Positivo"
            stroke={SENTIMENT_COLORS.positive}
            strokeWidth={LINE_CHART_CONFIG.strokeWidth}
            dot={LINE_CHART_CONFIG.dot}
            activeDot={LINE_CHART_CONFIG.activeDot}
          />
          <Line
            type="monotone"
            dataKey="negative"
            name="Negativo"
            stroke={SENTIMENT_COLORS.negative}
            strokeWidth={LINE_CHART_CONFIG.strokeWidth}
            dot={LINE_CHART_CONFIG.dot}
            activeDot={LINE_CHART_CONFIG.activeDot}
          />
          <Line
            type="monotone"
            dataKey="neutral"
            name="Neutro"
            stroke={SENTIMENT_COLORS.neutral}
            strokeWidth={LINE_CHART_CONFIG.strokeWidth}
            dot={LINE_CHART_CONFIG.dot}
            activeDot={LINE_CHART_CONFIG.activeDot}
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default SentimentLineChart;
