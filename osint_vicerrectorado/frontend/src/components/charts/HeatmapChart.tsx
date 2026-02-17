/**
 * Componente HeatmapChart
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useMemo } from 'react';
import { Box, Typography, useTheme, Tooltip } from '@mui/material';
import { HeatmapData } from '../../types';

interface HeatmapChartProps {
  data: HeatmapData[];
  title?: string;
  height?: number;
  id?: string;
}

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const HOURS = Array.from({ length: 24 }, (_, i) => 
  i.toString().padStart(2, '0') + ':00'
);

const HeatmapChart: React.FC<HeatmapChartProps> = ({
  data,
  title = 'Actividad por Día y Hora',
  height = 300,
  id = 'heatmap-chart',
}) => {
  const theme = useTheme();

  // Procesar datos para la matriz
  const { matrix, maxValue } = useMemo(() => {
    const mat: number[][] = Array.from({ length: 7 }, () =>
      Array.from({ length: 24 }, () => 0)
    );
    let max = 0;

    data.forEach((item) => {
      const dayIndex = item.day ?? -1;
      const hourIndex = item.hour ?? -1;
      const cellValue = item.value ?? 0;
      if (dayIndex >= 0 && dayIndex < 7 && hourIndex >= 0 && hourIndex < 24) {
        mat[dayIndex][hourIndex] = cellValue;
        if (cellValue > max) max = cellValue;
      }
    });

    return { matrix: mat, maxValue: max || 1 };
  }, [data]);

  // Calcular color basado en valor
  const getColor = (value: number): string => {
    const intensity = value / maxValue;
    const primaryColor = theme.palette.primary.main;
    
    if (intensity === 0) {
      return theme.palette.mode === 'dark' ? '#1e1e1e' : '#f5f5f5';
    }
    
    // Interpolar entre color claro y color primario
    const alpha = Math.min(0.1 + intensity * 0.9, 1);
    return `${primaryColor}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`;
  };

  const cellSize = 20;
  const labelWidth = 40;
  const labelHeight = 30;

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
      <Box
        sx={{
          overflowX: 'auto',
          pb: 2,
        }}
      >
        <Box
          sx={{
            display: 'inline-block',
            minWidth: labelWidth + 24 * cellSize + 20,
          }}
        >
          {/* Header con horas */}
          <Box sx={{ display: 'flex', ml: `${labelWidth}px`, mb: 0.5 }}>
            {HOURS.filter((_, i) => i % 2 === 0).map((hour, i) => (
              <Typography
                key={hour}
                variant="caption"
                sx={{
                  width: cellSize * 2,
                  textAlign: 'center',
                  fontSize: '0.65rem',
                  color: 'text.secondary',
                }}
              >
                {hour}
              </Typography>
            ))}
          </Box>

          {/* Filas del heatmap */}
          {DAYS.map((day, dayIndex) => (
            <Box
              key={day}
              sx={{
                display: 'flex',
                alignItems: 'center',
                mb: '2px',
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  width: labelWidth,
                  textAlign: 'right',
                  pr: 1,
                  fontSize: '0.75rem',
                  color: 'text.secondary',
                }}
              >
                {day}
              </Typography>
              <Box sx={{ display: 'flex', gap: '2px' }}>
                {matrix[dayIndex].map((value, hourIndex) => (
                  <Tooltip
                    key={`${dayIndex}-${hourIndex}`}
                    title={`${DAYS[dayIndex]} ${HOURS[hourIndex]}: ${value} menciones`}
                    arrow
                    placement="top"
                  >
                    <Box
                      sx={{
                        width: cellSize,
                        height: cellSize,
                        backgroundColor: getColor(value),
                        borderRadius: '2px',
                        cursor: 'pointer',
                        transition: 'transform 0.1s',
                        '&:hover': {
                          transform: 'scale(1.1)',
                          zIndex: 1,
                        },
                      }}
                    />
                  </Tooltip>
                ))}
              </Box>
            </Box>
          ))}

          {/* Leyenda */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              mt: 2,
              gap: 1,
            }}
          >
            <Typography variant="caption" color="text.secondary">
              Menos
            </Typography>
            {[0, 0.25, 0.5, 0.75, 1].map((intensity) => (
              <Box
                key={intensity}
                sx={{
                  width: 16,
                  height: 16,
                  backgroundColor: getColor(intensity * maxValue),
                  borderRadius: '2px',
                }}
              />
            ))}
            <Typography variant="caption" color="text.secondary">
              Más
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default HeatmapChart;
