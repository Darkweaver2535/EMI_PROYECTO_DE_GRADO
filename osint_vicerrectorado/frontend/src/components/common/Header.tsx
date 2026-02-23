/**
 * Componente Header
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Menu,
  MenuItem,
  Avatar,
  Tooltip,
  Badge,
  useTheme as useMuiTheme,
  Divider,
  Chip,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  AccountCircle,
  Logout as LogoutIcon,
  Settings as SettingsIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  OpenInNew as OpenInNewIcon,
  MarkEmailRead as MarkReadIcon,
} from '@mui/icons-material';
import { useAuth, useTheme } from '../../contexts';
import { useNavigate } from 'react-router-dom';
import { Alert } from '../../types';

interface HeaderProps {
  onMenuToggle?: () => void;
  title?: string;
  notificationCount?: number;
  alerts?: Alert[];
  onMarkAlertRead?: (alertId: string) => void;
}

const Header: React.FC<HeaderProps> = ({
  onMenuToggle,
  title = 'Sistema OSINT - EMI Bolivia',
  notificationCount = 0,
  alerts = [],
  onMarkAlertRead,
}) => {
  const { user, logout } = useAuth();
  const { mode, toggleTheme } = useTheme();
  const muiTheme = useMuiTheme();
  const navigate = useNavigate();
  
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [notifAnchorEl, setNotifAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNotifOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNotifAnchorEl(event.currentTarget);
  };

  const handleNotifClose = () => {
    setNotifAnchorEl(null);
  };

  const handleLogout = async () => {
    handleMenuClose();
    await logout();
  };

  const handleGoToSettings = () => {
    handleMenuClose();
    navigate('/dashboard/configuracion');
  };

  const handleGoToAlerts = () => {
    handleNotifClose();
    navigate('/dashboard/alerts');
  };

  const handleMarkRead = (alertId: string) => {
    if (onMarkAlertRead) {
      onMarkAlertRead(alertId);
    }
  };

  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getSeverityIcon = (severity?: string) => {
    switch (severity) {
      case 'critical':
      case 'critica':
        return <ErrorIcon sx={{ color: '#d32f2f', fontSize: 20 }} />;
      case 'high':
      case 'alta':
        return <WarningIcon sx={{ color: '#f57c00', fontSize: 20 }} />;
      case 'medium':
      case 'media':
        return <InfoIcon sx={{ color: '#1976d2', fontSize: 20 }} />;
      case 'low':
      case 'baja':
        return <CheckCircleIcon sx={{ color: '#388e3c', fontSize: 20 }} />;
      default:
        return <InfoIcon sx={{ color: '#757575', fontSize: 20 }} />;
    }
  };

  const getSeverityLabel = (severity?: string) => {
    switch (severity) {
      case 'critical':
      case 'critica':
        return 'Critica';
      case 'high':
      case 'alta':
        return 'Alta';
      case 'medium':
      case 'media':
        return 'Media';
      case 'low':
      case 'baja':
        return 'Baja';
      default:
        return severity || '';
    }
  };

  const getSeverityColor = (severity?: string): 'error' | 'warning' | 'info' | 'success' | 'default' => {
    switch (severity) {
      case 'critical':
      case 'critica':
        return 'error';
      case 'high':
      case 'alta':
        return 'warning';
      case 'medium':
      case 'media':
        return 'info';
      case 'low':
      case 'baja':
        return 'success';
      default:
        return 'default';
    }
  };

  const formatTimeAgo = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Ahora';
      if (diffMins < 60) return `Hace ${diffMins} min`;
      if (diffHours < 24) return `Hace ${diffHours}h`;
      if (diffDays < 7) return `Hace ${diffDays}d`;
      return date.toLocaleDateString('es-BO', { day: '2-digit', month: 'short' });
    } catch {
      return '';
    }
  };

  // Show up to 5 alerts in dropdown
  const displayAlerts = alerts.slice(0, 5);

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: muiTheme.zIndex.drawer + 1,
        backgroundColor: muiTheme.palette.primary.main,
      }}
    >
      <Toolbar>
        {onMenuToggle && (
          <IconButton
            color="inherit"
            aria-label="abrir menu"
            edge="start"
            onClick={onMenuToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
        )}

        {/* Logo SADUTO */}
        <Box
          component="img"
          src="/assets/saduto-logo.png"
          alt="SADUTO Logo"
          sx={{
            height: 40,
            mr: 2,
            display: { xs: 'none', sm: 'block' },
          }}
          onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
            e.currentTarget.style.display = 'none';
          }}
        />

        <Typography
          variant="h6"
          component="h1"
          sx={{
            flexGrow: 1,
            fontWeight: 600,
            display: { xs: 'none', md: 'block' },
          }}
        >
          {title}
        </Typography>

        <Typography
          variant="subtitle1"
          component="h1"
          sx={{
            flexGrow: 1,
            fontWeight: 600,
            display: { xs: 'block', md: 'none' },
          }}
        >
          SADUTO
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Theme Toggle */}
          <Tooltip title={mode === 'dark' ? 'Modo claro' : 'Modo oscuro'}>
            <IconButton color="inherit" onClick={toggleTheme}>
              {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>

          {/* Notifications */}
          <Tooltip title="Notificaciones">
            <IconButton color="inherit" onClick={handleNotifOpen}>
              <Badge badgeContent={notificationCount} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* User Menu */}
          <Tooltip title="Cuenta">
            <IconButton onClick={handleMenuOpen} color="inherit">
              {user?.avatarUrl ? (
                <Avatar
                  src={user.avatarUrl}
                  alt={user.name}
                  sx={{ width: 32, height: 32 }}
                />
              ) : user?.name ? (
                <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                  {getInitials(user.name)}
                </Avatar>
              ) : (
                <AccountCircle />
              )}
            </IconButton>
          </Tooltip>
        </Box>

        {/* User Dropdown Menu */}
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        >
          {user && (
            <MenuItem disabled sx={{ opacity: '1 !important' }}>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold">
                  {user.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {user.email}
                </Typography>
              </Box>
            </MenuItem>
          )}
          {user?.rol !== 'uebu' && (
            <MenuItem onClick={handleGoToSettings}>
              <SettingsIcon sx={{ mr: 1 }} fontSize="small" />
              Configuracion
            </MenuItem>
          )}
          <MenuItem onClick={handleLogout}>
            <LogoutIcon sx={{ mr: 1 }} fontSize="small" />
            Cerrar sesion
          </MenuItem>
        </Menu>

        {/* Notifications Dropdown */}
        <Menu
          anchorEl={notifAnchorEl}
          open={Boolean(notifAnchorEl)}
          onClose={handleNotifClose}
          transformOrigin={{ horizontal: 'right', vertical: 'top' }}
          anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
          PaperProps={{
            sx: { width: 380, maxHeight: 480 },
          }}
        >
          {/* Header */}
          <Box sx={{ px: 2, py: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="subtitle1" fontWeight="bold">
              Notificaciones
            </Typography>
            {notificationCount > 0 && (
              <Chip label={notificationCount} size="small" color="error" />
            )}
          </Box>
          <Divider />

          {displayAlerts.length === 0 ? (
            <Box sx={{ px: 2, py: 4, textAlign: 'center' }}>
              <NotificationsIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                No hay notificaciones nuevas
              </Typography>
            </Box>
          ) : (
            <>
              {displayAlerts.map((alert) => (
                <MenuItem
                  key={alert.id}
                  sx={{
                    py: 1.5,
                    px: 2,
                    alignItems: 'flex-start',
                    whiteSpace: 'normal',
                    borderLeft: 3,
                    borderColor: alert.severidad === 'critica' || alert.severity === 'critical'
                      ? '#d32f2f'
                      : alert.severidad === 'alta' || alert.severity === 'high'
                      ? '#f57c00'
                      : alert.severidad === 'media' || alert.severity === 'medium'
                      ? '#1976d2'
                      : '#388e3c',
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                  onClick={() => {
                    handleNotifClose();
                    navigate('/dashboard/alerts');
                  }}
                >
                  <ListItemIcon sx={{ mt: 0.5, minWidth: 36 }}>
                    {getSeverityIcon(alert.severity || alert.severidad)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.3 }}>
                        <Typography variant="body2" fontWeight={600} sx={{ flex: 1, lineHeight: 1.3 }}>
                          {(alert.title || alert.titulo || '').slice(0, 60)}
                          {(alert.title || alert.titulo || '').length > 60 ? '...' : ''}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, lineHeight: 1.3 }}>
                          {(alert.message || alert.descripcion || '').slice(0, 80)}
                          {(alert.message || alert.descripcion || '').length > 80 ? '...' : ''}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={getSeverityLabel(alert.severity || alert.severidad)}
                            size="small"
                            color={getSeverityColor(alert.severity || alert.severidad)}
                            sx={{ height: 18, fontSize: '0.65rem' }}
                          />
                          <Typography variant="caption" color="text.disabled">
                            {formatTimeAgo(alert.createdAt || alert.fechaDeteccion)}
                          </Typography>
                          {(alert.estado === 'nueva' || alert.status === 'new') && (
                            <Tooltip title="Marcar como leida">
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleMarkRead(String(alert.id));
                                }}
                                sx={{ p: 0.3, ml: 'auto' }}
                              >
                                <MarkReadIcon sx={{ fontSize: 16 }} />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </Box>
                    }
                  />
                </MenuItem>
              ))}

              {notificationCount > 5 && (
                <Box sx={{ px: 2, py: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" textAlign="center" display="block">
                    +{notificationCount - 5} alertas mas
                  </Typography>
                </Box>
              )}

              <Divider />
              <MenuItem
                onClick={handleGoToAlerts}
                sx={{ justifyContent: 'center', py: 1.5 }}
              >
                <OpenInNewIcon sx={{ mr: 1, fontSize: 18 }} />
                <Typography variant="body2" fontWeight={500} color="primary">
                  Ver todas las alertas ({notificationCount})
                </Typography>
              </MenuItem>
            </>
          )}
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
