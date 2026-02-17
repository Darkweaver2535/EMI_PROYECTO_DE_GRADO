/**
 * Componente ScheduleForm
 * Formulario para crear/editar programaciones de reportes
 * Sistema de Analítica OSINT - EMI Bolivia
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Grid,
  Chip,
  Alert,
  Switch,
  FormControlLabel,
  Divider,
  IconButton,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Save as SaveIcon,
  Close as CloseIcon,
  Add as AddIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';

import {
  ReportSchedule,
  CreateScheduleRequest,
  PDFReportType,
  ExcelReportType,
  ScheduleFrequency,
  PDF_REPORT_OPTIONS,
  EXCEL_REPORT_OPTIONS,
  FREQUENCY_OPTIONS,
  DAYS_OF_WEEK,
  CAREER_OPTIONS,
  SEMESTER_OPTIONS
} from '../../types/reports.types';
import reportsService from '../../services/reportsService';

// Colores EMI
const EMI_GREEN = '#1B5E20';

interface ScheduleFormProps {
  open: boolean;
  onClose: () => void;
  onSave: () => void;
  editSchedule?: ReportSchedule | null;
}

const ScheduleForm: React.FC<ScheduleFormProps> = ({
  open,
  onClose,
  onSave,
  editSchedule
}) => {
  const [formData, setFormData] = useState<CreateScheduleRequest>({
    name: '',
    report_type: 'executive',
    frequency: 'weekly',
    day_of_week: 0,
    day_of_month: 1,
    hour: 8,
    minute: 0,
    params: {},
    recipients: [],
    enabled: true
  });

  const [newEmail, setNewEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Determinar formato según tipo de reporte
  const isPDFReport = ['executive', 'alerts', 'statistical', 'career'].includes(formData.report_type);
  const reportOptions = isPDFReport ? PDF_REPORT_OPTIONS : EXCEL_REPORT_OPTIONS;

  // Cargar datos si estamos editando
  useEffect(() => {
    if (editSchedule) {
      setFormData({
        name: editSchedule.name,
        report_type: editSchedule.report_type,
        frequency: editSchedule.frequency,
        day_of_week: editSchedule.day_of_week,
        day_of_month: editSchedule.day_of_month,
        hour: editSchedule.hour,
        minute: editSchedule.minute,
        params: editSchedule.params,
        recipients: editSchedule.recipients,
        enabled: editSchedule.enabled
      });
    } else {
      // Reset form para nueva programación
      setFormData({
        name: '',
        report_type: 'executive',
        frequency: 'weekly',
        day_of_week: 0,
        day_of_month: 1,
        hour: 8,
        minute: 0,
        params: {},
        recipients: [],
        enabled: true
      });
    }
    setError(null);
  }, [editSchedule, open]);

  // Manejar cambios en el formulario
  const handleChange = (field: keyof CreateScheduleRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Limpiar parámetros al cambiar tipo de reporte
    if (field === 'report_type') {
      setFormData(prev => ({ ...prev, params: {} }));
    }
  };

  // Manejar cambios en parámetros
  const handleParamChange = (key: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      params: { ...prev.params, [key]: value }
    }));
  };

  // Agregar email
  const handleAddEmail = () => {
    if (!newEmail || !newEmail.includes('@')) {
      setError('Ingrese un email válido');
      return;
    }
    
    if (formData.recipients.includes(newEmail)) {
      setError('Este email ya está en la lista');
      return;
    }
    
    setFormData(prev => ({
      ...prev,
      recipients: [...prev.recipients, newEmail]
    }));
    setNewEmail('');
    setError(null);
  };

  // Eliminar email
  const handleRemoveEmail = (email: string) => {
    setFormData(prev => ({
      ...prev,
      recipients: prev.recipients.filter(e => e !== email)
    }));
  };

  // Validar formulario
  const validate = (): boolean => {
    if (!formData.name.trim()) {
      setError('El nombre es requerido');
      return false;
    }
    
    if (formData.recipients.length === 0) {
      setError('Debe agregar al menos un destinatario');
      return false;
    }
    
    if (formData.frequency === 'weekly' && formData.day_of_week === undefined) {
      setError('Seleccione el día de la semana');
      return false;
    }
    
    if (formData.frequency === 'monthly' && !formData.day_of_month) {
      setError('Seleccione el día del mes');
      return false;
    }
    
    return true;
  };

  // Guardar programación
  const handleSave = async () => {
    if (!validate()) return;
    
    setSaving(true);
    setError(null);
    
    try {
      if (editSchedule) {
        await reportsService.updateSchedule(editSchedule.id, formData);
      } else {
        await reportsService.createSchedule(formData);
      }
      
      onSave();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Error guardando programación');
    } finally {
      setSaving(false);
    }
  };

  // Renderizar campos de parámetros según tipo de reporte
  const renderParamsFields = () => {
    switch (formData.report_type) {
      case 'executive':
        return (
          <Alert severity="info" sx={{ mt: 2 }}>
            El reporte ejecutivo usará automáticamente los últimos 7 días como período.
          </Alert>
        );
        
      case 'alerts':
        return (
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Severidad</InputLabel>
                <Select
                  value={formData.params?.severity || 'all'}
                  onChange={(e) => handleParamChange('severity', e.target.value)}
                  label="Severidad"
                >
                  <MenuItem value="all">Todas</MenuItem>
                  <MenuItem value="critical">Solo Críticas</MenuItem>
                  <MenuItem value="high">Alta y Críticas</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                label="Últimos N días"
                type="number"
                value={formData.params?.days || 7}
                onChange={(e) => handleParamChange('days', parseInt(e.target.value))}
                inputProps={{ min: 1, max: 30 }}
              />
            </Grid>
          </Grid>
        );
        
      case 'statistical':
        return (
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Semestre</InputLabel>
                <Select
                  value={formData.params?.semester || ''}
                  onChange={(e) => handleParamChange('semester', e.target.value)}
                  label="Semestre"
                >
                  {SEMESTER_OPTIONS.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        );
        
      case 'career':
        return (
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Carrera</InputLabel>
                <Select
                  value={formData.params?.career_id || ''}
                  onChange={(e) => {
                    const career = CAREER_OPTIONS.find(c => c.id === e.target.value);
                    handleParamChange('career_id', e.target.value);
                    handleParamChange('career_name', career?.name || '');
                  }}
                  label="Carrera"
                >
                  {CAREER_OPTIONS.map(career => (
                    <MenuItem key={career.id} value={career.id}>{career.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        );
        
      case 'pivot_table':
        return (
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <FormControl fullWidth size="small">
                <InputLabel>Dimensión</InputLabel>
                <Select
                  value={formData.params?.dimension || 'career'}
                  onChange={(e) => handleParamChange('dimension', e.target.value)}
                  label="Dimensión"
                >
                  <MenuItem value="career">Por Carrera</MenuItem>
                  <MenuItem value="source">Por Fuente</MenuItem>
                  <MenuItem value="month">Por Mes</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        );
        
      default:
        return null;
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { maxHeight: '90vh' }
      }}
    >
      <DialogTitle sx={{ bgcolor: EMI_GREEN, color: 'white', display: 'flex', alignItems: 'center', gap: 1 }}>
        <ScheduleIcon />
        {editSchedule ? 'Editar Programación' : 'Nueva Programación'}
        <Box sx={{ flex: 1 }} />
        <IconButton size="small" onClick={onClose} sx={{ color: 'white' }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent dividers>
        <Grid container spacing={3}>
          {/* Información básica */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ color: EMI_GREEN, fontWeight: 600 }}>
              Información Básica
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={8}>
                <TextField
                  fullWidth
                  size="small"
                  label="Nombre de la programación"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Ej: Reporte Ejecutivo Semanal"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.enabled}
                      onChange={(e) => handleChange('enabled', e.target.checked)}
                      color="primary"
                    />
                  }
                  label="Habilitado"
                />
              </Grid>
            </Grid>
          </Grid>

          <Grid item xs={12}>
            <Divider />
          </Grid>

          {/* Tipo de reporte */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ color: EMI_GREEN, fontWeight: 600 }}>
              Tipo de Reporte
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Tipo de Reporte</InputLabel>
                  <Select
                    value={formData.report_type}
                    onChange={(e) => handleChange('report_type', e.target.value)}
                    label="Tipo de Reporte"
                  >
                    <MenuItem disabled>--- PDF ---</MenuItem>
                    {PDF_REPORT_OPTIONS.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.icon} {opt.label}
                      </MenuItem>
                    ))}
                    <MenuItem disabled>--- Excel ---</MenuItem>
                    {EXCEL_REPORT_OPTIONS.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.icon} {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
            
            {renderParamsFields()}
          </Grid>

          <Grid item xs={12}>
            <Divider />
          </Grid>

          {/* Programación */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ color: EMI_GREEN, fontWeight: 600 }}>
              Frecuencia y Horario
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth size="small">
                  <InputLabel>Frecuencia</InputLabel>
                  <Select
                    value={formData.frequency}
                    onChange={(e) => handleChange('frequency', e.target.value)}
                    label="Frecuencia"
                  >
                    {FREQUENCY_OPTIONS.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              {formData.frequency === 'weekly' && (
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Día de la Semana</InputLabel>
                    <Select
                      value={formData.day_of_week ?? 0}
                      onChange={(e) => handleChange('day_of_week', e.target.value)}
                      label="Día de la Semana"
                    >
                      {DAYS_OF_WEEK.map(day => (
                        <MenuItem key={day.value} value={day.value}>{day.label}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              )}
              
              {formData.frequency === 'monthly' && (
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Día del Mes"
                    type="number"
                    value={formData.day_of_month || 1}
                    onChange={(e) => handleChange('day_of_month', parseInt(e.target.value))}
                    inputProps={{ min: 1, max: 28 }}
                    helperText="1-28 para evitar problemas con meses cortos"
                  />
                </Grid>
              )}
              
              <Grid item xs={6} md={2}>
                <TextField
                  fullWidth
                  size="small"
                  label="Hora"
                  type="number"
                  value={formData.hour}
                  onChange={(e) => handleChange('hour', parseInt(e.target.value))}
                  inputProps={{ min: 0, max: 23 }}
                />
              </Grid>
              
              <Grid item xs={6} md={2}>
                <TextField
                  fullWidth
                  size="small"
                  label="Minuto"
                  type="number"
                  value={formData.minute || 0}
                  onChange={(e) => handleChange('minute', parseInt(e.target.value))}
                  inputProps={{ min: 0, max: 59 }}
                />
              </Grid>
            </Grid>
          </Grid>

          <Grid item xs={12}>
            <Divider />
          </Grid>

          {/* Destinatarios */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ color: EMI_GREEN, fontWeight: 600 }}>
              Destinatarios
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <TextField
                size="small"
                placeholder="email@ejemplo.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddEmail()}
                sx={{ flex: 1 }}
              />
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={handleAddEmail}
                sx={{ borderColor: EMI_GREEN, color: EMI_GREEN }}
              >
                Agregar
              </Button>
            </Box>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {formData.recipients.map(email => (
                <Chip
                  key={email}
                  label={email}
                  onDelete={() => handleRemoveEmail(email)}
                  color="primary"
                  variant="outlined"
                />
              ))}
              {formData.recipients.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  No hay destinatarios agregados
                </Typography>
              )}
            </Box>
          </Grid>
        </Grid>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
      </DialogContent>
      
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSave}
          disabled={saving}
          sx={{ bgcolor: EMI_GREEN, '&:hover': { bgcolor: '#0d3f14' } }}
        >
          {saving ? 'Guardando...' : 'Guardar'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ScheduleForm;
