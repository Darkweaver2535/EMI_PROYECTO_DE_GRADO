/**
 * Componente RadarChart para perfiles de carreras
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Box, Typography, Paper, useTheme } from '@mui/material';
import { RadarProfileData } from '../../types';
import { CAREER_COLORS, RADAR_CHART_CONFIG } from '../../utils';

interface RadarChartProps {
  data: RadarProfileData | RadarProfileData[];
  title?: string;
  height?: number;
  showLegend?: boolean;
  id?: string;
}

interface ChartDataPoint {
  metric: string;
  [key: string]: string | number;
}

const RadarChart: React.FC<RadarChartProps> = ({
  data,
  title,
  height = 400,
  showLegend = true,
  id = 'radar-chart',
}) => {
  const theme = useTheme();

  // Normalizar data a array
  const profiles = Array.isArray(data) ? data : [data];

  if (profiles.length === 0) {
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

  // Transformar datos para Recharts
  const metricNames = Object.keys(profiles[0].metrics);
  const chartData: ChartDataPoint[] = metricNames.map(metric => {
    const point: ChartDataPoint = {
      metric: formatMetricName(metric),
    };
    profiles.forEach(profile => {
      point[profile.careerName] = profile.metrics[metric] || 0;
    });
    return point;
  });

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
            {label}
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
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: entry.color,
                }}
              />
              <Typography variant="body2">
                {entry.name}: {entry.value.toFixed(1)}
              </Typography>
            </Box>
          ))}
        </Paper>
      );
    }
    return null;
  };

  return (
    <Box id={id}>
      {title && (
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
          {title}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <RechartsRadarChart
          cx="50%"
          cy="50%"
          outerRadius={RADAR_CHART_CONFIG.outerRadius}
          data={chartData}
        >
          <PolarGrid stroke={theme.palette.divider} />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
          />
          {profiles.map((profile, index) => (
            <Radar
              key={profile.careerName}
              name={profile.careerName}
              dataKey={profile.careerName}
              stroke={CAREER_COLORS[index % CAREER_COLORS.length]}
              fill={CAREER_COLORS[index % CAREER_COLORS.length]}
              fillOpacity={RADAR_CHART_CONFIG.fillOpacity}
              strokeWidth={RADAR_CHART_CONFIG.strokeWidth}
            />
          ))}
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
        </RechartsRadarChart>
      </ResponsiveContainer>
    </Box>
  );
};

/**
 * Formatea nombre de métrica para visualización
 */
function formatMetricName(metric: string): string {
  const names: Record<string, string> = {
    sentiment: 'Sentimiento',
    mentions: 'Menciones',
    engagement: 'Engagement',
    reach: 'Alcance',
    visibility: 'Visibilidad',
    reputation: 'Reputación',
    growth: 'Crecimiento',
    satisfaction: 'Satisfacción',
  };
  return names[metric.toLowerCase()] || metric.charAt(0).toUpperCase() + metric.slice(1);
}

export default RadarChart;
