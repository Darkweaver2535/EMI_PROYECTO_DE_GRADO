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
import { Alert, AlertStats } from '../../types';
import { formatDateDisplay, formatTimeAgo } from '../../utils';

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

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = getApiParams();

      const [alertsResponse, statsData] = await Promise.all([
        alertsService.getAlerts({
          ...params,
          page: page + 1,
          limit: rowsPerPage,
        }),
        alertsService.getAlertStats({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
      ]);

      setAlerts(alertsResponse.alerts);
      setTotalAlerts(alertsResponse.total);
      setStats(statsData);
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
        alertId: selectedAlert.id,
        resolution: resolution.trim(),
      });
      handleCloseResolveDialog();
      loadData(); // Recargar datos
    } catch (err) {
      console.error('Error resolving alert:', err);
    }
  };

  const getSeverityIcon = (severity: string) => {
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
                            <SeverityChip severity={alert.severity} />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={500}>
                            {alert.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {alert.message.substring(0, 60)}...
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
                          <Tooltip title={formatDateDisplay(alert.createdAt)}>
                            <Typography variant="body2">
                              {formatTimeAgo(alert.createdAt)}
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
                  <SeverityChip severity={selectedAlert.severity} />
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
                  {formatDateDisplay(selectedAlert.createdAt)}
                </Typography>
              </Box>
              {selectedAlert.resolution && (
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Resolución
                  </Typography>
                  <Typography variant="body1">{selectedAlert.resolution}</Typography>
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
