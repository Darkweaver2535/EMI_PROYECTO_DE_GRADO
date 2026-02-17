/**
 * Componente EmptyState
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { SentimentDissatisfied as EmptyIcon } from '@mui/icons-material';

interface EmptyStateProps {
  title?: string;
  message?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'Sin datos',
  message = 'No hay datos disponibles para mostrar.',
  icon,
  action,
}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 300,
        py: 4,
        px: 2,
        textAlign: 'center',
      }}
    >
      <Box sx={{ color: 'text.secondary', mb: 2 }}>
        {icon || <EmptyIcon sx={{ fontSize: 64, opacity: 0.5 }} />}
      </Box>
      
      <Typography variant="h6" color="text.secondary" gutterBottom>
        {title}
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400 }}>
        {message}
      </Typography>
      
      {action && (
        <Button
          variant="outlined"
          onClick={action.onClick}
          sx={{ mt: 3 }}
        >
          {action.label}
        </Button>
      )}
    </Box>
  );
};

export default EmptyState;
