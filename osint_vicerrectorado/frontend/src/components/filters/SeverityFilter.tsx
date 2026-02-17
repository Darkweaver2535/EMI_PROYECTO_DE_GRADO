/**
 * Componente SeverityFilter
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Box,
  Chip,
} from '@mui/material';
import { AlertSeverity } from '../../types';

interface SeverityFilterProps {
  value: AlertSeverity | 'all';
  onChange: (value: AlertSeverity | 'all') => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
  fullWidth?: boolean;
}

interface SeverityOption {
  value: AlertSeverity | 'all';
  label: string;
  color: string;
  bgColor: string;
}

const severityOptions: SeverityOption[] = [
  { value: 'all', label: 'Todas las severidades', color: '#757575', bgColor: '#f5f5f5' },
  { value: 'critical', label: 'Crítica', color: '#d32f2f', bgColor: '#ffebee' },
  { value: 'high', label: 'Alta', color: '#f57c00', bgColor: '#fff3e0' },
  { value: 'medium', label: 'Media', color: '#fbc02d', bgColor: '#fffde7' },
  { value: 'low', label: 'Baja', color: '#388e3c', bgColor: '#e8f5e9' },
];

const SeverityFilter: React.FC<SeverityFilterProps> = ({
  value,
  onChange,
  disabled = false,
  size = 'small',
  fullWidth = false,
}) => {
  const handleChange = (event: SelectChangeEvent<string>) => {
    onChange(event.target.value as AlertSeverity | 'all');
  };

  const selectedOption = severityOptions.find(opt => opt.value === value);

  return (
    <FormControl
      size={size}
      disabled={disabled}
      sx={{ minWidth: 180 }}
      fullWidth={fullWidth}
    >
      <InputLabel id="severity-filter-label">Severidad</InputLabel>
      <Select
        labelId="severity-filter-label"
        id="severity-filter"
        value={value}
        onChange={handleChange}
        label="Severidad"
        renderValue={(selected) => (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedOption && selectedOption.value !== 'all' && (
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  backgroundColor: selectedOption.color,
                }}
              />
            )}
            {selectedOption?.label || selected}
          </Box>
        )}
      >
        {severityOptions.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {option.value !== 'all' && (
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: option.color,
                  }}
                />
              )}
              <span>{option.label}</span>
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

/**
 * Chip de severidad para mostrar en listas
 */
export const SeverityChip: React.FC<{ severity: AlertSeverity; size?: 'small' | 'medium' }> = ({
  severity,
  size = 'small',
}) => {
  const option = severityOptions.find(opt => opt.value === severity);
  
  if (!option) return null;

  return (
    <Chip
      label={option.label}
      size={size}
      sx={{
        backgroundColor: option.bgColor,
        color: option.color,
        fontWeight: 500,
        '& .MuiChip-label': {
          px: 1,
        },
      }}
    />
  );
};

export default SeverityFilter;
