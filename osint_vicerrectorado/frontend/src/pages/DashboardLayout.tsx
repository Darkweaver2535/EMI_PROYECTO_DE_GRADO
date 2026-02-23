/**
 * Layout principal del Dashboard
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { Box, Toolbar, useMediaQuery, useTheme as useMuiTheme } from '@mui/material';
import { Header, Sidebar, DRAWER_WIDTH, ErrorBoundary } from '../components/common';
import { useAuth } from '../contexts';
import { alertsService } from '../services';
import { Alert } from '../types';

const DashboardLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const muiTheme = useMuiTheme();
  const isMobile = useMediaQuery(muiTheme.breakpoints.down('md'));
  
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [alertCount, setAlertCount] = useState(0);
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    setSidebarOpen(!isMobile);
  }, [isMobile]);

  const loadAlerts = useCallback(async () => {
    try {
      const alerts = await alertsService.getActiveAlerts(100);
      setActiveAlerts(alerts);
      setAlertCount(alerts.length);
    } catch (err) {
      console.error('Error loading alerts:', err);
    }
  }, []);

  // Cargar alertas activas
  useEffect(() => {
    if (isAuthenticated) {
      loadAlerts();
      // Actualizar cada 5 minutos
      const interval = setInterval(loadAlerts, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, loadAlerts]);

  const handleMarkAlertRead = async (alertId: string) => {
    try {
      await alertsService.markAsRead(alertId);
      await loadAlerts();
    } catch (err) {
      console.error('Error marking alert as read:', err);
    }
  };

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
        alerts={activeAlerts}
        onMarkAlertRead={handleMarkAlertRead}
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
