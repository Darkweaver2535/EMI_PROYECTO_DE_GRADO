/**
 * Layout principal del Dashboard
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useState, useEffect } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Box, Toolbar, useMediaQuery, useTheme as useMuiTheme } from '@mui/material';
import { Header, Sidebar, DRAWER_WIDTH, ErrorBoundary } from '../components/common';
import { useAuth } from '../contexts';
import { alertsService } from '../services';

const DashboardLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const muiTheme = useMuiTheme();
  const isMobile = useMediaQuery(muiTheme.breakpoints.down('md'));
  
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    setSidebarOpen(!isMobile);
  }, [isMobile]);

  // Cargar contador de alertas activas
  useEffect(() => {
    const loadAlertCount = async () => {
      try {
        const alerts = await alertsService.getActiveAlerts(100);
        setAlertCount(alerts.length);
      } catch (err) {
        console.error('Error loading alert count:', err);
      }
    };

    if (isAuthenticated) {
      loadAlertCount();
      // Actualizar cada 5 minutos
      const interval = setInterval(loadAlertCount, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Mostrar loading mientras se verifica autenticación
  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        Cargando...
      </Box>
    );
  }

  // Redirigir a login si no está autenticado
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Header
        onMenuToggle={handleSidebarToggle}
        notificationCount={alertCount}
      />
      
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        variant={isMobile ? 'temporary' : 'permanent'}
      />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          minHeight: '100vh',
          backgroundColor: 'background.default',
        }}
      >
        <Toolbar /> {/* Spacer para el AppBar fijo */}
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </Box>
    </Box>
  );
};

export default DashboardLayout;
