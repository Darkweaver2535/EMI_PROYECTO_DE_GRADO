/**
 * Componente CareerFilter
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useEffect, useState } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  CircularProgress,
  ListSubheader,
  TextField,
  InputAdornment,
  Box,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { Career } from '../../types';
import { benchmarkingService } from '../../services';

interface CareerFilterProps {
  value: string | 'all';
  onChange: (value: string | 'all') => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
  fullWidth?: boolean;
  multiple?: boolean;
}

interface GroupedCareers {
  [faculty: string]: Career[];
}

const CareerFilter: React.FC<CareerFilterProps> = ({
  value,
  onChange,
  disabled = false,
  size = 'small',
  fullWidth = false,
}) => {
  const [careers, setCareers] = useState<Career[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCareers = async () => {
      try {
        setLoading(true);
        const data = await benchmarkingService.getCareers();
        setCareers(data.map(c => ({ id: c.id, name: c.name, faculty: c.faculty })));
      } catch (err) {
        console.error('Error loading careers:', err);
        setError('Error al cargar carreras');
        // Datos de fallback
        setCareers([
          { id: 'ing-sistemas', name: 'Ingeniería de Sistemas', faculty: 'Ingeniería' },
          { id: 'ing-civil', name: 'Ingeniería Civil', faculty: 'Ingeniería' },
          { id: 'ing-comercial', name: 'Ingeniería Comercial', faculty: 'Ciencias Económicas' },
          { id: 'administracion', name: 'Administración de Empresas', faculty: 'Ciencias Económicas' },
          { id: 'derecho', name: 'Derecho', faculty: 'Ciencias Jurídicas' },
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadCareers();
  }, []);

  const handleChange = (event: SelectChangeEvent<string>) => {
    onChange(event.target.value as string | 'all');
  };

  // Agrupar carreras por facultad
  const groupedCareers: GroupedCareers = careers.reduce((acc, career) => {
    const faculty = career.faculty || 'Otras';
    if (!acc[faculty]) {
      acc[faculty] = [];
    }
    acc[faculty].push(career);
    return acc;
  }, {} as GroupedCareers);

  // Filtrar por búsqueda
  const filteredGrouped: GroupedCareers = Object.entries(groupedCareers).reduce(
    (acc, [faculty, facultyCareers]) => {
      const filtered = facultyCareers.filter(
        career =>
          career.name.toLowerCase().includes(searchText.toLowerCase()) ||
          faculty.toLowerCase().includes(searchText.toLowerCase())
      );
      if (filtered.length > 0) {
        acc[faculty] = filtered;
      }
      return acc;
    },
    {} as GroupedCareers
  );

  const selectedCareer = careers.find(c => c.id === value);

  return (
    <FormControl
      size={size}
      disabled={disabled || loading}
      sx={{ minWidth: 200 }}
      fullWidth={fullWidth}
    >
      <InputLabel id="career-filter-label">Carrera</InputLabel>
      <Select
        labelId="career-filter-label"
        id="career-filter"
        value={value}
        onChange={handleChange}
        label="Carrera"
        renderValue={(selected) => {
          if (selected === 'all') return 'Todas las carreras';
          return selectedCareer?.name || selected;
        }}
        MenuProps={{
          PaperProps: {
            style: { maxHeight: 400 },
          },
          autoFocus: false,
        }}
        onClose={() => setSearchText('')}
      >
        {/* Campo de búsqueda */}
        <ListSubheader sx={{ pt: 0 }}>
          <TextField
            size="small"
            autoFocus
            placeholder="Buscar carrera..."
            fullWidth
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            sx={{ mb: 1 }}
          />
        </ListSubheader>

        <MenuItem value="all">
          <em>Todas las carreras</em>
        </MenuItem>

        {loading ? (
          <MenuItem disabled>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={20} />
              Cargando carreras...
            </Box>
          </MenuItem>
        ) : error ? (
          <MenuItem disabled>
            <em>{error}</em>
          </MenuItem>
        ) : (
          Object.entries(filteredGrouped).map(([faculty, facultyCareers]) => [
            <ListSubheader key={faculty} sx={{ bgcolor: 'background.paper' }}>
              {faculty}
            </ListSubheader>,
            ...facultyCareers.map((career) => (
              <MenuItem key={career.id} value={career.id} sx={{ pl: 4 }}>
                {career.name}
              </MenuItem>
            )),
          ])
        )}
      </Select>
    </FormControl>
  );
};

export default CareerFilter;
