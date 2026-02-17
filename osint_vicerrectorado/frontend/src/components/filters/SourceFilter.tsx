/**
 * Componente SourceFilter
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Chip,
  Box,
} from '@mui/material';
import { OSINTSource } from '../../types';

interface SourceFilterProps {
  value: OSINTSource | 'all';
  onChange: (value: OSINTSource | 'all') => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
  fullWidth?: boolean;
}

interface SourceOption {
  value: OSINTSource | 'all';
  label: string;
  color?: string;
}

const sourceOptions: SourceOption[] = [
  { value: 'all', label: 'Todas las fuentes' },
  { value: 'facebook', label: 'Facebook', color: '#1877F2' },
  { value: 'twitter', label: 'Twitter/X', color: '#1DA1F2' },
  { value: 'instagram', label: 'Instagram', color: '#E4405F' },
  { value: 'news', label: 'Noticias', color: '#FF6B6B' },
  { value: 'web', label: 'Web', color: '#4CAF50' },
  { value: 'forums', label: 'Foros', color: '#9C27B0' },
];

const SourceFilter: React.FC<SourceFilterProps> = ({
  value,
  onChange,
  disabled = false,
  size = 'small',
  fullWidth = false,
}) => {
  const handleChange = (event: SelectChangeEvent<string>) => {
    onChange(event.target.value as OSINTSource | 'all');
  };

  const selectedOption = sourceOptions.find(opt => opt.value === value);

  return (
    <FormControl
      size={size}
      disabled={disabled}
      sx={{ minWidth: 180 }}
      fullWidth={fullWidth}
    >
      <InputLabel id="source-filter-label">Fuente</InputLabel>
      <Select
        labelId="source-filter-label"
        id="source-filter"
        value={value}
        onChange={handleChange}
        label="Fuente"
        renderValue={(selected) => (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedOption?.color && (
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: selectedOption.color,
                }}
              />
            )}
            {selectedOption?.label || selected}
          </Box>
        )}
      >
        {sourceOptions.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {option.color && (
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    backgroundColor: option.color,
                  }}
                />
              )}
              {option.label}
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};

export default SourceFilter;
