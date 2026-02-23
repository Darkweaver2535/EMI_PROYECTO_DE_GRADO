/**
 * Dashboard de Configuración del Sistema
 * Configuración de alertas + perfil de usuario
 * Sistema OSINT EMI
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Alert as MuiAlert,
  Chip,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Slider,
  InputAdornment,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  NotificationsActive as AlertConfigIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Person as ProfileIcon,
  Save as SaveIcon,
  Visibility as ViewIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { LoadingSpinner } from '../common';
import configuracionService, { ConfigAlerta } from '../../services/configuracionService';
import { useAuth } from '../../contexts';
import authService from '../../services/authService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const ConfiguracionDashboard: React.FC = () => {
  const { user } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState<ConfigAlerta[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Config dialog
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [configMode, setConfigMode] = useState<'create' | 'edit'>('create');
  const [editingConfig, setEditingConfig] = useState<ConfigAlerta | null>(null);
  const [configForm, setConfigForm] = useState({
    nombre: '',
    tipo_alerta: 'sentiment_negative',
    umbral_valor: 0.7,
    umbral_confianza: 0.5,
    severidad_minima: 'media',
    activa: true,
    notificar_email: false,
  });

  // Password change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);

  const loadConfigs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await configuracionService.getConfiguraciones();
      setConfigs(res.configuraciones);
    } catch (err) {
      console.error('Error loading configs:', err);
      setError('Error al cargar configuraciones');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleOpenCreateConfig = () => {
    setConfigMode('create');
    setConfigForm({
      nombre: '',
      tipo_alerta: 'sentiment_negative',
      umbral_valor: 0.7,
      umbral_confianza: 0.5,
      severidad_minima: 'media',
      activa: true,
      notificar_email: false,
    });
    setEditingConfig(null);
    setConfigDialogOpen(true);
  };

  const handleOpenEditConfig = (config: ConfigAlerta) => {
    setConfigMode('edit');
    setConfigForm({
      nombre: config.nombre,
      tipo_alerta: config.tipo_alerta,
      umbral_valor: config.umbral_valor,
      umbral_confianza: config.umbral_confianza,
      severidad_minima: config.severidad_minima,
      activa: config.activa,
      notificar_email: config.notificar_email,
    });
    setEditingConfig(config);
    setConfigDialogOpen(true);
  };

  const handleSaveConfig = async () => {
    try {
      if (configMode === 'create') {
        await configuracionService.createConfiguracion(configForm);
        setSuccess('Configuración creada');
      } else if (editingConfig) {
        await configuracionService.updateConfiguracion(editingConfig.id, configForm);
        setSuccess('Configuración actualizada');
      }
      setConfigDialogOpen(false);
      loadConfigs();
    } catch {
      setError('Error al guardar configuración');
    }
  };

  const handleDeleteConfig = async (id: number) => {
    try {
      await configuracionService.deleteConfiguracion(id);
      setSuccess('Configuración eliminada');
      loadConfigs();
    } catch {
      setError('Error al eliminar configuración');
    }
  };

  const handleToggleConfig = async (config: ConfigAlerta) => {
    try {
      await configuracionService.updateConfiguracion(config.id, {
        activa: !config.activa,
      });
      loadConfigs();
    } catch {
      setError('Error al actualizar configuración');
    }
  };

  const handleChangePassword = async () => {
    setError(null);
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }
    if (newPassword.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres');
      return;
    }
    try {
      await authService.changePassword(currentPassword, newPassword);
      setSuccess('Contraseña actualizada exitosamente');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch {
      setError('Error al cambiar la contraseña. Verifique la contraseña actual.');
    }
  };

  const rolLabels: Record<string, string> = {
    administrador: 'Administrador del Sistema',
    vicerrector: 'Vicerrector de Grado / Jefe',
    uebu: 'Usuario UEBU',
  };

  if (loading && configs.length === 0) {
    return <LoadingSpinner message="Cargando configuración..." />;
  }

  return (
    <Box>
      <Typography variant="h4" component="h1" fontWeight={600} sx={{ mb: 3 }}>
        Configuración del Sistema
      </Typography>

      {error && (
        <MuiAlert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </MuiAlert>
      )}
      {success && (
        <MuiAlert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </MuiAlert>
      )}

      <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 1 }}>
        <Tab icon={<AlertConfigIcon />} label="Configuración de Alertas" iconPosition="start" />
        <Tab icon={<ProfileIcon />} label="Mi Perfil" iconPosition="start" />
      </Tabs>

      {/* Tab: Alert Configuration */}
      <TabPanel value={tabValue} index={0}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" fontWeight={500}>
            Reglas de Alertas
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Actualizar">
              <IconButton onClick={loadConfigs}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenCreateConfig}>
              Nueva Regla
            </Button>
          </Box>
        </Box>

        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Nombre</TableCell>
                  <TableCell>Tipo Alerta</TableCell>
                  <TableCell>Umbral Valor</TableCell>
                  <TableCell>Umbral Confianza</TableCell>
                  <TableCell>Severidad Mín.</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {configs.map((config) => (
                  <TableRow key={config.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {config.nombre}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={config.tipo_alerta} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{config.umbral_valor}</TableCell>
                    <TableCell>{config.umbral_confianza}</TableCell>
                    <TableCell>
                      <Chip
                        label={config.severidad_minima}
                        size="small"
                        color={
                          config.severidad_minima === 'critica'
                            ? 'error'
                            : config.severidad_minima === 'alta'
                            ? 'warning'
                            : 'info'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      {config.notificar_email ? (
                        <Chip label="Sí" size="small" color="success" />
                      ) : (
                        <Chip label="No" size="small" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={config.activa}
                        onChange={() => handleToggleConfig(config)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Editar">
                        <IconButton size="small" onClick={() => handleOpenEditConfig(config)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Eliminar">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteConfig(config.id)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {configs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      <Typography variant="body2" color="text.secondary" py={4}>
                        No hay configuraciones de alertas
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>

        {/* Info card */}
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Tipos de Alertas Disponibles
            </Typography>
            <Grid container spacing={2}>
              {[
                { tipo: 'sentiment_negative', desc: 'Se activa cuando se detectan comentarios negativos con alta confianza' },
                { tipo: 'engagement_spike', desc: 'Se activa cuando hay un pico inusual de interacciones' },
                { tipo: 'reputation_critical', desc: 'Se activa cuando la reputación baja a niveles críticos' },
                { tipo: 'volume_anomaly', desc: 'Se activa cuando el volumen de publicaciones es anómalo' },
              ].map((t) => (
                <Grid item xs={12} sm={6} key={t.tipo}>
                  <Paper elevation={0} sx={{ p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                    <Chip label={t.tipo} size="small" variant="outlined" sx={{ mb: 1 }} />
                    <Typography variant="body2" color="text.secondary">
                      {t.desc}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Tab: Profile */}
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight={500}>
                  Información del Usuario
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Usuario
                    </Typography>
                    <Typography variant="body1" fontWeight={500}>
                      {user?.username}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Nombre
                    </Typography>
                    <Typography variant="body1">
                      {user?.name || user?.nombre}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Email
                    </Typography>
                    <Typography variant="body1">{user?.email}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Rol
                    </Typography>
                    <Chip
                      label={rolLabels[user?.rol || ''] || user?.rol}
                      color={
                        user?.rol === 'administrador'
                          ? 'error'
                          : user?.rol === 'vicerrector'
                          ? 'warning'
                          : 'info'
                      }
                      size="small"
                    />
                  </Box>
                  {user?.cargo && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Cargo
                      </Typography>
                      <Typography variant="body1">{user.cargo}</Typography>
                    </Box>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight={500}>
                  Cambiar Contraseña
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    label="Contraseña Actual"
                    type={showPasswords ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    fullWidth
                    size="small"
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton size="small" onClick={() => setShowPasswords(!showPasswords)}>
                            {showPasswords ? <VisibilityOffIcon /> : <ViewIcon />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    }}
                  />
                  <TextField
                    label="Nueva Contraseña"
                    type={showPasswords ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    fullWidth
                    size="small"
                  />
                  <TextField
                    label="Confirmar Nueva Contraseña"
                    type={showPasswords ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    fullWidth
                    size="small"
                    error={!!confirmPassword && confirmPassword !== newPassword}
                    helperText={
                      confirmPassword && confirmPassword !== newPassword
                        ? 'Las contraseñas no coinciden'
                        : ''
                    }
                  />
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={handleChangePassword}
                    disabled={!currentPassword || !newPassword || newPassword !== confirmPassword}
                  >
                    Cambiar Contraseña
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Config Dialog */}
      <Dialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {configMode === 'create' ? 'Nueva Regla de Alerta' : 'Editar Regla de Alerta'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Nombre"
              value={configForm.nombre}
              onChange={(e) => setConfigForm({ ...configForm, nombre: e.target.value })}
              fullWidth
              size="small"
              required
            />
            <FormControl fullWidth size="small">
              <InputLabel>Tipo de Alerta</InputLabel>
              <Select
                value={configForm.tipo_alerta}
                label="Tipo de Alerta"
                onChange={(e) => setConfigForm({ ...configForm, tipo_alerta: e.target.value })}
              >
                <MenuItem value="sentiment_negative">Sentimiento Negativo</MenuItem>
                <MenuItem value="engagement_spike">Pico de Engagement</MenuItem>
                <MenuItem value="reputation_critical">Reputación Crítica</MenuItem>
                <MenuItem value="volume_anomaly">Anomalía de Volumen</MenuItem>
                <MenuItem value="custom">Personalizado</MenuItem>
              </Select>
            </FormControl>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Umbral de Valor: {configForm.umbral_valor}
              </Typography>
              <Slider
                value={configForm.umbral_valor}
                onChange={(_, v) =>
                  setConfigForm({ ...configForm, umbral_valor: v as number })
                }
                min={0}
                max={1}
                step={0.05}
                valueLabelDisplay="auto"
              />
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Umbral de Confianza: {configForm.umbral_confianza}
              </Typography>
              <Slider
                value={configForm.umbral_confianza}
                onChange={(_, v) =>
                  setConfigForm({ ...configForm, umbral_confianza: v as number })
                }
                min={0}
                max={1}
                step={0.05}
                valueLabelDisplay="auto"
              />
            </Box>
            <FormControl fullWidth size="small">
              <InputLabel>Severidad Mínima</InputLabel>
              <Select
                value={configForm.severidad_minima}
                label="Severidad Mínima"
                onChange={(e) =>
                  setConfigForm({ ...configForm, severidad_minima: e.target.value })
                }
              >
                <MenuItem value="critica">Crítica</MenuItem>
                <MenuItem value="alta">Alta</MenuItem>
                <MenuItem value="media">Media</MenuItem>
                <MenuItem value="baja">Baja</MenuItem>
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Switch
                  checked={configForm.activa}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, activa: e.target.checked })
                  }
                />
              }
              label="Regla activa"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={configForm.notificar_email}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, notificar_email: e.target.checked })
                  }
                />
              }
              label="Notificación por email"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>Cancelar</Button>
          <Button
            onClick={handleSaveConfig}
            variant="contained"
            disabled={!configForm.nombre}
          >
            {configMode === 'create' ? 'Crear' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConfiguracionDashboard;
