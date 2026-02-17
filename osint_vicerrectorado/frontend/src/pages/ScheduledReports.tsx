/**
 * Página ScheduledReports
 * Gestión de reportes programados
 * Sistema de Analítica OSINT - EMI Bolivia
 * Sprint 5: Reportes y Estadísticas
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Button,
  Chip,
  Switch,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Alert,
  Snackbar,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Collapse,
  Divider
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
  History as HistoryIcon,
  Schedule as ScheduleIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Email as EmailIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  PictureAsPdf as PdfIcon,
  TableChart as ExcelIcon
} from '@mui/icons-material';

// Componentes
import ScheduleForm from '../components/reports/ScheduleForm';

// Tipos y servicios
import { ReportSchedule, ExecutionLog, CreateScheduleRequest } from '../types/reports.types';
import reportsService, { formatFrequency, getReportTypeName } from '../services/reportsService';

// Colores EMI
const EMI_GREEN = '#1B5E20';
const EMI_GOLD = '#FFD700';

const ScheduledReports: React.FC = () => {
  // Estado de programaciones
  const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Estado del formulario
  const [formOpen, setFormOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ReportSchedule | null>(null);
  
  // Estado del diálogo de confirmación
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    schedule: ReportSchedule | null;
  }>({
    open: false,
    schedule: null
  });
  
  // Estado del historial expandido
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null);
  const [historyData, setHistoryData] = useState<Record<string, ExecutionLog[]>>({});
  const [loadingHistory, setLoadingHistory] = useState<string | null>(null);
  
  // Estado de notificaciones
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info'
  });

  // Cargar programaciones
  const loadSchedules = useCallback(async () => {
    try {
      setLoading(true);
      const response = await reportsService.getSchedules();
      if (response.success) {
        setSchedules(response.schedules);
      }
    } catch (error) {
      console.error('Error loading schedules:', error);
      showNotification('Error cargando programaciones', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  // Mostrar notificación
  const showNotification = (message: string, severity: 'success' | 'error' | 'info') => {
    setNotification({ open: true, message, severity });
  };

  // Abrir formulario para crear
  const handleCreateClick = () => {
    setEditingSchedule(null);
    setFormOpen(true);
  };

  // Abrir formulario para editar
  const handleEditClick = (schedule: ReportSchedule) => {
    setEditingSchedule(schedule);
    setFormOpen(true);
  };

  // Guardar programación
  const handleSaveSchedule = async (data: CreateScheduleRequest) => {
    try {
      let response;
      if (editingSchedule) {
        response = await reportsService.updateSchedule(editingSchedule.id, data);
      } else {
        response = await reportsService.createSchedule(data);
      }

      if (response.success) {
        showNotification(
          editingSchedule ? 'Programación actualizada' : 'Programación creada',
          'success'
        );
        setFormOpen(false);
        loadSchedules();
      } else {
        showNotification(response.error || 'Error guardando programación', 'error');
      }
    } catch (error) {
      showNotification('Error guardando programación', 'error');
    }
  };

  // Confirmar eliminación
  const handleDeleteClick = (schedule: ReportSchedule) => {
    setDeleteDialog({ open: true, schedule });
  };

  // Eliminar programación
  const handleDeleteConfirm = async () => {
    if (!deleteDialog.schedule) return;

    try {
      const response = await reportsService.deleteSchedule(deleteDialog.schedule.id);
      if (response.success) {
        showNotification('Programación eliminada', 'success');
        loadSchedules();
      } else {
        showNotification(response.error || 'Error eliminando programación', 'error');
      }
    } catch (error) {
      showNotification('Error eliminando programación', 'error');
    } finally {
      setDeleteDialog({ open: false, schedule: null });
    }
  };

  // Toggle habilitar/deshabilitar
  const handleToggleEnabled = async (schedule: ReportSchedule) => {
    try {
      const response = await reportsService.toggleSchedule(schedule.id);
      if (response.success) {
        showNotification(
          response.schedule?.enabled ? 'Programación habilitada' : 'Programación deshabilitada',
          'success'
        );
        loadSchedules();
      }
    } catch (error) {
      showNotification('Error cambiando estado', 'error');
    }
  };

  // Ejecutar ahora
  const handleRunNow = async (schedule: ReportSchedule) => {
    try {
      const response = await reportsService.runScheduleNow(schedule.id);
      if (response.success) {
        showNotification('Ejecución iniciada', 'info');
      } else {
        showNotification(response.error || 'Error ejecutando', 'error');
      }
    } catch (error) {
      showNotification('Error ejecutando', 'error');
    }
  };

  // Cargar historial de ejecución
  const handleToggleHistory = async (scheduleId: string) => {
    if (expandedHistory === scheduleId) {
      setExpandedHistory(null);
      return;
    }

    setExpandedHistory(scheduleId);

    if (!historyData[scheduleId]) {
      try {
        setLoadingHistory(scheduleId);
        const response = await reportsService.getScheduleHistory(scheduleId);
        if (response.success) {
          setHistoryData(prev => ({
            ...prev,
            [scheduleId]: response.history
          }));
        }
      } catch (error) {
        console.error('Error loading history:', error);
      } finally {
        setLoadingHistory(null);
      }
    }
  };

  // Renderizar historial de ejecuciones
  const renderExecutionHistory = (scheduleId: string) => {
    const history = historyData[scheduleId] || [];
    const isLoading = loadingHistory === scheduleId;

    return (
      <Collapse in={expandedHistory === scheduleId}>
        <Box sx={{ p: 2, bgcolor: '#f5f5f5' }}>
          <Typography variant="subtitle2" gutterBottom>
            Últimas ejecuciones
          </Typography>
          
          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : history.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Sin ejecuciones registradas
            </Typography>
          ) : (
            <List dense>
              {history.slice(0, 5).map((log, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {log.status === 'success' ? (
                      <SuccessIcon color="success" fontSize="small" />
                    ) : (
                      <ErrorIcon color="error" fontSize="small" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={new Date(log.executed_at).toLocaleString('es-BO')}
                    secondary={log.status === 'success' ? log.report_file : log.error}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      </Collapse>
    );
  };

  // Obtener estadísticas de programaciones
  const getScheduleStats = () => {
    const total = schedules.length;
    const active = schedules.filter(s => s.enabled).length;
    const daily = schedules.filter(s => s.frequency === 'daily').length;
    const weekly = schedules.filter(s => s.frequency === 'weekly').length;
    const monthly = schedules.filter(s => s.frequency === 'monthly').length;
    
    return { total, active, daily, weekly, monthly };
  };

  const stats = getScheduleStats();

  return (
    <Box sx={{ bgcolor: '#f5f5f5', minHeight: '100vh', py: 4 }}>
      <Container maxWidth="xl">
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Box>
            <Typography variant="h4" sx={{ color: EMI_GREEN, fontWeight: 700, mb: 1 }}>
              🗓️ Reportes Programados
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Configure la generación automática de reportes
            </Typography>
          </Box>
          
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateClick}
            sx={{
              bgcolor: EMI_GREEN,
              '&:hover': { bgcolor: '#2e7d32' }
            }}
          >
            Nueva Programación
          </Button>
        </Box>

        {/* Estadísticas */}
        <Grid container spacing={2} sx={{ mb: 4 }}>
          <Grid item xs={6} sm={4} md={2.4}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" sx={{ color: EMI_GREEN, fontWeight: 700 }}>
                  {stats.total}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" sx={{ color: '#2e7d32', fontWeight: 700 }}>
                  {stats.active}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Activas
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" sx={{ color: '#1976d2', fontWeight: 700 }}>
                  {stats.daily}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Diarias
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" sx={{ color: '#ed6c02', fontWeight: 700 }}>
                  {stats.weekly}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Semanales
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={4} md={2.4}>
            <Card elevation={1}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" sx={{ color: '#9c27b0', fontWeight: 700 }}>
                  {stats.monthly}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Mensuales
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabla de programaciones */}
        <Paper elevation={2}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress />
            </Box>
          ) : schedules.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <ScheduleIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No hay programaciones configuradas
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Cree una programación para generar reportes automáticamente
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleCreateClick}
                sx={{ bgcolor: EMI_GREEN }}
              >
                Crear Primera Programación
              </Button>
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                    <TableCell sx={{ fontWeight: 600 }}>Nombre</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Tipo de Reporte</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Frecuencia</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Próxima Ejecución</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Destinatarios</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Estado</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="center">Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {schedules.map((schedule) => (
                    <React.Fragment key={schedule.id}>
                      <TableRow hover>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {schedule.report_type.includes('excel') ? (
                              <ExcelIcon color="success" fontSize="small" />
                            ) : (
                              <PdfIcon color="error" fontSize="small" />
                            )}
                            <Typography variant="body2" fontWeight={500}>
                              {schedule.name}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {getReportTypeName(schedule.report_type)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={formatFrequency(schedule)}
                            size="small"
                            variant="outlined"
                            color={
                              schedule.frequency === 'daily' ? 'primary' :
                              schedule.frequency === 'weekly' ? 'warning' : 'secondary'
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {schedule.next_run ? 
                              new Date(schedule.next_run).toLocaleString('es-BO') :
                              '-'
                            }
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <EmailIcon fontSize="small" color="action" />
                            <Typography variant="body2">
                              {schedule.recipients.length} destinatario(s)
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Switch
                            checked={schedule.enabled}
                            onChange={() => handleToggleEnabled(schedule)}
                            color="success"
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Tooltip title="Ejecutar ahora">
                            <IconButton
                              size="small"
                              onClick={() => handleRunNow(schedule)}
                              color="primary"
                            >
                              <PlayIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Ver historial">
                            <IconButton
                              size="small"
                              onClick={() => handleToggleHistory(schedule.id)}
                            >
                              {expandedHistory === schedule.id ? (
                                <ExpandLessIcon fontSize="small" />
                              ) : (
                                <ExpandMoreIcon fontSize="small" />
                              )}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Editar">
                            <IconButton
                              size="small"
                              onClick={() => handleEditClick(schedule)}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Eliminar">
                            <IconButton
                              size="small"
                              onClick={() => handleDeleteClick(schedule)}
                              color="error"
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell colSpan={7} sx={{ py: 0 }}>
                          {renderExecutionHistory(schedule.id)}
                        </TableCell>
                      </TableRow>
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>

        {/* Información adicional */}
        <Grid container spacing={3} sx={{ mt: 3 }}>
          <Grid item xs={12} md={6}>
            <Card elevation={1}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ color: EMI_GREEN }}>
                  ⚙️ Configuración de Frecuencias
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Box component="ul" sx={{ pl: 2, '& li': { mb: 1 } }}>
                  <li>
                    <strong>Diaria:</strong> Ejecuta todos los días a la hora configurada
                  </li>
                  <li>
                    <strong>Semanal:</strong> Ejecuta un día específico de la semana
                  </li>
                  <li>
                    <strong>Mensual:</strong> Ejecuta un día específico del mes
                  </li>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card elevation={1}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ color: EMI_GREEN }}>
                  📧 Distribución por Email
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Box component="ul" sx={{ pl: 2, '& li': { mb: 1 } }}>
                  <li>
                    Los reportes se envían automáticamente a los destinatarios configurados
                  </li>
                  <li>
                    Los archivos adjuntos tienen un límite de 10MB
                  </li>
                  <li>
                    Se realizan hasta 3 reintentos en caso de fallo
                  </li>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>

      {/* Formulario de programación */}
      <ScheduleForm
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditingSchedule(null);
        }}
        onSave={handleSaveSchedule}
        schedule={editingSchedule}
      />

      {/* Diálogo de confirmación de eliminación */}
      <Dialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, schedule: null })}
      >
        <DialogTitle>Confirmar Eliminación</DialogTitle>
        <DialogContent>
          <DialogContentText>
            ¿Está seguro de eliminar la programación "{deleteDialog.schedule?.name}"?
            Esta acción no se puede deshacer.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialog({ open: false, schedule: null })}>
            Cancelar
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Eliminar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Notificaciones */}
      <Snackbar
        open={notification.open}
        autoHideDuration={5000}
        onClose={() => setNotification(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setNotification(prev => ({ ...prev, open: false }))}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ScheduledReports;
