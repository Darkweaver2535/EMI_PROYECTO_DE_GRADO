/**
 * Componente ReportBuilder
 * Formulario para configurar y generar reportes
 * Sistema de Analítica OSINT - EMI Bolivia
 */

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Paper,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  PictureAsPdf as PdfIcon,
  TableChart as ExcelIcon,
  Send as SendIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { es } from 'date-fns/locale';
import { format, subDays, startOfMonth, endOfMonth } from 'date-fns';

import {
  PDFReportType,
  ExcelReportType,
  ReportParams,
  PDF_REPORT_OPTIONS,
  EXCEL_REPORT_OPTIONS,
  CAREER_OPTIONS,
  SEMESTER_OPTIONS,
  ReportOption
} from '../../types/reports.types';
import reportsService from '../../services/reportsService';

// Colores EMI
const EMI_GREEN = '#1B5E20';
const EMI_GOLD = '#FFD700';

interface ReportBuilderProps {
  onReportGenerated?: (taskId: string, reportType: string) => void;
  onError?: (error: string) => void;
}

const ReportBuilder: React.FC<ReportBuilderProps> = ({ onReportGenerated, onError }) => {
  // Estado del formulario
  const [reportFormat, setReportFormat] = useState<'pdf' | 'excel'>('pdf');
  const [selectedReport, setSelectedReport] = useState<string>('');
  const [params, setParams] = useState<ReportParams>({});
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Opciones según formato
  const reportOptions = reportFormat === 'pdf' ? PDF_REPORT_OPTIONS : EXCEL_REPORT_OPTIONS;

  // Obtener configuración del reporte seleccionado
  const selectedReportConfig = reportOptions.find(opt => opt.value === selectedReport);

  // Secciones disponibles para reportes ejecutivos
  const executiveSections = [
    { key: 'summary', label: 'Resumen Ejecutivo' },
    { key: 'sentiment', label: 'Análisis de Sentimiento' },
    { key: 'alerts', label: 'Alertas Críticas' },
    { key: 'complaints', label: 'Top Quejas' },
    { key: 'trends', label: 'Tendencias por Carrera' },
    { key: 'recommendations', label: 'Recomendaciones' }
  ];

  // Manejar cambio de formato
  const handleFormatChange = (format: 'pdf' | 'excel') => {
    setReportFormat(format);
    setSelectedReport('');
    setParams({});
    setError(null);
    setSuccess(null);
  };

  // Manejar cambio de tipo de reporte
  const handleReportTypeChange = (reportType: string) => {
    setSelectedReport(reportType);
    
    // Configurar parámetros por defecto según tipo
    const defaultParams: ReportParams = {};
    
    if (reportType === 'executive') {
      defaultParams.start_date = format(subDays(new Date(), 7), 'yyyy-MM-dd');
      defaultParams.end_date = format(new Date(), 'yyyy-MM-dd');
      defaultParams.sections = ['summary', 'sentiment', 'alerts', 'complaints', 'trends', 'recommendations'];
    } else if (reportType === 'alerts') {
      defaultParams.severity = 'all';
      defaultParams.days = 7;
    } else if (reportType === 'career') {
      defaultParams.start_date = format(startOfMonth(new Date()), 'yyyy-MM-dd');
      defaultParams.end_date = format(endOfMonth(new Date()), 'yyyy-MM-dd');
    } else if (reportType === 'anomalies') {
      defaultParams.days = 30;
      defaultParams.threshold = 2.0;
    }
    
    setParams(defaultParams);
    setError(null);
    setSuccess(null);
  };

  // Manejar cambio de parámetros
  const handleParamChange = (key: string, value: any) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  // Manejar cambio de secciones
  const handleSectionToggle = (section: string) => {
    const currentSections = params.sections || [];
    const newSections = currentSections.includes(section)
      ? currentSections.filter(s => s !== section)
      : [...currentSections, section];
    handleParamChange('sections', newSections);
  };

  // Validar formulario
  const validateForm = (): boolean => {
    if (!selectedReport) {
      setError('Seleccione un tipo de reporte');
      return false;
    }

    const config = selectedReportConfig;
    if (!config) return false;

    for (const param of config.requiredParams) {
      if (!params[param as keyof ReportParams]) {
        setError(`El campo ${param} es requerido`);
        return false;
      }
    }

    return true;
  };

  // Generar reporte
  const handleGenerate = async () => {
    if (!validateForm()) return;

    setIsGenerating(true);
    setError(null);
    setSuccess(null);

    try {
      let response;
      
      if (reportFormat === 'pdf') {
        response = await reportsService.generatePDFReport(
          selectedReport as PDFReportType,
          params
        );
      } else {
        response = await reportsService.generateExcelReport(
          selectedReport as ExcelReportType,
          params
        );
      }

      if (response.success && response.task_id) {
        setSuccess(`Generación iniciada. ID de tarea: ${response.task_id}`);
        if (onReportGenerated) {
          onReportGenerated(response.task_id, selectedReport);
        }
      } else {
        throw new Error(response.error || 'Error desconocido');
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'Error generando reporte';
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  // Renderizar campos según tipo de reporte
  const renderReportFields = () => {
    if (!selectedReport) return null;

    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="subtitle2" gutterBottom sx={{ color: EMI_GREEN, fontWeight: 600 }}>
          Configuración del Reporte
        </Typography>

        <Grid container spacing={2}>
          {/* Campos para Reporte Ejecutivo */}
          {selectedReport === 'executive' && (
            <>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
                  <DatePicker
                    label="Fecha Inicio"
                    value={params.start_date ? new Date(params.start_date) : null}
                    onChange={(date) => handleParamChange('start_date', date ? format(date, 'yyyy-MM-dd') : '')}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
                  <DatePicker
                    label="Fecha Fin"
                    value={params.end_date ? new Date(params.end_date) : null}
                    onChange={(date) => handleParamChange('end_date', date ? format(date, 'yyyy-MM-dd') : '')}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12}>
                <Typography variant="body2" gutterBottom>Secciones a incluir:</Typography>
                <FormGroup row>
                  {executiveSections.map(section => (
                    <FormControlLabel
                      key={section.key}
                      control={
                        <Checkbox
                          checked={params.sections?.includes(section.key) || false}
                          onChange={() => handleSectionToggle(section.key)}
                          size="small"
                        />
                      }
                      label={section.label}
                    />
                  ))}
                </FormGroup>
              </Grid>
            </>
          )}

          {/* Campos para Reporte de Alertas */}
          {selectedReport === 'alerts' && (
            <>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Severidad</InputLabel>
                  <Select
                    value={params.severity || 'all'}
                    onChange={(e) => handleParamChange('severity', e.target.value)}
                    label="Severidad"
                  >
                    <MenuItem value="all">Todas</MenuItem>
                    <MenuItem value="critical">Solo Críticas</MenuItem>
                    <MenuItem value="high">Alta y Críticas</MenuItem>
                    <MenuItem value="medium">Media y superiores</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Últimos N días"
                  type="number"
                  value={params.days || 7}
                  onChange={(e) => handleParamChange('days', parseInt(e.target.value))}
                  inputProps={{ min: 1, max: 90 }}
                />
              </Grid>
            </>
          )}

          {/* Campos para Anuario Estadístico */}
          {selectedReport === 'statistical' && (
            <Grid item xs={12} md={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Semestre</InputLabel>
                <Select
                  value={params.semester || ''}
                  onChange={(e) => handleParamChange('semester', e.target.value)}
                  label="Semestre"
                >
                  {SEMESTER_OPTIONS.map(opt => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          )}

          {/* Campos para Reporte por Carrera */}
          {selectedReport === 'career' && (
            <>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Carrera</InputLabel>
                  <Select
                    value={params.career_id || ''}
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
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
                  <DatePicker
                    label="Fecha Inicio"
                    value={params.start_date ? new Date(params.start_date) : null}
                    onChange={(date) => handleParamChange('start_date', date ? format(date, 'yyyy-MM-dd') : '')}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
                  <DatePicker
                    label="Fecha Fin"
                    value={params.end_date ? new Date(params.end_date) : null}
                    onChange={(date) => handleParamChange('end_date', date ? format(date, 'yyyy-MM-dd') : '')}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                  />
                </LocalizationProvider>
              </Grid>
            </>
          )}

          {/* Campos para Tabla Pivote */}
          {selectedReport === 'pivot_table' && (
            <Grid item xs={12} md={6}>
              <FormControl fullWidth size="small">
                <InputLabel>Dimensión</InputLabel>
                <Select
                  value={params.dimension || ''}
                  onChange={(e) => handleParamChange('dimension', e.target.value)}
                  label="Dimensión"
                >
                  <MenuItem value="career">Por Carrera</MenuItem>
                  <MenuItem value="source">Por Fuente</MenuItem>
                  <MenuItem value="month">Por Mes</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          )}

          {/* Campos para Reporte de Anomalías */}
          {selectedReport === 'anomalies' && (
            <>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Últimos N días"
                  type="number"
                  value={params.days || 30}
                  onChange={(e) => handleParamChange('days', parseInt(e.target.value))}
                  inputProps={{ min: 7, max: 180 }}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  label="Umbral de detección"
                  type="number"
                  value={params.threshold || 2.0}
                  onChange={(e) => handleParamChange('threshold', parseFloat(e.target.value))}
                  inputProps={{ min: 1, max: 5, step: 0.5 }}
                  helperText="Desviaciones estándar"
                />
              </Grid>
            </>
          )}

          {/* Campos para Dataset de Sentimientos */}
          {selectedReport === 'sentiment_dataset' && (
            <>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
                  <DatePicker
                    label="Fecha Inicio (opcional)"
                    value={params.start_date ? new Date(params.start_date) : null}
                    onChange={(date) => handleParamChange('start_date', date ? format(date, 'yyyy-MM-dd') : '')}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                  />
                </LocalizationProvider>
              </Grid>
              <Grid item xs={12} md={6}>
                <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={es}>
                  <DatePicker
                    label="Fecha Fin (opcional)"
                    value={params.end_date ? new Date(params.end_date) : null}
                    onChange={(date) => handleParamChange('end_date', date ? format(date, 'yyyy-MM-dd') : '')}
                    slotProps={{ textField: { fullWidth: true, size: 'small' } }}
                  />
                </LocalizationProvider>
              </Grid>
            </>
          )}
        </Grid>
      </Box>
    );
  };

  return (
    <Card elevation={2}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ color: EMI_GREEN, fontWeight: 600 }}>
          🛠️ Generador de Reportes
        </Typography>

        {/* Selector de formato */}
        <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
          <Button
            variant={reportFormat === 'pdf' ? 'contained' : 'outlined'}
            startIcon={<PdfIcon />}
            onClick={() => handleFormatChange('pdf')}
            sx={{
              bgcolor: reportFormat === 'pdf' ? EMI_GREEN : 'transparent',
              color: reportFormat === 'pdf' ? 'white' : EMI_GREEN,
              borderColor: EMI_GREEN,
              '&:hover': {
                bgcolor: reportFormat === 'pdf' ? '#0d3f14' : 'rgba(27, 94, 32, 0.1)'
              }
            }}
          >
            PDF
          </Button>
          <Button
            variant={reportFormat === 'excel' ? 'contained' : 'outlined'}
            startIcon={<ExcelIcon />}
            onClick={() => handleFormatChange('excel')}
            sx={{
              bgcolor: reportFormat === 'excel' ? EMI_GREEN : 'transparent',
              color: reportFormat === 'excel' ? 'white' : EMI_GREEN,
              borderColor: EMI_GREEN,
              '&:hover': {
                bgcolor: reportFormat === 'excel' ? '#0d3f14' : 'rgba(27, 94, 32, 0.1)'
              }
            }}
          >
            Excel
          </Button>
        </Box>

        {/* Selector de tipo de reporte */}
        <Typography variant="subtitle2" gutterBottom sx={{ color: EMI_GREEN }}>
          Tipo de Reporte
        </Typography>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          {reportOptions.map((option) => (
            <Grid item xs={12} sm={6} md={3} key={option.value}>
              <Paper
                elevation={selectedReport === option.value ? 4 : 1}
                sx={{
                  p: 2,
                  cursor: 'pointer',
                  border: selectedReport === option.value ? `2px solid ${EMI_GREEN}` : '2px solid transparent',
                  bgcolor: selectedReport === option.value ? 'rgba(27, 94, 32, 0.05)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: EMI_GREEN,
                    bgcolor: 'rgba(27, 94, 32, 0.05)'
                  }
                }}
                onClick={() => handleReportTypeChange(option.value)}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="h5">{option.icon}</Typography>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    {option.label}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {option.description}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>

        {/* Campos del reporte */}
        {renderReportFields()}

        {/* Mensajes de error/éxito */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mt: 2 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}

        {/* Botón de generar */}
        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={isGenerating ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
            onClick={handleGenerate}
            disabled={isGenerating || !selectedReport}
            sx={{
              bgcolor: EMI_GREEN,
              '&:hover': { bgcolor: '#0d3f14' },
              '&:disabled': { bgcolor: '#ccc' }
            }}
          >
            {isGenerating ? 'Generando...' : 'Generar Reporte'}
          </Button>
          
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => {
              setSelectedReport('');
              setParams({});
              setError(null);
              setSuccess(null);
            }}
            sx={{ borderColor: EMI_GREEN, color: EMI_GREEN }}
          >
            Limpiar
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ReportBuilder;
