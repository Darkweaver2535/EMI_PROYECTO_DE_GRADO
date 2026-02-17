/**
 * Dashboard de Reputación
 * Sistema OSINT EMI - Sprint 4
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  Avatar,
  Paper,
} from '@mui/material';
import {
  Stars as ReputationIcon,
  Visibility as VisibilityIcon,
  TrendingUp as TrendingUpIcon,
  Forum as ForumIcon,
} from '@mui/icons-material';
import {
  KPICard,
  LoadingSpinner,
  ExportButton,
  DateRangePicker,
  EmptyState,
} from '../common';
import {
  WordCloudChart,
  HeatmapChart,
  CareerBarChart,
} from '../charts';
import { SourceFilter } from '../filters';
import { useFilters } from '../../contexts';
import { reputationService } from '../../services';
import {
  WordCloudWord,
  HeatmapData,
  TopicCluster,
  CompetitorData,
} from '../../types';
import { CAREER_COLORS } from '../../utils';

const ReputationDashboard: React.FC = () => {
  const { filters, setDateRange, setSource, getApiParams } = useFilters();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wordCloudData, setWordCloudData] = useState<WordCloudWord[]>([]);
  const [heatmapData, setHeatmapData] = useState<HeatmapData[]>([]);
  const [topics, setTopics] = useState<TopicCluster[]>([]);
  const [competitors, setCompetitors] = useState<CompetitorData[]>([]);
  const [metrics, setMetrics] = useState<{
    overallScore: number;
    mentionVolume: number;
    sentimentScore: number;
    engagementRate: number;
    reachEstimate: number;
    trend: 'up' | 'down' | 'stable';
  } | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = getApiParams();

      const [wordCloud, heatmap, topicsData, competitorsData, metricsData] = await Promise.all([
        reputationService.getWordCloud({
          startDate: params.startDate,
          endDate: params.endDate,
          source: params.source,
        }),
        reputationService.getHeatmap({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
        reputationService.getTopics({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
        reputationService.getCompetitors({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
        reputationService.getReputationMetrics({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
      ]);

      setWordCloudData(wordCloud);
      setHeatmapData(heatmap);
      setTopics(topicsData);
      setCompetitors(competitorsData);
      setMetrics(metricsData);
    } catch (err) {
      console.error('Error loading reputation data:', err);
      setError('Error al cargar los datos de reputación. Por favor, intente de nuevo.');
      
      // Datos de demostración para desarrollo
      setWordCloudData([
        { text: 'EMI', value: 150 },
        { text: 'ingeniería', value: 120 },
        { text: 'carrera', value: 100 },
        { text: 'universidad', value: 90 },
        { text: 'Bolivia', value: 85 },
        { text: 'militar', value: 80 },
        { text: 'educación', value: 75 },
        { text: 'estudiantes', value: 70 },
        { text: 'sistemas', value: 65 },
        { text: 'tecnología', value: 60 },
      ]);
      
      setMetrics({
        overallScore: 78,
        mentionVolume: 1250,
        sentimentScore: 0.65,
        engagementRate: 3.2,
        reachEstimate: 45000,
        trend: 'up',
      });
    } finally {
      setLoading(false);
    }
  }, [getApiParams]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleWordClick = (word: WordCloudWord) => {
    console.log('Word clicked:', word);
    // Aquí se podría abrir un modal con detalles del término
  };

  const getExportColumns = () => [
    { key: 'text', header: 'Término' },
    { key: 'value', header: 'Frecuencia' },
  ];

  if (loading) {
    return <LoadingSpinner message="Cargando análisis de reputación..." />;
  }

  return (
    <Box id="reputation-dashboard">
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
          Dashboard de Reputación
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
          <SourceFilter
            value={filters.source}
            onChange={setSource}
          />
          <ExportButton
            elementId="reputation-dashboard"
            data={wordCloudData}
            columns={getExportColumns()}
            filename="reputacion-emi"
            title="Análisis de Reputación - EMI"
          />
        </Box>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* KPIs */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Puntuación General"
            value={`${metrics?.overallScore || 0}/100`}
            icon={<ReputationIcon />}
            color="primary"
            trend={metrics?.trend}
            subtitle="índice de reputación"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Volumen de Menciones"
            value={metrics?.mentionVolume?.toLocaleString() || '0'}
            icon={<ForumIcon />}
            color="info"
            subtitle="en el período"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Tasa de Engagement"
            value={`${metrics?.engagementRate?.toFixed(1) || 0}%`}
            icon={<TrendingUpIcon />}
            color="success"
            subtitle="interacciones/publicación"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Alcance Estimado"
            value={metrics?.reachEstimate?.toLocaleString() || '0'}
            icon={<VisibilityIcon />}
            color="warning"
            subtitle="personas alcanzadas"
          />
        </Grid>
      </Grid>

      {/* Contenido principal */}
      <Grid container spacing={3}>
        {/* Nube de palabras */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              {wordCloudData.length > 0 ? (
                <WordCloudChart
                  data={wordCloudData}
                  title="Términos Más Mencionados"
                  height={350}
                  onWordClick={handleWordClick}
                  id="reputation-wordcloud"
                />
              ) : (
                <EmptyState
                  title="Sin datos"
                  message="No hay suficientes datos para generar la nube de palabras."
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Temas detectados */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                Temas Detectados
              </Typography>
              {topics.length > 0 ? (
                <List>
                  {topics.slice(0, 6).map((topic, index) => (
                    <ListItem
                      key={topic.id}
                      sx={{
                        borderLeft: `4px solid ${CAREER_COLORS[index % CAREER_COLORS.length]}`,
                        mb: 1,
                        bgcolor: 'background.default',
                        borderRadius: 1,
                      }}
                    >
                      <ListItemText
                        primary={topic.name}
                        secondary={
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                            {topic.keywords.slice(0, 4).map((keyword) => (
                              <Chip
                                key={keyword}
                                label={keyword}
                                size="small"
                                variant="outlined"
                              />
                            ))}
                          </Box>
                        }
                      />
                      <Chip
                        label={`${topic.count}`}
                        size="small"
                        color="primary"
                        sx={{ ml: 1 }}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <EmptyState
                  title="Sin temas"
                  message="No se detectaron temas específicos en el período."
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Heatmap de actividad */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              {heatmapData.length > 0 ? (
                <HeatmapChart
                  data={heatmapData}
                  title="Actividad por Día y Hora"
                  height={300}
                  id="reputation-heatmap"
                />
              ) : (
                <Box sx={{ py: 4 }}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                    Actividad por Día y Hora
                  </Typography>
                  <EmptyState
                    title="Sin datos de actividad"
                    message="No hay datos de actividad temporal disponibles."
                  />
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Comparación con competidores */}
        <Grid item xs={12} lg={6}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                Comparación con Otras Instituciones
              </Typography>
              {competitors.length > 0 ? (
                <List>
                  {competitors.slice(0, 5).map((competitor, index) => (
                    <ListItem
                      key={competitor.name}
                      sx={{
                        py: 1.5,
                        borderBottom: index < competitors.length - 1 ? 1 : 0,
                        borderColor: 'divider',
                      }}
                    >
                      <Avatar
                        sx={{
                          bgcolor: CAREER_COLORS[index % CAREER_COLORS.length],
                          width: 36,
                          height: 36,
                          mr: 2,
                        }}
                      >
                        {index + 1}
                      </Avatar>
                      <ListItemText
                        primary={competitor.name}
                        secondary={`${competitor.mentions.toLocaleString()} menciones`}
                      />
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          color={competitor.sentiment >= 0 ? 'success.main' : 'error.main'}
                        >
                          {competitor.sentiment >= 0 ? '+' : ''}
                          {(competitor.sentiment * 100).toFixed(0)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          sentimiento
                        </Typography>
                      </Box>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <EmptyState
                  title="Sin datos de comparación"
                  message="No hay datos de otras instituciones para comparar."
                />
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ReputationDashboard;
