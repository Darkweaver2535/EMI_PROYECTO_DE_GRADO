/**
 * Dashboard de Análisis de Sentimientos
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
  ListItemIcon,
  Divider,
  Paper,
  Tabs,
  Tab,
} from '@mui/material';
import {
  SentimentSatisfiedAlt as PositiveIcon,
  SentimentVeryDissatisfied as NegativeIcon,
  SentimentNeutral as NeutralIcon,
  TrendingUp,
  TrendingDown,
} from '@mui/icons-material';
import {
  KPICard,
  LoadingSpinner,
  ExportButton,
  DateRangePicker,
  EmptyState,
} from '../common';
import {
  SentimentLineChart,
  SentimentPieChart,
} from '../charts';
import { SourceFilter, CareerFilter } from '../filters';
import { useFilters } from '../../contexts';
import { sentimentService } from '../../services';
import {
  SentimentData,
  SentimentDistribution,
  SentimentKPIs,
  TopPost,
} from '../../types';
import { formatDateDisplay, SENTIMENT_COLORS } from '../../utils';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
  </div>
);

const SentimentDashboard: React.FC = () => {
  const { filters, setDateRange, setSource, setCareer, getApiParams } = useFilters();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trendData, setTrendData] = useState<SentimentData[]>([]);
  const [distribution, setDistribution] = useState<SentimentDistribution | null>(null);
  const [kpis, setKPIs] = useState<SentimentKPIs | null>(null);
  const [topPositive, setTopPositive] = useState<TopPost[]>([]);
  const [topNegative, setTopNegative] = useState<TopPost[]>([]);
  const [postsTab, setPostsTab] = useState(0);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = getApiParams();

      const [trend, dist, positive, negative] = await Promise.all([
        sentimentService.getTrend(params),
        sentimentService.getDistribution({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
        sentimentService.getTopPosts({
          type: 'positive',
          limit: 10,
          startDate: params.startDate,
          endDate: params.endDate,
        }),
        sentimentService.getTopPosts({
          type: 'negative',
          limit: 10,
          startDate: params.startDate,
          endDate: params.endDate,
        }),
      ]);

      setTrendData(trend);
      setDistribution(dist);
      setTopPositive(positive);
      setTopNegative(negative);

      // Calcular KPIs desde distribución
      const calculatedKPIs = sentimentService.calculateKPIsFromDistribution(dist);
      setKPIs(calculatedKPIs);
    } catch (err) {
      console.error('Error loading sentiment data:', err);
      setError('Error al cargar los datos de sentimientos. Por favor, intente de nuevo.');
    } finally {
      setLoading(false);
    }
  }, [getApiParams]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return <PositiveIcon sx={{ color: SENTIMENT_COLORS.positive }} />;
      case 'negative':
        return <NegativeIcon sx={{ color: SENTIMENT_COLORS.negative }} />;
      default:
        return <NeutralIcon sx={{ color: SENTIMENT_COLORS.neutral }} />;
    }
  };

  const getExportColumns = () => [
    { key: 'date', header: 'Fecha' },
    { key: 'positive', header: 'Positivo (%)' },
    { key: 'negative', header: 'Negativo (%)' },
    { key: 'neutral', header: 'Neutro (%)' },
  ];

  if (loading) {
    return <LoadingSpinner message="Cargando análisis de sentimientos..." />;
  }

  return (
    <Box id="sentiment-dashboard">
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
          Análisis de Sentimientos
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
          <CareerFilter
            value={filters.career}
            onChange={setCareer}
          />
          <ExportButton
            elementId="sentiment-dashboard"
            data={trendData}
            columns={getExportColumns()}
            filename="sentimientos-emi"
            title="Análisis de Sentimientos - EMI"
          />
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* KPIs */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Posts Positivos"
            value={`${kpis?.positivePercent?.toFixed(1) || 0}%`}
            icon={<PositiveIcon />}
            color="success"
            trend={kpis?.trend === 'up' ? 'up' : kpis?.trend === 'down' ? 'down' : 'stable'}
            subtitle="del total analizado"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Posts Negativos"
            value={`${kpis?.negativePercent?.toFixed(1) || 0}%`}
            icon={<NegativeIcon />}
            color="error"
            subtitle="requieren atención"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Índice de Satisfacción"
            value={`${kpis?.satisfactionIndex?.toFixed(1) || 0}`}
            icon={kpis?.satisfactionIndex && kpis.satisfactionIndex >= 0 ? <TrendingUp /> : <TrendingDown />}
            color={kpis?.satisfactionIndex && kpis.satisfactionIndex >= 0 ? 'success' : 'error'}
            subtitle="positivo - negativo"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Total Analizado"
            value={kpis?.totalPosts?.toLocaleString() || '0'}
            icon={<NeutralIcon />}
            color="info"
            subtitle="publicaciones"
          />
        </Grid>
      </Grid>

      {/* Gráficos principales */}
      <Grid container spacing={3}>
        {/* Tendencia de sentimientos */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              {trendData.length > 0 ? (
                <SentimentLineChart
                  data={trendData}
                  title="Tendencia de Sentimientos"
                  height={350}
                  id="sentiment-trend-chart"
                />
              ) : (
                <EmptyState
                  title="Sin datos de tendencia"
                  message="No hay datos suficientes para mostrar la tendencia en el período seleccionado."
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Distribución actual */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              {distribution ? (
                <SentimentPieChart
                  data={distribution}
                  title="Distribución Actual"
                  height={350}
                  id="sentiment-distribution-chart"
                />
              ) : (
                <EmptyState
                  title="Sin datos"
                  message="No hay datos de distribución disponibles."
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Posts destacados */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                Publicaciones Destacadas
              </Typography>
              
              <Tabs
                value={postsTab}
                onChange={(_, newValue) => setPostsTab(newValue)}
                sx={{ borderBottom: 1, borderColor: 'divider' }}
              >
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PositiveIcon sx={{ color: SENTIMENT_COLORS.positive }} />
                      <span>Más Positivas ({topPositive.length})</span>
                    </Box>
                  }
                />
                <Tab
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <NegativeIcon sx={{ color: SENTIMENT_COLORS.negative }} />
                      <span>Más Negativas ({topNegative.length})</span>
                    </Box>
                  }
                />
              </Tabs>

              <TabPanel value={postsTab} index={0}>
                {topPositive.length > 0 ? (
                  <List>
                    {topPositive.map((post, index) => (
                      <React.Fragment key={post.id}>
                        {index > 0 && <Divider />}
                        <ListItem alignItems="flex-start">
                          <ListItemIcon sx={{ mt: 1 }}>
                            {getSentimentIcon('positive')}
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                <Typography variant="body1" component="span">
                                  {post.text.length > 200 ? `${post.text.substring(0, 200)}...` : post.text}
                                </Typography>
                              </Box>
                            }
                            secondary={
                              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                                <Chip
                                  size="small"
                                  label={post.source}
                                  variant="outlined"
                                />
                                <Chip
                                  size="small"
                                  label={`Score: ${(post.sentimentScore * 100).toFixed(0)}%`}
                                  sx={{
                                    bgcolor: SENTIMENT_COLORS.positive + '20',
                                    color: SENTIMENT_COLORS.positive,
                                  }}
                                />
                                <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                                  {formatDateDisplay(post.date)}
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      </React.Fragment>
                    ))}
                  </List>
                ) : (
                  <EmptyState
                    title="Sin publicaciones positivas"
                    message="No se encontraron publicaciones positivas en el período seleccionado."
                  />
                )}
              </TabPanel>

              <TabPanel value={postsTab} index={1}>
                {topNegative.length > 0 ? (
                  <List>
                    {topNegative.map((post, index) => (
                      <React.Fragment key={post.id}>
                        {index > 0 && <Divider />}
                        <ListItem alignItems="flex-start">
                          <ListItemIcon sx={{ mt: 1 }}>
                            {getSentimentIcon('negative')}
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                <Typography variant="body1" component="span">
                                  {post.text.length > 200 ? `${post.text.substring(0, 200)}...` : post.text}
                                </Typography>
                              </Box>
                            }
                            secondary={
                              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                                <Chip
                                  size="small"
                                  label={post.source}
                                  variant="outlined"
                                />
                                <Chip
                                  size="small"
                                  label={`Score: ${(Math.abs(post.sentimentScore) * 100).toFixed(0)}%`}
                                  sx={{
                                    bgcolor: SENTIMENT_COLORS.negative + '20',
                                    color: SENTIMENT_COLORS.negative,
                                  }}
                                />
                                <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
                                  {formatDateDisplay(post.date)}
                                </Typography>
                              </Box>
                            }
                          />
                        </ListItem>
                      </React.Fragment>
                    ))}
                  </List>
                ) : (
                  <EmptyState
                    title="Sin publicaciones negativas"
                    message="No se encontraron publicaciones negativas en el período seleccionado."
                  />
                )}
              </TabPanel>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SentimentDashboard;
