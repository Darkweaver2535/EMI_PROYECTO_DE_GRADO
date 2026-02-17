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
} from '@mui/material';
import {
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  AccountCircle,
  Logout as LogoutIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useAuth, useTheme } from '../../contexts';

interface HeaderProps {
  onMenuToggle?: () => void;
  title?: string;
  notificationCount?: number;
}

const Header: React.FC<HeaderProps> = ({
  onMenuToggle,
  title = 'Sistema OSINT - EMI Bolivia',
  notificationCount = 0,
}) => {
  const { user, logout } = useAuth();
  const { mode, toggleTheme } = useTheme();
  const muiTheme = useMuiTheme();
  
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

  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

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
            aria-label="abrir menú"
            edge="start"
            onClick={onMenuToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
        )}

        {/* Logo EMI */}
        <Box
          component="img"
          src="/assets/emi-logo.png"
          alt="EMI Logo"
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
          OSINT EMI
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
          <MenuItem onClick={handleMenuClose}>
            <SettingsIcon sx={{ mr: 1 }} fontSize="small" />
            Configuración
          </MenuItem>
          <MenuItem onClick={handleLogout}>
            <LogoutIcon sx={{ mr: 1 }} fontSize="small" />
            Cerrar sesión
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
            sx: { width: 320, maxHeight: 400 },
          }}
        >
          <MenuItem disabled sx={{ opacity: '1 !important' }}>
            <Typography variant="subtitle2" fontWeight="bold">
              Notificaciones
            </Typography>
          </MenuItem>
          {notificationCount === 0 ? (
            <MenuItem disabled>
              <Typography variant="body2" color="text.secondary">
                No hay notificaciones nuevas
              </Typography>
            </MenuItem>
          ) : (
            <MenuItem onClick={handleNotifClose}>
              <Typography variant="body2">
                Ver todas las alertas ({notificationCount})
              </Typography>
            </MenuItem>
          )}
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
