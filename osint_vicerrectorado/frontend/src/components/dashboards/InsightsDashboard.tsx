/**
 * Dashboard de Insights (DeepSeek)
 * Sistema OSINT EMI
 *
 * Muestra el resumen ejecutivo dinámico generado por DeepSeek tras el
 * análisis BERT: estado de percepción, temas críticos, recomendaciones y
 * carreras destacadas. Permite disparar el análisis y ver su progreso.
 * Todos los datos provienen del backend; no hay valores estáticos.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  LinearProgress,
  Alert,
  Divider,
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  PlayArrow as PlayIcon,
  Warning as WarningIcon,
  Lightbulb as LightbulbIcon,
  School as SchoolIcon,
} from '@mui/icons-material';
import { KPICard, LoadingSpinner, EmptyState } from '../common';
import { deepseekService } from '../../services';
import { DeepSeekInsights, DeepSeekStatus } from '../../services/deepseekService';

const SEVERITY_COLOR: Record<string, 'default' | 'warning' | 'error' | 'info'> = {
  baja: 'info',
  media: 'warning',
  alta: 'error',
  critica: 'error',
};

const SENTIMENT_COLOR: Record<string, 'success' | 'warning' | 'error' | 'primary'> = {
  Positivo: 'success',
  Neutral: 'warning',
  Negativo: 'error',
};

const InsightsDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [insights, setInsights] = useState<DeepSeekInsights | null>(null);
  const [status, setStatus] = useState<DeepSeekStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [ins, st] = await Promise.all([
        deepseekService.getInsights(),
        deepseekService.getStatus(),
      ]);
      setInsights(ins);
      setStatus(st);
      setError(null);
    } catch (err) {
      console.error('Error cargando insights DeepSeek:', err);
      setError('No se pudieron cargar los insights de IA.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-refresco mientras hay un análisis en curso
  useEffect(() => {
    if (!status?.ejecutando) return;
    const id = setInterval(loadData, 5000);
    return () => clearInterval(id);
  }, [status?.ejecutando, loadData]);

  const handleRun = async () => {
    setLaunching(true);
    try {
      await deepseekService.ejecutar(false);
      await loadData();
    } catch (err) {
      console.error('Error ejecutando DeepSeek:', err);
      setError('No se pudo iniciar el análisis IA.');
    } finally {
      setLaunching(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Cargando insights de IA..." />;
  }

  const running = status?.ejecutando || launching;
  const progress = status && status.total > 0
    ? Math.round((status.analizados / status.total) * 100)
    : 0;

  return (
    <Box id="insights-dashboard">
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AIIcon color="primary" />
          <Typography variant="h4" component="h1" fontWeight={600}>
            Insights IA
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<PlayIcon />}
          onClick={handleRun}
          disabled={running}
        >
          {running ? 'Analizando...' : 'Ejecutar análisis IA'}
        </Button>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Estado / progreso */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Ítems analizados"
            value={status?.analizados ?? 0}
            icon={<AIIcon />}
            color="primary"
            subtitle={`de ${status?.total ?? 0} elegibles`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Pendientes"
            value={status?.pendientes ?? 0}
            icon={<PlayIcon />}
            color="warning"
            subtitle="por procesar"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Sentimiento general"
            value={insights?.sentimientoGeneral || '—'}
            icon={<WarningIcon />}
            color={SENTIMENT_COLOR[insights?.sentimientoGeneral || ''] || 'primary'}
            subtitle="percepción pública"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Temas críticos"
            value={insights?.temasCriticos?.length ?? 0}
            icon={<WarningIcon />}
            color="error"
            subtitle="detectados"
          />
        </Grid>
      </Grid>

      {running && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="body2" gutterBottom>
              Análisis en progreso: {progress}% ({status?.analizados}/{status?.total})
            </Typography>
            <LinearProgress variant="determinate" value={progress} />
          </CardContent>
        </Card>
      )}

      {!insights?.disponible ? (
        <EmptyState
          title="Sin análisis IA todavía"
          message="Ejecuta el análisis IA para generar el resumen ejecutivo dinámico a partir de los datos ya analizados."
        />
      ) : (
        <Grid container spacing={3}>
          {/* Resumen ejecutivo */}
          <Grid item xs={12} lg={8}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight={500}>
                  Resumen ejecutivo
                </Typography>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
                  {insights.resumenEjecutivo}
                </Typography>
                {insights.fecha && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                    Generado: {new Date(insights.fecha).toLocaleString()}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Recomendaciones */}
          <Grid item xs={12} lg={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight={500}>
                  Recomendaciones
                </Typography>
                {insights.recomendaciones && insights.recomendaciones.length > 0 ? (
                  <List dense>
                    {insights.recomendaciones.map((rec, i) => (
                      <ListItem key={i} disableGutters alignItems="flex-start">
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <LightbulbIcon color="warning" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText primary={rec} />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Sin recomendaciones.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Temas críticos */}
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight={500}>
                  Temas críticos
                </Typography>
                {insights.temasCriticos && insights.temasCriticos.length > 0 ? (
                  <List dense>
                    {insights.temasCriticos.map((t, i) => (
                      <React.Fragment key={i}>
                        <ListItem disableGutters alignItems="flex-start">
                          <ListItemIcon sx={{ minWidth: 32 }}>
                            <WarningIcon
                              color={SEVERITY_COLOR[t.severidad] === 'error' ? 'error' : 'warning'}
                              fontSize="small"
                            />
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" fontWeight={500}>{t.tema}</Typography>
                                <Chip
                                  size="small"
                                  label={t.severidad}
                                  color={SEVERITY_COLOR[t.severidad] || 'default'}
                                />
                              </Box>
                            }
                            secondary={t.descripcion}
                          />
                        </ListItem>
                        {i < insights.temasCriticos!.length - 1 && <Divider component="li" />}
                      </React.Fragment>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No se detectaron temas críticos.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Carreras destacadas */}
          <Grid item xs={12} lg={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom fontWeight={500}>
                  Carreras destacadas
                </Typography>
                {insights.carrerasDestacadas && insights.carrerasDestacadas.length > 0 ? (
                  <List dense>
                    {insights.carrerasDestacadas.map((c, i) => (
                      <ListItem key={i} disableGutters alignItems="flex-start">
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <SchoolIcon color="primary" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={c.careerName || `Carrera ${c.careerId}`}
                          secondary={c.observacion || (c.menciones != null ? `${c.menciones} menciones` : undefined)}
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Sin carreras destacadas.
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default InsightsDashboard;
