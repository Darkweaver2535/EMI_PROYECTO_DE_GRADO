/**
 * Página ReportsCenter
 * Centro principal de generación de reportes
 * Sistema de Analítica OSINT - EMI Bolivia
 * Sprint 5: Reportes y Estadísticas
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Paper,
  Alert,
  Snackbar,
  Divider
} from '@mui/material';
import {
  Description as ReportIcon,
  History as HistoryIcon,
  Analytics as StatsIcon
} from '@mui/icons-material';

// Componentes
import ReportBuilder from '../components/reports/ReportBuilder';
import ReportProgress from '../components/reports/ReportProgress';
import ReportHistory from '../components/reports/ReportHistory';

// Tipos y servicios
import { TaskStatusResponse, ReportsStats } from '../types/reports.types';
import reportsService from '../services/reportsService';

// Colores EMI
const EMI_BLUE = '#0D47A1';
const EMI_GOLD = '#FFD700';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`reports-tabpanel-${index}`}
      aria-labelledby={`reports-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

interface TaskInfo {
  taskId: string;
  reportType: string;
  startTime: Date;
}

const ReportsCenter: React.FC = () => {
  // Estado de la pestaña activa
  const [tabValue, setTabValue] = useState(0);
  
  // Estado de tareas en progreso
  const [activeTasks, setActiveTasks] = useState<TaskInfo[]>([]);
  
  // Estado de estadísticas
  const [stats, setStats] = useState<ReportsStats | null>(null);
  
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

  // Cargar estadísticas al montar
  useEffect(() => {
    loadStats();
  }, []);

  // Cargar estadísticas
  const loadStats = async () => {
    try {
      const response = await reportsService.getReportsStats();
      if (response.success && response.stats) {
        setStats(response.stats);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  // Manejar reporte generado
  const handleReportGenerated = (taskId: string, reportType: string) => {
    setActiveTasks(prev => [
      ...prev,
      { taskId, reportType, startTime: new Date() }
    ]);
    
    setNotification({
      open: true,
      message: 'Generación de reporte iniciada',
      severity: 'info'
    });
  };

  // Manejar tarea completada
  const handleTaskComplete = (taskId: string, result: TaskStatusResponse) => {
    if (result.status === 'SUCCESS') {
      setNotification({
        open: true,
        message: '¡Reporte generado exitosamente!',
        severity: 'success'
      });
      loadStats(); // Actualizar estadísticas
    } else if (result.status === 'FAILURE') {
      setNotification({
        open: true,
        message: 'Error generando el reporte',
        severity: 'error'
      });
    }
  };

  // Remover tarea de la lista
  const handleRemoveTask = (taskId: string) => {
    setActiveTasks(prev => prev.filter(t => t.taskId !== taskId));
  };

  // Manejar error
  const handleError = (error: string) => {
    setNotification({
      open: true,
      message: error,
      severity: 'error'
    });
  };

  return (
    <Box sx={{ bgcolor: '#f5f5f5', minHeight: '100vh', py: 4 }}>
      <Container maxWidth="xl">
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" sx={{ color: EMI_BLUE, fontWeight: 700, mb: 1 }}>
            Centro de Reportes
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Genere reportes PDF y Excel del análisis de percepción institucional
          </Typography>
        </Box>

        {/* Estadísticas rápidas */}
        {stats && (
          <Grid container spacing={2} sx={{ mb: 4 }}>
            <Grid item xs={6} md={3}>
              <Card elevation={1}>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="h4" sx={{ color: EMI_BLUE, fontWeight: 700 }}>
                    {stats.reports.total_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Reportes Generados
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card elevation={1}>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="h4" sx={{ color: '#1976d2', fontWeight: 700 }}>
                    {stats.reports.pdf_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    PDFs
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card elevation={1}>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="h4" sx={{ color: '#1565C0', fontWeight: 700 }}>
                    {stats.reports.excel_count}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Excel
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} md={3}>
              <Card elevation={1}>
                <CardContent sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="h4" sx={{ color: '#ed6c02', fontWeight: 700 }}>
                    {stats.reports.total_size_mb} MB
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Espacio Usado
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Tareas en progreso */}
        {activeTasks.length > 0 && (
          <ReportProgress
            tasks={activeTasks}
            onTaskComplete={handleTaskComplete}
            onRemoveTask={handleRemoveTask}
          />
        )}

        {/* Pestañas */}
        <Paper elevation={2} sx={{ mb: 4 }}>
          <Tabs
            value={tabValue}
            onChange={(_, newValue) => setTabValue(newValue)}
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              '& .MuiTab-root': {
                fontWeight: 600
              },
              '& .Mui-selected': {
                color: EMI_BLUE
              },
              '& .MuiTabs-indicator': {
                bgcolor: EMI_BLUE
              }
            }}
          >
            <Tab
              icon={<ReportIcon />}
              iconPosition="start"
              label="Generar Reporte"
            />
            <Tab
              icon={<HistoryIcon />}
              iconPosition="start"
              label="Historial"
            />
          </Tabs>

          <Box sx={{ p: 3 }}>
            <TabPanel value={tabValue} index={0}>
              <ReportBuilder
                onReportGenerated={handleReportGenerated}
                onError={handleError}
              />
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <ReportHistory />
            </TabPanel>
          </Box>
        </Paper>

        {/* Información adicional */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card elevation={1}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ color: EMI_BLUE }}>
                  Tipos de Reportes PDF
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Box component="ul" sx={{ pl: 2, '& li': { mb: 1 } }}>
                  <li>
                    <strong>Reporte Ejecutivo:</strong> Resumen semanal con KPIs, gráficos de tendencias y recomendaciones (8-12 páginas)
                  </li>
                  <li>
                    <strong>Reporte de Alertas:</strong> Detalle de alertas críticas con timeline y acciones recomendadas (4-6 páginas)
                  </li>
                  <li>
                    <strong>Anuario Estadístico:</strong> Análisis semestral completo con todos los indicadores (30-50 páginas)
                  </li>
                  <li>
                    <strong>Reporte por Carrera:</strong> Análisis específico de una carrera con comparativas (10-15 páginas)
                  </li>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Card elevation={1}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ color: EMI_BLUE }}>
                  Tipos de Reportes Excel
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Box component="ul" sx={{ pl: 2, '& li': { mb: 1 } }}>
                  <li>
                    <strong>Dataset de Sentimientos:</strong> Datos completos con múltiples hojas de análisis y gráficos
                  </li>
                  <li>
                    <strong>Tabla Pivote:</strong> Análisis agregado por carrera, fuente o mes
                  </li>
                  <li>
                    <strong>Reporte de Anomalías:</strong> Detección de patrones anómalos con alertas
                  </li>
                  <li>
                    <strong>Reporte Combinado:</strong> Todas las métricas consolidadas en un solo archivo
                  </li>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>

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

export default ReportsCenter;
