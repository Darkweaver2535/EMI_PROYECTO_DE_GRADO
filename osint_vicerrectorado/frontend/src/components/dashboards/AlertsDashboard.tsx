/**
 * Dashboard de Alertas y Anomalías
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Alert as MuiAlert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Paper,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as ResolvedIcon,
  Visibility as ViewIcon,
  Done as DoneIcon,
  Refresh as RefreshIcon,
  NotificationsActive as AlertIcon,
} from '@mui/icons-material';
import {
  KPICard,
  LoadingSpinner,
  ExportButton,
  DateRangePicker,
  EmptyState,
} from '../common';
import { SeverityFilter, SeverityChip } from '../filters';
import { useFilters } from '../../contexts';
import { alertsService } from '../../services';
import api from '../../services/api';
import { Alert, AlertStats } from '../../types';
import { formatDateDisplay, formatTimeAgo } from '../../utils';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, Legend,
  ResponsiveContainer,
} from 'recharts';

interface ProblemStats {
  disponible: boolean;
  resumen?: { totalAnalizado: number; totalProblemas: number; tasaProblemas: number; criticos: number; temasAfectados: number };
  porTema?: { tema: string; problemas: number; negativos: number; quejas: number }[];
  porSeveridad?: { severidad: string; cantidad: number }[];
  porCarrera?: { careerId: string; careerName: string; problemas: number }[];
  tendencia?: { fecha: string; problemas: number }[];
  topProblemas?: { tema: string; severidad: string; resumen: string }[];
}

const SEV_COLORS: Record<string, string> = { critica: '#b91c1c', alta: '#ea580c', media: '#d97706', baja: '#64748b' };

const AlertsDashboard: React.FC = () => {
  const { filters, setDateRange, setSeverity, getApiParams } = useFilters();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalAlerts, setTotalAlerts] = useState(0);
  
  // Dialog state
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [resolveDialogOpen, setResolveDialogOpen] = useState(false);
  const [resolution, setResolution] = useState('');
  const [problemStats, setProblemStats] = useState<ProblemStats | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = getApiParams();

      const [alertsResponse, statsData, problemsResp] = await Promise.all([
        alertsService.getAlerts({
          ...params,
          page: page + 1,
          limit: rowsPerPage,
        }),
        alertsService.getAlertStats({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
        api.get<ProblemStats>('/ai/alerts/estadisticas-problemas').then(r => r.data).catch(() => null),
      ]);

      setAlerts(alertsResponse.alerts);
      setTotalAlerts(alertsResponse.total);
      setStats(statsData);
      setProblemStats(problemsResp);
    } catch (err) {
      console.error('Error loading alerts data:', err);
      setError('Error al cargar las alertas. Por favor, intente de nuevo.');
      
      // Datos de demostración
      setStats({
        total: 42,
        critical: 3,
        high: 8,
        medium: 15,
        low: 16,
        pending: 26,
        resolved: 16,
        lastHour: 2,
        last24Hours: 12,
      });
    } finally {
      setLoading(false);
    }
  }, [getApiParams, page, rowsPerPage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleViewAlert = (alert: Alert) => {
    setSelectedAlert(alert);
  };

  const handleOpenResolveDialog = (alert: Alert) => {
    setSelectedAlert(alert);
    setResolveDialogOpen(true);
    setResolution('');
  };

  const handleCloseResolveDialog = () => {
    setResolveDialogOpen(false);
    setSelectedAlert(null);
    setResolution('');
  };

  const handleResolveAlert = async () => {
    if (!selectedAlert || !resolution.trim()) return;

    try {
      await alertsService.resolveAlert({
        alertId: String(selectedAlert.id),
        resolution: resolution.trim(),
      });
      handleCloseResolveDialog();
      loadData(); // Recargar datos
    } catch (err) {
      console.error('Error resolving alert:', err);
    }
  };

  const getSeverityIcon = (severity?: string) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon sx={{ color: '#d32f2f' }} />;
      case 'high':
        return <WarningIcon sx={{ color: '#f57c00' }} />;
      case 'medium':
        return <WarningIcon sx={{ color: '#fbc02d' }} />;
      default:
        return <WarningIcon sx={{ color: '#388e3c' }} />;
    }
  };

  const getExportColumns = () => [
    { key: 'id', header: 'ID' },
    { key: 'title', header: 'Título' },
    { key: 'type', header: 'Tipo' },
    { key: 'severity', header: 'Severidad' },
    { key: 'status', header: 'Estado' },
    { key: 'createdAt', header: 'Fecha' },
  ];

  if (loading && alerts.length === 0) {
    return <LoadingSpinner message="Cargando alertas y anomalías..." />;
  }

  return (
    <Box id="alerts-dashboard">
      {/* Header y Filtros */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          justifyContent: 'space-between',
          alignItems: { xs: 'stretch', md: 'center' },
          gap: 2,
          mb: 3,
        }}
      >
        <Typography variant="h4" component="h1" fontWeight={600}>
          Alertas y Anomalías
        </Typography>

        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 2,
            alignItems: 'center',
          }}
        >
          <DateRangePicker
            startDate={filters.dateRange.startDate}
            endDate={filters.dateRange.endDate}
            onChange={setDateRange}
          />
          <SeverityFilter
            value={filters.severity}
            onChange={setSeverity}
          />
          <Tooltip title="Actualizar">
            <IconButton onClick={loadData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <ExportButton
            elementId="alerts-dashboard"
            data={alerts}
            columns={getExportColumns()}
            filename="alertas-emi"
            title="Alertas y Anomalías - EMI"
          />
        </Box>
      </Box>

      {error && (
        <MuiAlert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </MuiAlert>
      )}

      {/* KPIs */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Alertas Críticas"
            value={stats?.critical || 0}
            icon={<ErrorIcon />}
            color="error"
            subtitle="requieren acción inmediata"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Alertas Altas"
            value={stats?.high || 0}
            icon={<WarningIcon />}
            color="warning"
            subtitle="prioridad alta"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Pendientes"
            value={stats?.pending || 0}
            icon={<AlertIcon />}
            color="info"
            subtitle="sin resolver"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Resueltas"
            value={stats?.resolved || 0}
            icon={<ResolvedIcon />}
            color="success"
            subtitle="en el período"
          />
        </Grid>
      </Grid>

      {/* ══════ ESTADÍSTICAS DE DETECCIÓN DE PROBLEMAS ══════ */}
      {problemStats?.disponible && problemStats.resumen && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
            Estadísticas de Detección de Problemas
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Análisis cuantitativo (IA) del contenido institucional clasificado como
            negativo o queja, para identificar dónde y qué tan graves son los problemas.
          </Typography>

          {/* KPIs de problemas */}
          <Grid container spacing={2} sx={{ mb: 2 }}>
            {[
              { label: 'Tasa de problemas', value: `${problemStats.resumen.tasaProblemas}%`, color: '#b91c1c', sub: 'del contenido institucional' },
              { label: 'Problemas detectados', value: problemStats.resumen.totalProblemas, color: '#ea580c', sub: 'negativos + quejas' },
              { label: 'Críticos / altos', value: problemStats.resumen.criticos, color: '#d32f2f', sub: 'requieren atención' },
              { label: 'Áreas afectadas', value: problemStats.resumen.temasAfectados, color: '#7c3aed', sub: 'temas distintos' },
            ].map((k) => (
              <Grid item xs={6} md={3} key={k.label}>
                <Card variant="outlined">
                  <CardContent sx={{ py: 1.5 }}>
                    <Typography variant="h4" sx={{ fontWeight: 700, color: k.color }}>{k.value}</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{k.label}</Typography>
                    <Typography variant="caption" color="text.secondary">{k.sub}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={2}>
            {/* Problemas por tema */}
            <Grid item xs={12} md={7}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Problemas por tema institucional
                  </Typography>
                  {problemStats.porTema && problemStats.porTema.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={problemStats.porTema} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis type="number" allowDecimals={false} fontSize={12} />
                        <YAxis dataKey="tema" type="category" width={120} fontSize={11} />
                        <RTooltip />
                        <Legend />
                        <Bar dataKey="negativos" name="Negativos" stackId="a" fill="#ef4444" />
                        <Bar dataKey="quejas" name="Quejas" stackId="a" fill="#f59e0b" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <EmptyState title="Sin problemas" message="No se detectaron problemas." />}
                </CardContent>
              </Card>
            </Grid>

            {/* Distribución por severidad */}
            <Grid item xs={12} md={5}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Severidad de los problemas
                  </Typography>
                  {problemStats.porSeveridad && problemStats.porSeveridad.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie data={problemStats.porSeveridad} dataKey="cantidad" nameKey="severidad"
                             cx="50%" cy="50%" outerRadius={95} label={(e: any) => `${e.severidad} (${e.cantidad})`}>
                          {problemStats.porSeveridad.map((s) => (
                            <Cell key={s.severidad} fill={SEV_COLORS[s.severidad] || '#94a3b8'} />
                          ))}
                        </Pie>
                        <RTooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : <EmptyState title="Sin datos" message="" />}
                </CardContent>
              </Card>
            </Grid>

            {/* Evolución temporal */}
            <Grid item xs={12} md={7}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Evolución de problemas en el tiempo
                  </Typography>
                  {problemStats.tendencia && problemStats.tendencia.length > 0 ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={problemStats.tendencia}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="fecha" fontSize={10} />
                        <YAxis allowDecimals={false} fontSize={12} />
                        <RTooltip />
                        <Line type="monotone" dataKey="problemas" name="Problemas" stroke="#b91c1c" strokeWidth={2} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : <EmptyState title="Sin tendencia" message="" />}
                </CardContent>
              </Card>
            </Grid>

            {/* Problemas por carrera */}
            <Grid item xs={12} md={5}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                    Problemas por carrera
                  </Typography>
                  {problemStats.porCarrera && problemStats.porCarrera.length > 0 ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={problemStats.porCarrera} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis type="number" allowDecimals={false} fontSize={12} />
                        <YAxis dataKey="careerName" type="category" width={130} fontSize={10} />
                        <RTooltip />
                        <Bar dataKey="problemas" name="Problemas" fill="#7c3aed" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <EmptyState title="Sin datos" message="No hay problemas asociados a carreras." />}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Resumen por severidad */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                Distribución por Severidad
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
                {[
                  { label: 'Crítica', value: stats?.critical || 0, color: '#d32f2f' },
                  { label: 'Alta', value: stats?.high || 0, color: '#f57c00' },
                  { label: 'Media', value: stats?.medium || 0, color: '#fbc02d' },
                  { label: 'Baja', value: stats?.low || 0, color: '#388e3c' },
                ].map((item) => (
                  <Box key={item.label} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        bgcolor: item.color,
                      }}
                    />
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {item.label}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {item.value}
                    </Typography>
                    <Box
                      sx={{
                        width: 100,
                        height: 8,
                        bgcolor: 'divider',
                        borderRadius: 1,
                        overflow: 'hidden',
                      }}
                    >
                      <Box
                        sx={{
                          width: `${stats?.total ? (item.value / stats.total) * 100 : 0}%`,
                          height: '100%',
                          bgcolor: item.color,
                          borderRadius: 1,
                        }}
                      />
                    </Box>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                Actividad Reciente
              </Typography>
              <Box sx={{ display: 'flex', gap: 4, mt: 2 }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: 'warning.main',
                    color: 'warning.contrastText',
                    borderRadius: 2,
                    flex: 1,
                    textAlign: 'center',
                  }}
                >
                  <Typography variant="h3" fontWeight={700}>
                    {stats?.lastHour || 0}
                  </Typography>
                  <Typography variant="body2">Última hora</Typography>
                </Paper>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: 'info.main',
                    color: 'info.contrastText',
                    borderRadius: 2,
                    flex: 1,
                    textAlign: 'center',
                  }}
                >
                  <Typography variant="h3" fontWeight={700}>
                    {stats?.last24Hours || 0}
                  </Typography>
                  <Typography variant="body2">Últimas 24 horas</Typography>
                </Paper>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    borderRadius: 2,
                    flex: 1,
                    textAlign: 'center',
                  }}
                >
                  <Typography variant="h3" fontWeight={700}>
                    {stats?.total || 0}
                  </Typography>
                  <Typography variant="body2">Total en período</Typography>
                </Paper>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabla de alertas */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
            Lista de Alertas
          </Typography>
          
          {alerts.length > 0 ? (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Severidad</TableCell>
                      <TableCell>Título</TableCell>
                      <TableCell>Tipo</TableCell>
                      <TableCell>Fuente</TableCell>
                      <TableCell>Estado</TableCell>
                      <TableCell>Fecha</TableCell>
                      <TableCell align="right">Acciones</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {alerts.map((alert) => (
                      <TableRow
                        key={alert.id}
                        hover
                        sx={{
                          bgcolor: alert.status === 'pending' && alert.severity === 'critical'
                            ? 'error.main'
                            : 'transparent',
                          '& td': {
                            color: alert.status === 'pending' && alert.severity === 'critical'
                              ? 'error.contrastText'
                              : 'inherit',
                          },
                        }}
                      >
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getSeverityIcon(alert.severity)}
                            <SeverityChip severity={alert.severity || 'media'} />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={500}>
                            {alert.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {(alert.message ?? '').substring(0, 60)}...
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={alert.type} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>{alert.source || '-'}</TableCell>
                        <TableCell>
                          <Chip
                            label={alert.status === 'resolved' ? 'Resuelta' : 'Pendiente'}
                            size="small"
                            color={alert.status === 'resolved' ? 'success' : 'warning'}
                          />
                        </TableCell>
                        <TableCell>
                          <Tooltip title={formatDateDisplay(alert.createdAt ?? '')}>
                            <Typography variant="body2">
                              {formatTimeAgo(alert.createdAt ?? '')}
                            </Typography>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="Ver detalles">
                            <IconButton
                              size="small"
                              onClick={() => handleViewAlert(alert)}
                            >
                              <ViewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {alert.status !== 'resolved' && (
                            <Tooltip title="Resolver">
                              <IconButton
                                size="small"
                                color="success"
                                onClick={() => handleOpenResolveDialog(alert)}
                              >
                                <DoneIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                rowsPerPageOptions={[5, 10, 25]}
                component="div"
                count={totalAlerts}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                labelRowsPerPage="Filas por página"
              />
            </>
          ) : (
            <EmptyState
              title="Sin alertas"
              message="No hay alertas que coincidan con los filtros seleccionados."
              icon={<ResolvedIcon sx={{ fontSize: 64, color: 'success.main' }} />}
            />
          )}
        </CardContent>
      </Card>

      {/* Dialog para resolver alerta */}
      <Dialog
        open={resolveDialogOpen}
        onClose={handleCloseResolveDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Resolver Alerta</DialogTitle>
        <DialogContent>
          {selectedAlert && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Alerta:
              </Typography>
              <Typography variant="body1" gutterBottom>
                {selectedAlert.title}
              </Typography>
            </Box>
          )}
          <TextField
            autoFocus
            margin="dense"
            label="Resolución"
            fullWidth
            multiline
            rows={4}
            value={resolution}
            onChange={(e) => setResolution(e.target.value)}
            placeholder="Describe las acciones tomadas para resolver esta alerta..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseResolveDialog}>Cancelar</Button>
          <Button
            onClick={handleResolveAlert}
            variant="contained"
            disabled={!resolution.trim()}
          >
            Resolver
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog para ver detalles de alerta */}
      <Dialog
        open={!!selectedAlert && !resolveDialogOpen}
        onClose={() => setSelectedAlert(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedAlert && getSeverityIcon(selectedAlert.severity)}
            Detalles de Alerta
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedAlert && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Título
                </Typography>
                <Typography variant="body1">{selectedAlert.title}</Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Mensaje
                </Typography>
                <Typography variant="body1">{selectedAlert.message}</Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 4 }}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Tipo
                  </Typography>
                  <Chip label={selectedAlert.type} size="small" />
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Severidad
                  </Typography>
                  <SeverityChip severity={selectedAlert.severity || 'media'} />
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Estado
                  </Typography>
                  <Chip
                    label={selectedAlert.status === 'resolved' ? 'Resuelta' : 'Pendiente'}
                    size="small"
                    color={selectedAlert.status === 'resolved' ? 'success' : 'warning'}
                  />
                </Box>
              </Box>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Fecha de creación
                </Typography>
                <Typography variant="body1">
                  {formatDateDisplay(selectedAlert.createdAt ?? '')}
                </Typography>
              </Box>
              {selectedAlert.resolution && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Resolución
                  </Typography>
                  <Typography variant="body1">
                    {selectedAlert.resolution.comment ?? selectedAlert.resolution.date ?? '-'}
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedAlert(null)}>Cerrar</Button>
          {selectedAlert?.status !== 'resolved' && (
            <Button
              variant="contained"
              onClick={() => {
                setResolveDialogOpen(true);
              }}
            >
              Resolver
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AlertsDashboard;
