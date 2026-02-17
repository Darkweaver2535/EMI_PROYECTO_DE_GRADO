/**
 * Componente DateRangePicker
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Menu,
  MenuItem,
  Divider,
  Typography,
  useTheme,
} from '@mui/material';
import { DateRange as DateRangeIcon } from '@mui/icons-material';
import { formatDateForAPI, formatDateDisplay, getDefaultDateRange } from '../../utils';

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (startDate: string, endDate: string) => void;
  minDate?: string;
  maxDate?: string;
  disabled?: boolean;
}

interface PresetRange {
  label: string;
  days: number;
}

const presetRanges: PresetRange[] = [
  { label: 'Últimos 7 días', days: 7 },
  { label: 'Últimos 14 días', days: 14 },
  { label: 'Últimos 30 días', days: 30 },
  { label: 'Últimos 90 días', days: 90 },
  { label: 'Este mes', days: -1 },
  { label: 'Mes anterior', days: -2 },
];

const DateRangePicker: React.FC<DateRangePickerProps> = ({
  startDate,
  endDate,
  onChange,
  minDate,
  maxDate,
  disabled = false,
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [tempStartDate, setTempStartDate] = useState(startDate);
  const [tempEndDate, setTempEndDate] = useState(endDate);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
    setTempStartDate(startDate);
    setTempEndDate(endDate);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleApply = () => {
    onChange(tempStartDate, tempEndDate);
    handleClose();
  };

  const handlePresetSelect = (preset: PresetRange) => {
    const today = new Date();
    let start: Date | string;
    let end: Date | string = today;

    if (preset.days === -1) {
      // Este mes
      start = new Date(today.getFullYear(), today.getMonth(), 1);
      end = today;
    } else if (preset.days === -2) {
      // Mes anterior
      start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      end = new Date(today.getFullYear(), today.getMonth(), 0);
    } else {
      // Últimos N días
      const range = getDefaultDateRange(preset.days);
      start = range.startDate;
      end = range.endDate;
    }

    const formattedStart = formatDateForAPI(start);
    const formattedEnd = formatDateForAPI(end);
    
    setTempStartDate(formattedStart);
    setTempEndDate(formattedEnd);
    onChange(formattedStart, formattedEnd);
    handleClose();
  };

  const displayText = `${formatDateDisplay(startDate)} - ${formatDateDisplay(endDate)}`;

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<DateRangeIcon />}
        onClick={handleClick}
        disabled={disabled}
        sx={{
          minWidth: 240,
          justifyContent: 'flex-start',
          textTransform: 'none',
        }}
      >
        {displayText}
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        PaperProps={{
          sx: { width: 320, p: 2 },
        }}
      >
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Rangos predefinidos
        </Typography>
        
        {presetRanges.map((preset) => (
          <MenuItem
            key={preset.label}
            onClick={() => handlePresetSelect(preset)}
            sx={{ borderRadius: 1 }}
          >
            {preset.label}
          </MenuItem>
        ))}

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Rango personalizado
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Fecha inicio"
            type="date"
            value={tempStartDate}
            onChange={(e) => setTempStartDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            inputProps={{
              min: minDate,
              max: tempEndDate || maxDate,
            }}
            fullWidth
            size="small"
          />

          <TextField
            label="Fecha fin"
            type="date"
            value={tempEndDate}
            onChange={(e) => setTempEndDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            inputProps={{
              min: tempStartDate || minDate,
              max: maxDate,
            }}
            fullWidth
            size="small"
          />

          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
            <Button size="small" onClick={handleClose}>
              Cancelar
            </Button>
            <Button
              size="small"
              variant="contained"
              onClick={handleApply}
              disabled={!tempStartDate || !tempEndDate}
            >
              Aplicar
            </Button>
          </Box>
        </Box>
      </Menu>
    </>
  );
};

export default DateRangePicker;
