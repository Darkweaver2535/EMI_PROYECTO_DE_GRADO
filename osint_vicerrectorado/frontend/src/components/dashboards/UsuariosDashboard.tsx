/**
 * Dashboard de Gestión de Usuarios
 * Sistema OSINT EMI - Módulo de Usuarios con CRUD
 * Roles: administrador, vicerrector, uebu
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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert as MuiAlert,
  Switch,
  FormControlLabel,
  Paper,
  Divider,
  InputAdornment,
  alpha,
} from '@mui/material';
import {
  PersonAdd as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  AdminPanelSettings as AdminIcon,
  SupervisorAccount as ViceIcon,
  Person as UserIcon,
  Visibility as ViewIcon,
  VisibilityOff as VisibilityOffIcon,
  Search as SearchIcon,
  History as HistoryIcon,
  Security as SecurityIcon,
  TravelExplore as OsintModIcon,
  Comment as PostsModIcon,
  Psychology as AiModIcon,
  SmartToy as NlpModIcon,
  Assessment as EvalModIcon,
  Group as UsersModIcon,
  Settings as ConfigModIcon,
} from '@mui/icons-material';
import { KPICard, LoadingSpinner } from '../common';
import usuariosService, { UsuarioData, UsuarioPermisos } from '../../services/usuariosService';

const rolLabels: Record<string, string> = {
  administrador: 'Administrador',
  vicerrector: 'Vicerrector / Jefe',
  uebu: 'Usuario UEBU',
};

const rolColors: Record<string, 'error' | 'warning' | 'info' | 'success'> = {
  administrador: 'error',
  vicerrector: 'warning',
  uebu: 'info',
};

const rolIcons: Record<string, React.ReactNode> = {
  administrador: <AdminIcon />,
  vicerrector: <ViceIcon />,
  uebu: <UserIcon />,
};

// ========== MÓDULOS Y PERMISOS ==========
const MODULE_DEFINITIONS: { key: keyof UsuarioPermisos; label: string; icon: React.ReactNode; description: string }[] = [
  { key: 'osint', label: 'Inteligencia OSINT', icon: <OsintModIcon />, description: 'Monitoreo y recolección de datos OSINT' },
  { key: 'posts', label: 'Posts y Comentarios', icon: <PostsModIcon />, description: 'Gestión de posts, comentarios y web scraping' },
  { key: 'dashboards', label: 'Análisis IA', icon: <AiModIcon />, description: 'Sentimientos, reputación, alertas, benchmarking' },
  { key: 'nlp', label: 'IA / ML / NLP', icon: <NlpModIcon />, description: 'Pipeline de procesamiento de lenguaje natural' },
  { key: 'evaluacion', label: 'Evaluación del Sistema', icon: <EvalModIcon />, description: 'Métricas de rendimiento y evaluación (95.2%)' },
  { key: 'usuarios', label: 'Gestión de Usuarios', icon: <UsersModIcon />, description: 'CRUD de usuarios y roles del sistema' },
  { key: 'configuracion', label: 'Configuración', icon: <ConfigModIcon />, description: 'Ajustes generales del sistema' },
];

const DEFAULT_PERMISOS: Record<string, UsuarioPermisos> = {
  administrador: { osint: true, posts: true, dashboards: true, nlp: true, evaluacion: true, usuarios: true, configuracion: true },
  vicerrector: { osint: true, posts: true, dashboards: true, nlp: true, evaluacion: true, usuarios: false, configuracion: true },
  uebu: { osint: false, posts: false, dashboards: true, nlp: true, evaluacion: false, usuarios: false, configuracion: false },
};

interface UserFormData {
  username: string;
  email: string;
  nombre_completo: string;
  rol: 'administrador' | 'vicerrector' | 'uebu';
  cargo: string;
  password: string;
  activo: boolean;
  permisos: UsuarioPermisos;
}

const emptyForm: UserFormData = {
  username: '',
  email: '',
  nombre_completo: '',
  rol: 'uebu',
  cargo: '',
  password: '',
  activo: true,
  permisos: { ...DEFAULT_PERMISOS.uebu },
};

const UsuariosDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [usuarios, setUsuarios] = useState<UsuarioData[]>([]);
  const [filteredUsuarios, setFilteredUsuarios] = useState<UsuarioData[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Dialog states
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<'create' | 'edit'>('create');
  const [formData, setFormData] = useState<UserFormData>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // Delete dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState<UsuarioData | null>(null);

  // Logs dialog
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);
  const [logs, setLogs] = useState<Array<{
    id: number; usuario: string; nombre_usuario: string;
    accion: string; detalle: string; ip: string; fecha: string;
  }>>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await usuariosService.getUsuarios();
      setUsuarios(res.usuarios);
      setFilteredUsuarios(res.usuarios);
    } catch (err) {
      console.error('Error loading users:', err);
      setError('Error al cargar los usuarios.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!searchTerm) {
      setFilteredUsuarios(usuarios);
    } else {
      const term = searchTerm.toLowerCase();
      setFilteredUsuarios(
        usuarios.filter(
          (u) =>
            u.username.toLowerCase().includes(term) ||
            u.nombre_completo.toLowerCase().includes(term) ||
            u.email.toLowerCase().includes(term) ||
            u.rol.toLowerCase().includes(term)
        )
      );
    }
  }, [searchTerm, usuarios]);

  const handleOpenCreate = () => {
    setDialogMode('create');
    setFormData({ ...emptyForm, permisos: { ...DEFAULT_PERMISOS.uebu } });
    setEditingId(null);
    setShowPassword(false);
    setDialogOpen(true);
  };

  const handleOpenEdit = (user: UsuarioData) => {
    setDialogMode('edit');
    const userPermisos = user.permisos || DEFAULT_PERMISOS[user.rol] || DEFAULT_PERMISOS.uebu;
    setFormData({
      username: user.username,
      email: user.email,
      nombre_completo: user.nombre_completo,
      rol: user.rol,
      cargo: user.cargo || '',
      password: '',
      activo: user.activo !== false,
      permisos: { ...userPermisos },
    });
    setEditingId(user.id || null);
    setShowPassword(false);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setFormData(emptyForm);
    setEditingId(null);
  };

  const handleSave = async () => {
    setError(null);
    try {
      if (dialogMode === 'create') {
        if (!formData.password) {
          setError('La contraseña es requerida para nuevos usuarios');
          return;
        }
        await usuariosService.createUsuario({
          username: formData.username,
          email: formData.email,
          nombre_completo: formData.nombre_completo,
          rol: formData.rol,
          cargo: formData.cargo,
          password: formData.password,
          permisos: formData.permisos,
        });
        setSuccess('Usuario creado exitosamente');
      } else if (editingId) {
        const updateData: Partial<UsuarioData> = {
          username: formData.username,
          email: formData.email,
          nombre_completo: formData.nombre_completo,
          rol: formData.rol,
          cargo: formData.cargo,
          activo: formData.activo,
          permisos: formData.permisos,
        };
        if (formData.password) {
          updateData.password = formData.password;
        }
        await usuariosService.updateUsuario(editingId, updateData);
        setSuccess('Usuario actualizado exitosamente');
      }
      handleCloseDialog();
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al guardar';
      setError(msg);
    }
  };

  const handleOpenDelete = (user: UsuarioData) => {
    setDeletingUser(user);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingUser?.id) return;
    try {
      await usuariosService.deleteUsuario(deletingUser.id);
      setSuccess(`Usuario "${deletingUser.username}" desactivado`);
      setDeleteDialogOpen(false);
      setDeletingUser(null);
      loadData();
    } catch (err) {
      setError('Error al desactivar usuario');
    }
  };

  const handleOpenLogs = async () => {
    try {
      const res = await usuariosService.getLogs(100);
      setLogs(res.logs);
      setLogsDialogOpen(true);
    } catch {
      setError('Error al cargar registros de actividad');
    }
  };

  // Stats
  const totalUsers = usuarios.length;
  const activeUsers = usuarios.filter((u) => u.activo !== false).length;
  const adminCount = usuarios.filter((u) => u.rol === 'administrador').length;
  const viceCount = usuarios.filter((u) => u.rol === 'vicerrector').length;

  if (loading && usuarios.length === 0) {
    return <LoadingSpinner message="Cargando usuarios..." />;
  }

  return (
    <Box>
      {/* Header */}
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
          Gestión de Usuarios
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<HistoryIcon />}
            onClick={handleOpenLogs}
          >
            Actividad
          </Button>
          <Tooltip title="Actualizar">
            <IconButton onClick={loadData}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenCreate}
          >
            Nuevo Usuario
          </Button>
        </Box>
      </Box>

      {/* Alerts */}
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

      {/* KPIs */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Total Usuarios"
            value={totalUsers}
            icon={<UserIcon />}
            color="primary"
            subtitle="registrados en el sistema"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Usuarios Activos"
            value={activeUsers}
            icon={<UserIcon />}
            color="success"
            subtitle="con acceso habilitado"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Administradores"
            value={adminCount}
            icon={<AdminIcon />}
            color="error"
            subtitle="control total"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Vicerrectores / Jefes"
            value={viceCount}
            icon={<ViceIcon />}
            color="warning"
            subtitle="supervisión"
          />
        </Grid>
      </Grid>

      {/* Search */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ py: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Buscar por nombre, usuario, email o rol..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
            Lista de Usuarios ({filteredUsuarios.length})
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Usuario</TableCell>
                  <TableCell>Nombre Completo</TableCell>
                  <TableCell>Rol</TableCell>
                  <TableCell>Módulos</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Último Acceso</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredUsuarios.map((user) => {
                  const permisos = user.permisos || DEFAULT_PERMISOS[user.rol] || DEFAULT_PERMISOS.uebu;
                  const activeCount = Object.values(permisos).filter(Boolean).length;
                  const totalCount = MODULE_DEFINITIONS.length;
                  return (
                  <TableRow key={user.id} hover>
                    <TableCell>{user.id}</TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {user.username}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {user.email}
                      </Typography>
                    </TableCell>
                    <TableCell>{user.nombre_completo}</TableCell>
                    <TableCell>
                      <Chip
                        icon={rolIcons[user.rol] as React.ReactElement}
                        label={rolLabels[user.rol] || user.rol}
                        size="small"
                        color={rolColors[user.rol] || 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Tooltip title={MODULE_DEFINITIONS.filter(m => permisos[m.key]).map(m => m.label).join(', ') || 'Sin módulos'}>
                        <Chip
                          label={`${activeCount}/${totalCount}`}
                          size="small"
                          color={activeCount === totalCount ? 'success' : activeCount > 0 ? 'warning' : 'default'}
                          variant="outlined"
                          icon={<SecurityIcon fontSize="small" />}
                        />
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.activo !== false ? 'Activo' : 'Inactivo'}
                        size="small"
                        color={user.activo !== false ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {user.ultimo_login || 'Nunca'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Editar">
                        <IconButton size="small" onClick={() => handleOpenEdit(user)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Desactivar">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleOpenDelete(user)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                  );
                })}
                {filteredUsuarios.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      <Typography variant="body2" color="text.secondary" py={4}>
                        No se encontraron usuarios
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Roles info */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
            Roles del Sistema
          </Typography>
          <Grid container spacing={2}>
            {[
              {
                rol: 'administrador',
                nombre: 'Administrador del Sistema',
                desc: 'Acceso total: gestión de usuarios, configuración del sistema, administración de alertas y todos los módulos.',
                icon: <AdminIcon sx={{ fontSize: 40 }} />,
                color: '#d32f2f',
              },
              {
                rol: 'vicerrector',
                nombre: 'Vicerrector de Grado / Jefe',
                desc: 'Supervisión ejecutiva: dashboards, reportes, visualización de análisis y alertas críticas.',
                icon: <ViceIcon sx={{ fontSize: 40 }} />,
                color: '#f57c00',
              },
              {
                rol: 'uebu',
                nombre: 'Usuario UEBU',
                desc: 'Análisis operativo: gestión de alertas, análisis de sentimientos, OSINT y NLP.',
                icon: <UserIcon sx={{ fontSize: 40 }} />,
                color: '#1976d2',
              },
            ].map((r) => (
              <Grid item xs={12} md={4} key={r.rol}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 2,
                    height: '100%',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                    <Box sx={{ color: r.color }}>{r.icon}</Box>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {r.nombre}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {r.desc}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    {usuarios.filter((u) => u.rol === r.rol).length} usuario(s)
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {dialogMode === 'create' ? <AddIcon color="primary" /> : <EditIcon color="primary" />}
          {dialogMode === 'create' ? 'Crear Nuevo Usuario' : 'Editar Usuario'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Nombre de Usuario"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              fullWidth
              required
              size="small"
            />
            <TextField
              label="Nombre Completo"
              value={formData.nombre_completo}
              onChange={(e) => setFormData({ ...formData, nombre_completo: e.target.value })}
              fullWidth
              required
              size="small"
            />
            <TextField
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              fullWidth
              required
              size="small"
            />
            <FormControl fullWidth size="small" required>
              <InputLabel>Rol</InputLabel>
              <Select
                value={formData.rol}
                label="Rol"
                onChange={(e) => {
                  const newRol = e.target.value as 'administrador' | 'vicerrector' | 'uebu';
                  setFormData({
                    ...formData,
                    rol: newRol,
                    permisos: { ...(DEFAULT_PERMISOS[newRol] || DEFAULT_PERMISOS.uebu) },
                  });
                }}
              >
                <MenuItem value="administrador">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AdminIcon fontSize="small" color="error" />
                    Administrador del Sistema
                  </Box>
                </MenuItem>
                <MenuItem value="vicerrector">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ViceIcon fontSize="small" color="warning" />
                    Vicerrector de Grado / Jefe
                  </Box>
                </MenuItem>
                <MenuItem value="uebu">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <UserIcon fontSize="small" color="info" />
                    Usuario UEBU
                  </Box>
                </MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Cargo"
              value={formData.cargo}
              onChange={(e) => setFormData({ ...formData, cargo: e.target.value })}
              fullWidth
              size="small"
            />
            <TextField
              label={dialogMode === 'create' ? 'Contraseña' : 'Nueva Contraseña (dejar en blanco para no cambiar)'}
              type={showPassword ? 'text' : 'password'}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              fullWidth
              required={dialogMode === 'create'}
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? <VisibilityOffIcon /> : <ViewIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            {dialogMode === 'edit' && (
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.activo}
                    onChange={(e) =>
                      setFormData({ ...formData, activo: e.target.checked })
                    }
                  />
                }
                label="Usuario activo"
              />
            )}

            {/* ========== PERMISOS POR MÓDULO ========== */}
            <Divider sx={{ my: 0.5 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <SecurityIcon color="primary" fontSize="small" />
              <Typography variant="subtitle1" fontWeight={600}>
                Permisos de Acceso por Módulo
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: -1, mb: 1 }}>
              Los permisos se pre-configuran según el rol seleccionado. Puedes ajustarlos manualmente.
            </Typography>

            <Paper variant="outlined" sx={{ borderRadius: 2, overflow: 'hidden' }}>
              {MODULE_DEFINITIONS.map((mod, idx) => {
                const isEnabled = formData.permisos[mod.key];
                return (
                  <Box
                    key={mod.key}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      px: 2,
                      py: 1.2,
                      borderBottom: idx < MODULE_DEFINITIONS.length - 1 ? '1px solid' : 'none',
                      borderColor: 'divider',
                      bgcolor: isEnabled ? (theme) => alpha(theme.palette.success.main, 0.04) : 'transparent',
                      transition: 'background-color 0.2s',
                      '&:hover': {
                        bgcolor: (theme) => alpha(theme.palette.primary.main, 0.04),
                      },
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1, minWidth: 0 }}>
                      <Box sx={{
                        color: isEnabled ? 'primary.main' : 'text.disabled',
                        display: 'flex',
                        transition: 'color 0.2s',
                      }}>
                        {mod.icon}
                      </Box>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          variant="body2"
                          fontWeight={500}
                          sx={{ color: isEnabled ? 'text.primary' : 'text.disabled' }}
                        >
                          {mod.label}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{ color: isEnabled ? 'text.secondary' : 'text.disabled', display: { xs: 'none', sm: 'block' } }}
                        >
                          {mod.description}
                        </Typography>
                      </Box>
                    </Box>
                    <Switch
                      checked={isEnabled}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          permisos: {
                            ...formData.permisos,
                            [mod.key]: e.target.checked,
                          },
                        });
                      }}
                      color="success"
                      size="small"
                    />
                  </Box>
                );
              })}
            </Paper>

            {/* Quick actions */}
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Button
                size="small"
                variant="text"
                onClick={() => setFormData({
                  ...formData,
                  permisos: { osint: true, posts: true, dashboards: true, nlp: true, evaluacion: true, usuarios: true, configuracion: true },
                })}
              >
                Activar todos
              </Button>
              <Button
                size="small"
                variant="text"
                color="inherit"
                onClick={() => setFormData({
                  ...formData,
                  permisos: { osint: false, posts: false, dashboards: false, nlp: false, evaluacion: false, usuarios: false, configuracion: false },
                })}
              >
                Desactivar todos
              </Button>
              <Button
                size="small"
                variant="text"
                color="secondary"
                onClick={() => setFormData({
                  ...formData,
                  permisos: { ...(DEFAULT_PERMISOS[formData.rol] || DEFAULT_PERMISOS.uebu) },
                })}
              >
                Restaurar por rol
              </Button>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={!formData.username || !formData.email || !formData.nombre_completo}
          >
            {dialogMode === 'create' ? 'Crear' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirmar Desactivación</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Está seguro de desactivar al usuario{' '}
            <strong>{deletingUser?.nombre_completo}</strong> ({deletingUser?.username})?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            El usuario no podrá acceder al sistema pero sus datos se conservarán.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancelar</Button>
          <Button onClick={handleDelete} variant="contained" color="error">
            Desactivar
          </Button>
        </DialogActions>
      </Dialog>

      {/* Logs Dialog */}
      <Dialog
        open={logsDialogOpen}
        onClose={() => setLogsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Registro de Actividad</DialogTitle>
        <DialogContent>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Usuario</TableCell>
                  <TableCell>Acción</TableCell>
                  <TableCell>Detalle</TableCell>
                  <TableCell>IP</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <Typography variant="caption">{log.fecha}</Typography>
                    </TableCell>
                    <TableCell>{log.usuario}</TableCell>
                    <TableCell>
                      <Chip label={log.accion} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{log.detalle}</TableCell>
                    <TableCell>
                      <Typography variant="caption">{log.ip}</Typography>
                    </TableCell>
                  </TableRow>
                ))}
                {logs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      Sin registros
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLogsDialogOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UsuariosDashboard;
