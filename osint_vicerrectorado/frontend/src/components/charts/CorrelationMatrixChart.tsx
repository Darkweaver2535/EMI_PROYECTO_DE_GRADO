/**
 * Componente CorrelationMatrixChart
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useMemo } from 'react';
import { Box, Typography, Tooltip, useTheme } from '@mui/material';
import { CorrelationMatrix } from '../../types';

interface CorrelationMatrixChartProps {
  data: CorrelationMatrix;
  title?: string;
  height?: number;
  id?: string;
}

const CorrelationMatrixChart: React.FC<CorrelationMatrixChartProps> = ({
  data,
  title = 'Matriz de Correlaciones',
  height = 400,
  id = 'correlation-matrix-chart',
}) => {
  const theme = useTheme();

  const { variables, values } = data;
  const n = variables.length;

  // Calcular color basado en correlación (-1 a 1)
  const getColor = (value: number): string => {
    if (value >= 0) {
      // Positivo: verde
      const intensity = Math.abs(value);
      const r = Math.round(200 - intensity * 169);
      const g = Math.round(230 - intensity * 105);
      const b = Math.round(201 - intensity * 169);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      // Negativo: rojo
      const intensity = Math.abs(value);
      const r = Math.round(255 - intensity * 44);
      const g = Math.round(205 - intensity * 158);
      const b = Math.round(210 - intensity * 163);
      return `rgb(${r}, ${g}, ${b})`;
    }
  };

  const cellSize = Math.min(50, (height - 100) / n);

  const formatValue = (value: number): string => {
    return value.toFixed(2);
  };

  if (!variables || variables.length === 0) {
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
          }}
        >
          {/* Header con nombres de variables */}
          <Box sx={{ display: 'flex', ml: `${cellSize * 2}px` }}>
            {variables.map((variable, i) => (
              <Box
                key={`header-${i}`}
                sx={{
                  width: cellSize,
                  height: cellSize * 1.5,
                  display: 'flex',
                  alignItems: 'flex-end',
                  justifyContent: 'center',
                  transform: 'rotate(-45deg)',
                  transformOrigin: 'center bottom',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontSize: '0.7rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: cellSize * 1.5,
                  }}
                >
                  {variable}
                </Typography>
              </Box>
            ))}
          </Box>

          {/* Matriz */}
          {variables.map((rowVariable, rowIndex) => (
            <Box
              key={`row-${rowIndex}`}
              sx={{
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {/* Label de fila */}
              <Box
                sx={{
                  width: cellSize * 2,
                  pr: 1,
                  textAlign: 'right',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontSize: '0.7rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: 'block',
                  }}
                >
                  {rowVariable}
                </Typography>
              </Box>

              {/* Celdas */}
              {variables.map((colVariable, colIndex) => {
                const value = values[rowIndex][colIndex];
                return (
                  <Tooltip
                    key={`cell-${rowIndex}-${colIndex}`}
                    title={`${rowVariable} vs ${colVariable}: ${formatValue(value)}`}
                    arrow
                    placement="top"
                  >
                    <Box
                      sx={{
                        width: cellSize,
                        height: cellSize,
                        backgroundColor: getColor(value),
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        border: `1px solid ${theme.palette.divider}`,
                        transition: 'transform 0.1s',
                        '&:hover': {
                          transform: 'scale(1.05)',
                          zIndex: 1,
                          boxShadow: theme.shadows[4],
                        },
                      }}
                    >
                      {cellSize >= 35 && (
                        <Typography
                          variant="caption"
                          sx={{
                            fontSize: '0.6rem',
                            fontWeight: 500,
                            color:
                              Math.abs(value) > 0.5
                                ? theme.palette.common.white
                                : theme.palette.text.primary,
                          }}
                        >
                          {formatValue(value)}
                        </Typography>
                      )}
                    </Box>
                  </Tooltip>
                );
              })}
            </Box>
          ))}

          {/* Leyenda */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mt: 3,
              gap: 1,
            }}
          >
            <Typography variant="caption" color="text.secondary">
              -1
            </Typography>
            {[-1, -0.5, 0, 0.5, 1].map((value) => (
              <Box
                key={value}
                sx={{
                  width: 30,
                  height: 16,
                  backgroundColor: getColor(value),
                  borderRadius: '2px',
                }}
              />
            ))}
            <Typography variant="caption" color="text.secondary">
              +1
            </Typography>
          </Box>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', textAlign: 'center', mt: 0.5 }}
          >
            Correlación negativa ← → Correlación positiva
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default CorrelationMatrixChart;
