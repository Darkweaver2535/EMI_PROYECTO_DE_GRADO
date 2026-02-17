/**
 * Componente CareerBarChart
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Box, Typography, Paper, useTheme } from '@mui/material';
import { CareerRanking } from '../../types';
import { CAREER_COLORS, BAR_CHART_CONFIG } from '../../utils';

interface CareerBarChartProps {
  data: CareerRanking[];
  title?: string;
  height?: number;
  metric?: 'mentions' | 'sentiment' | 'engagement';
  horizontal?: boolean;
  showLegend?: boolean;
  id?: string;
}

const CareerBarChart: React.FC<CareerBarChartProps> = ({
  data,
  title,
  height = 400,
  metric = 'mentions',
  horizontal = false,
  showLegend = false,
  id = 'career-bar-chart',
}) => {
  const theme = useTheme();

  const metricConfig = {
    mentions: {
      dataKey: 'mentions',
      name: 'Menciones',
      color: theme.palette.primary.main,
      format: (value: number) => value.toLocaleString(),
    },
    sentiment: {
      dataKey: 'sentiment',
      name: 'Sentimiento',
      color: theme.palette.success.main,
      format: (value: number) => `${(value * 100).toFixed(1)}%`,
    },
    engagement: {
      dataKey: 'engagement',
      name: 'Engagement',
      color: theme.palette.info.main,
      format: (value: number) => value.toLocaleString(),
    },
  };

  const config = metricConfig[metric];

  const CustomTooltip = ({ active, payload, label }: any) => {
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
          <Typography variant="subtitle2" gutterBottom>
            {item.careerName}
          </Typography>
          <Typography variant="body2">
            {config.name}: {config.format(payload[0].value)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Ranking: #{item.rank}
          </Typography>
        </Paper>
      );
    }
    return null;
  };

  const getBarColor = (index: number) => {
    return CAREER_COLORS[index % CAREER_COLORS.length];
  };

  // Formatear nombre de carrera para el eje
  const formatCareerName = (name: string) => {
    if (name.length > 20) {
      return name.substring(0, 20) + '...';
    }
    return name;
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

  // Preparar datos con nombres formateados
  const chartData = data.map((item, index) => ({
    ...item,
    displayName: formatCareerName(item.careerName),
    rank: index + 1,
  }));

  return (
    <Box id={id}>
      {title && (
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
          {title}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          layout={horizontal ? 'vertical' : 'horizontal'}
          margin={BAR_CHART_CONFIG.margin}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={theme.palette.divider}
          />
          {horizontal ? (
            <>
              <XAxis
                type="number"
                tick={{ fontSize: 12 }}
                stroke={theme.palette.text.secondary}
              />
              <YAxis
                type="category"
                dataKey="displayName"
                tick={{ fontSize: 11 }}
                width={120}
                stroke={theme.palette.text.secondary}
              />
            </>
          ) : (
            <>
              <XAxis
                dataKey="displayName"
                tick={{ fontSize: 11, angle: -45, textAnchor: 'end' }}
                height={80}
                stroke={theme.palette.text.secondary}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                stroke={theme.palette.text.secondary}
              />
            </>
          )}
          <Tooltip content={<CustomTooltip />} />
          {showLegend && <Legend />}
          <Bar
            dataKey={config.dataKey}
            name={config.name}
            radius={BAR_CHART_CONFIG.barRadius as [number, number, number, number]}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default CareerBarChart;
