/**
 * Componente WordCloudChart
 * Sistema OSINT EMI - Sprint 4
 * Implementación personalizada compatible con React 18
 */

import React, { useMemo, useState } from 'react';
import { Box, Typography, Tooltip, useTheme, Fade } from '@mui/material';
import { WordCloudWord } from '../../types';

// Colores por defecto para las palabras
const defaultColors = ['#1B5E20', '#2E7D32', '#388E3C', '#43A047', '#4CAF50', '#66BB6A', '#81C784'];

interface WordCloudChartProps {
  data: WordCloudWord[];
  title?: string;
  height?: number;
  onWordClick?: (word: WordCloudWord) => void;
  colors?: string[];
  id?: string;
  maxWords?: number;
  minFontSize?: number;
  maxFontSize?: number;
}

const WordCloudChart: React.FC<WordCloudChartProps> = ({
  data,
  title,
  height = 350,
  onWordClick,
  colors = defaultColors,
  id = 'word-cloud-chart',
  maxWords = 50,
  minFontSize = 12,
  maxFontSize = 48,
}) => {
  const theme = useTheme();
  const [hoveredWord, setHoveredWord] = useState<string | null>(null);

  // Procesar y calcular tamaños de fuente
  const processedWords = useMemo(() => {
    if (!data || data.length === 0) return [];

    const filtered = data
      .filter(word => word.value > 0 && word.text.trim().length > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, maxWords);

    if (filtered.length === 0) return [];

    const maxValue = filtered[0].value;
    const minValue = filtered[filtered.length - 1].value;
    const valueRange = maxValue - minValue || 1;

    return filtered.map((word, index) => {
      // Calcular tamaño de fuente basado en el valor
      const normalizedValue = (word.value - minValue) / valueRange;
      const fontSize = minFontSize + normalizedValue * (maxFontSize - minFontSize);
      
      // Asignar color cíclicamente
      const color = colors[index % colors.length];
      
      // Calcular opacidad basada en el rank
      const opacity = 0.7 + (0.3 * (1 - index / filtered.length));

      return {
        ...word,
        fontSize: Math.round(fontSize),
        color,
        opacity,
      };
    });
  }, [data, maxWords, minFontSize, maxFontSize, colors]);

  // Mezclar palabras para una distribución más natural
  const shuffledWords = useMemo(() => {
    const words = [...processedWords];
    // Usar un algoritmo de mezcla determinista basado en el texto
    for (let i = words.length - 1; i > 0; i--) {
      const j = Math.floor((i * 0.7) % (i + 1));
      [words[i], words[j]] = [words[j], words[i]];
    }
    return words;
  }, [processedWords]);

  if (!data || data.length === 0 || processedWords.length === 0) {
    return (
      <Box
        id={id}
        data-testid="wordcloud-empty"
        sx={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: theme.palette.background.paper,
          borderRadius: 2,
        }}
      >
        <Typography color="text.secondary">
          No hay datos disponibles para la nube de palabras
        </Typography>
      </Box>
    );
  }

  return (
    <Box id={id} data-testid="wordcloud-container">
      {title && (
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
          {title}
        </Typography>
      )}
      <Box
        sx={{
          height,
          backgroundColor: theme.palette.background.paper,
          borderRadius: 2,
          overflow: 'hidden',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          alignContent: 'center',
          justifyContent: 'center',
          gap: 1,
          padding: 2,
        }}
      >
        {shuffledWords.map((word, index) => (
          <Tooltip
            key={`${word.text}-${index}`}
            title={`${word.text}: ${word.value} menciones`}
            arrow
            TransitionComponent={Fade}
            TransitionProps={{ timeout: 200 }}
          >
            <Box
              component="span"
              data-testid="wordcloud-word"
              onClick={() => onWordClick?.(word)}
              onMouseEnter={() => setHoveredWord(word.text)}
              onMouseLeave={() => setHoveredWord(null)}
              sx={{
                fontSize: word.fontSize,
                fontWeight: word.fontSize > 30 ? 700 : word.fontSize > 20 ? 600 : 500,
                fontFamily: 'Roboto, sans-serif',
                color: word.color,
                opacity: hoveredWord === word.text ? 1 : word.opacity,
                cursor: onWordClick ? 'pointer' : 'default',
                transition: 'all 0.2s ease',
                transform: hoveredWord === word.text ? 'scale(1.1)' : 'scale(1)',
                padding: '2px 4px',
                userSelect: 'none',
                '&:hover': {
                  transform: 'scale(1.1)',
                  opacity: 1,
                },
              }}
            >
              {word.text}
            </Box>
          </Tooltip>
        ))}
      </Box>
    </Box>
  );
};

export default WordCloudChart;
