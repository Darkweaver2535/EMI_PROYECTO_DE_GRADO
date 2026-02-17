/**
 * Componente ReportProgress
 * Muestra el progreso de generación de reportes
 * Sistema de Analítica OSINT - EMI Bolivia
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Button,
  Chip,
  IconButton,
  Alert,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Divider
} from '@mui/material';
import {
  Download as DownloadIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon
} from '@mui/icons-material';

import { TaskStatusResponse } from '../../types/reports.types';
import reportsService, { getStatusColor, getReportIcon, getReportTypeName } from '../../services/reportsService';

// Colores EMI
const EMI_GREEN = '#1B5E20';
const EMI_GOLD = '#FFD700';

interface TaskInfo {
  taskId: string;
  reportType: string;
  startTime: Date;
  status?: TaskStatusResponse;
}

interface ReportProgressProps {
  tasks: TaskInfo[];
  onTaskComplete?: (taskId: string, result: TaskStatusResponse) => void;
  onRemoveTask?: (taskId: string) => void;
}

const ReportProgress: React.FC<ReportProgressProps> = ({
  tasks,
  onTaskComplete,
  onRemoveTask
}) => {
  const [taskStatuses, setTaskStatuses] = useState<Record<string, TaskStatusResponse>>({});
  const [expanded, setExpanded] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  // Polling de estado para tareas activas
  useEffect(() => {
    const activeTasks = tasks.filter(t => {
      const status = taskStatuses[t.taskId];
      return !status || (status.status !== 'SUCCESS' && status.status !== 'FAILURE');
    });

    if (activeTasks.length === 0) return;

    const pollInterval = setInterval(async () => {
      for (const task of activeTasks) {
        try {
          const status = await reportsService.getTaskStatus(task.taskId);
          setTaskStatuses(prev => ({
            ...prev,
            [task.taskId]: status
          }));

          if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
            if (onTaskComplete) {
              onTaskComplete(task.taskId, status);
            }
          }
        } catch (error) {
          console.error(`Error polling task ${task.taskId}:`, error);
        }
      }
    }, 1500);

    return () => clearInterval(pollInterval);
  }, [tasks, taskStatuses, onTaskComplete]);

  // Descargar reporte completado
  const handleDownload = async (taskId: string) => {
    const status = taskStatuses[taskId];
    if (!status?.download_url) return;

    setDownloading(taskId);
    try {
      const filename = status.download_url.split('/').pop() || 'reporte';
      await reportsService.downloadAndSaveReport(filename);
    } catch (error) {
      console.error('Error downloading report:', error);
    } finally {
      setDownloading(null);
    }
  };

  // Obtener ícono de estado
  const getStatusIcon = (status?: TaskStatusResponse) => {
    if (!status) return <PendingIcon color="action" />;
    
    switch (status.status) {
      case 'SUCCESS':
        return <SuccessIcon sx={{ color: EMI_GREEN }} />;
      case 'FAILURE':
        return <ErrorIcon color="error" />;
      case 'PROGRESS':
      case 'STARTED':
        return <RefreshIcon color="primary" sx={{ animation: 'spin 1s linear infinite' }} />;
      default:
        return <PendingIcon color="action" />;
    }
  };

  // Formatear tiempo transcurrido
  const getElapsedTime = (startTime: Date): string => {
    const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000);
    if (elapsed < 60) return `${elapsed}s`;
    return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
  };

  if (tasks.length === 0) {
    return null;
  }

  return (
    <Card elevation={2} sx={{ mb: 3 }}>
      <CardContent sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6" sx={{ color: EMI_GREEN, fontWeight: 600 }}>
            ⏳ Tareas en Progreso ({tasks.length})
          </Typography>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <List disablePadding>
            {tasks.map((task, index) => {
              const status = taskStatuses[task.taskId];
              const progress = status?.progress || 0;
              const isComplete = status?.status === 'SUCCESS';
              const isFailed = status?.status === 'FAILURE';

              return (
                <React.Fragment key={task.taskId}>
                  {index > 0 && <Divider />}
                  <ListItem
                    sx={{
                      py: 2,
                      bgcolor: isComplete ? 'rgba(27, 94, 32, 0.05)' : isFailed ? 'rgba(211, 47, 47, 0.05)' : 'transparent'
                    }}
                  >
                    <ListItemIcon>
                      {getStatusIcon(status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="subtitle2">
                            {getReportIcon(task.reportType)} {getReportTypeName(task.reportType)}
                          </Typography>
                          <Chip
                            label={status?.status || 'PENDING'}
                            size="small"
                            color={
                              status?.status === 'SUCCESS' ? 'success' :
                              status?.status === 'FAILURE' ? 'error' :
                              'default'
                            }
                          />
                          <Typography variant="caption" color="text.secondary">
                            {getElapsedTime(task.startTime)}
                          </Typography>
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 1 }}>
                          {!isComplete && !isFailed && (
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={progress}
                                sx={{
                                  flex: 1,
                                  height: 8,
                                  borderRadius: 4,
                                  bgcolor: 'rgba(0,0,0,0.1)',
                                  '& .MuiLinearProgress-bar': {
                                    bgcolor: EMI_GREEN
                                  }
                                }}
                              />
                              <Typography variant="caption" sx={{ minWidth: 40 }}>
                                {progress}%
                              </Typography>
                            </Box>
                          )}
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                            {status?.message || 'Esperando en cola...'}
                          </Typography>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      {isComplete && status?.download_url && (
                        <Button
                          variant="contained"
                          size="small"
                          startIcon={<DownloadIcon />}
                          onClick={() => handleDownload(task.taskId)}
                          disabled={downloading === task.taskId}
                          sx={{ bgcolor: EMI_GREEN, '&:hover': { bgcolor: '#0d3f14' } }}
                        >
                          {downloading === task.taskId ? 'Descargando...' : 'Descargar'}
                        </Button>
                      )}
                      {(isComplete || isFailed) && onRemoveTask && (
                        <IconButton
                          size="small"
                          onClick={() => onRemoveTask(task.taskId)}
                          sx={{ ml: 1 }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                </React.Fragment>
              );
            })}
          </List>
        </Collapse>
      </CardContent>

      {/* Estilos para animación de spinner */}
      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}
      </style>
    </Card>
  );
};

export default ReportProgress;
