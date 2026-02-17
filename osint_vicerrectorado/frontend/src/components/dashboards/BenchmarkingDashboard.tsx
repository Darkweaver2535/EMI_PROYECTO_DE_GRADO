/**
 * Dashboard de Benchmarking
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Avatar,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  EmojiEvents as TrophyIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Assessment as AssessmentIcon,
  School as SchoolIcon,
} from '@mui/icons-material';
import {
  KPICard,
  LoadingSpinner,
  ExportButton,
  DateRangePicker,
  EmptyState,
} from '../common';
import {
  CareerBarChart,
  RadarChart,
  CorrelationMatrixChart,
} from '../charts';
import { CareerFilter } from '../filters';
import { useFilters } from '../../contexts';
import { benchmarkingService } from '../../services';
import {
  CareerRanking,
  CorrelationMatrix,
  RadarProfileData,
} from '../../types';
import { CAREER_COLORS } from '../../utils';

type MetricType = 'mentions' | 'sentiment' | 'engagement' | 'overall';

const BenchmarkingDashboard: React.FC = () => {
  const { filters, setDateRange, setCareer, getApiParams } = useFilters();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rankings, setRankings] = useState<CareerRanking[]>([]);
  const [correlations, setCorrelations] = useState<CorrelationMatrix | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<RadarProfileData | null>(null);
  const [comparisonProfiles, setComparisonProfiles] = useState<RadarProfileData[]>([]);
  const [metric, setMetric] = useState<MetricType>('overall');
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = getApiParams();

      const [rankingsData, correlationsData] = await Promise.all([
        benchmarkingService.getCareerRanking({
          startDate: params.startDate,
          endDate: params.endDate,
          metric,
          limit: 20,
        }),
        benchmarkingService.getCorrelations({
          startDate: params.startDate,
          endDate: params.endDate,
        }),
      ]);

      setRankings(rankingsData);
      setCorrelations(correlationsData);

      // Cargar perfiles radar de las top 3 carreras para comparación
      if (rankingsData.length >= 3) {
        const profilePromises = rankingsData.slice(0, 3).map(career =>
          benchmarkingService.getRadarProfile({
            careerId: career.careerId,
            startDate: params.startDate,
            endDate: params.endDate,
          })
        );
        const profiles = await Promise.all(profilePromises);
        setComparisonProfiles(profiles);
      }
    } catch (err) {
      console.error('Error loading benchmarking data:', err);
      setError('Error al cargar los datos de benchmarking. Por favor, intente de nuevo.');
      
      // Datos de demostración
      setRankings([
        { careerId: '1', careerName: 'Ing. de Sistemas', mentions: 450, sentiment: 0.72, engagement: 1250, rank: 1 },
        { careerId: '2', careerName: 'Ing. Civil', mentions: 380, sentiment: 0.65, engagement: 980, rank: 2 },
        { careerId: '3', careerName: 'Ing. Comercial', mentions: 320, sentiment: 0.58, engagement: 850, rank: 3 },
        { careerId: '4', careerName: 'Administración', mentions: 280, sentiment: 0.62, engagement: 720, rank: 4 },
        { careerId: '5', careerName: 'Derecho', mentions: 250, sentiment: 0.55, engagement: 680, rank: 5 },
      ]);
      
      setCorrelations({
        variables: ['Menciones', 'Sentimiento', 'Engagement', 'Alcance'],
        values: [
          [1.0, 0.45, 0.78, 0.82],
          [0.45, 1.0, 0.32, 0.28],
          [0.78, 0.32, 1.0, 0.65],
          [0.82, 0.28, 0.65, 1.0],
        ],
      });
      
      setComparisonProfiles([
        {
          careerId: '1',
          careerName: 'Ing. de Sistemas',
          metrics: { sentiment: 72, mentions: 85, engagement: 78, visibility: 82, reputation: 75 },
        },
        {
          careerId: '2',
          careerName: 'Ing. Civil',
          metrics: { sentiment: 65, mentions: 72, engagement: 68, visibility: 70, reputation: 68 },
        },
        {
          careerId: '3',
          careerName: 'Ing. Comercial',
          metrics: { sentiment: 58, mentions: 60, engagement: 55, visibility: 58, reputation: 62 },
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [getApiParams, metric]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleMetricChange = (event: SelectChangeEvent<MetricType>) => {
    setMetric(event.target.value as MetricType);
  };

  const handleViewModeChange = (
    event: React.MouseEvent<HTMLElement>,
    newMode: 'chart' | 'table' | null
  ) => {
    if (newMode !== null) {
      setViewMode(newMode);
    }
  };

  const loadCareerProfile = async (careerId: string) => {
    try {
      const params = getApiParams();
      const profile = await benchmarkingService.getRadarProfile({
        careerId,
        startDate: params.startDate,
        endDate: params.endDate,
      });
      setSelectedProfile(profile);
    } catch (err) {
      console.error('Error loading career profile:', err);
    }
  };

  const getMetricLabel = (m: MetricType): string => {
    const labels: Record<MetricType, string> = {
      mentions: 'Menciones',
      sentiment: 'Sentimiento',
      engagement: 'Engagement',
      overall: 'Puntuación General',
    };
    return labels[m];
  };

  const getTopCareer = (): CareerRanking | undefined => rankings[0];
  const getBottomCareer = (): CareerRanking | undefined => rankings[rankings.length - 1];

  const getExportColumns = () => [
    { key: 'rank', header: 'Ranking' },
    { key: 'careerName', header: 'Carrera' },
    { key: 'mentions', header: 'Menciones' },
    { key: 'sentiment', header: 'Sentimiento' },
    { key: 'engagement', header: 'Engagement' },
  ];

  if (loading && rankings.length === 0) {
    return <LoadingSpinner message="Cargando análisis de benchmarking..." />;
  }

  const topCareer = getTopCareer();
  const bottomCareer = getBottomCareer();

  return (
    <Box id="benchmarking-dashboard">
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
          Benchmarking de Carreras
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
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Métrica</InputLabel>
            <Select
              value={metric}
              onChange={handleMetricChange}
              label="Métrica"
            >
              <MenuItem value="overall">General</MenuItem>
              <MenuItem value="mentions">Menciones</MenuItem>
              <MenuItem value="sentiment">Sentimiento</MenuItem>
              <MenuItem value="engagement">Engagement</MenuItem>
            </Select>
          </FormControl>
          <ExportButton
            elementId="benchmarking-dashboard"
            data={rankings.map((r, i) => ({ ...r, rank: i + 1 }))}
            columns={getExportColumns()}
            filename="benchmarking-emi"
            title="Benchmarking de Carreras - EMI"
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
            title="Carreras Analizadas"
            value={rankings.length}
            icon={<SchoolIcon />}
            color="primary"
            subtitle="en el período"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Mejor Carrera"
            value={topCareer?.careerName?.split(' ').slice(0, 2).join(' ') || '-'}
            icon={<TrophyIcon />}
            color="success"
            subtitle={`${topCareer?.mentions?.toLocaleString() || 0} menciones`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Mayor Crecimiento"
            value="+15.3%"
            icon={<TrendingUpIcon />}
            color="info"
            subtitle="vs período anterior"
            trend="up"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KPICard
            title="Requiere Atención"
            value={bottomCareer?.careerName?.split(' ').slice(0, 2).join(' ') || '-'}
            icon={<TrendingDownIcon />}
            color="warning"
            subtitle="menor rendimiento"
          />
        </Grid>
      </Grid>

      {/* Contenido principal */}
      <Grid container spacing={3}>
        {/* Ranking de carreras */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 500 }}>
                  Ranking por {getMetricLabel(metric)}
                </Typography>
                <ToggleButtonGroup
                  value={viewMode}
                  exclusive
                  onChange={handleViewModeChange}
                  size="small"
                >
                  <ToggleButton value="chart">Gráfico</ToggleButton>
                  <ToggleButton value="table">Tabla</ToggleButton>
                </ToggleButtonGroup>
              </Box>

              {rankings.length > 0 ? (
                viewMode === 'chart' ? (
                  <CareerBarChart
                    data={rankings.slice(0, 10)}
                    metric={metric === 'overall' ? 'mentions' : metric}
                    height={400}
                    horizontal
                    id="career-ranking-chart"
                  />
                ) : (
                  <TableContainer>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell width={60}>#</TableCell>
                          <TableCell>Carrera</TableCell>
                          <TableCell align="right">Menciones</TableCell>
                          <TableCell align="right">Sentimiento</TableCell>
                          <TableCell align="right">Engagement</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {rankings.map((career, index) => (
                          <TableRow
                            key={career.careerId}
                            hover
                            onClick={() => loadCareerProfile(career.careerId)}
                            sx={{ cursor: 'pointer' }}
                          >
                            <TableCell>
                              <Avatar
                                sx={{
                                  bgcolor: index < 3 
                                    ? ['#FFD700', '#C0C0C0', '#CD7F32'][index]
                                    : CAREER_COLORS[index % CAREER_COLORS.length],
                                  width: 32,
                                  height: 32,
                                  fontSize: '0.875rem',
                                }}
                              >
                                {index + 1}
                              </Avatar>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontWeight={500}>
                                {career.careerName}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              {career.mentions.toLocaleString()}
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                size="small"
                                label={`${(career.sentiment * 100).toFixed(0)}%`}
                                sx={{
                                  bgcolor: career.sentiment >= 0.6 
                                    ? 'success.light' 
                                    : career.sentiment >= 0.4 
                                    ? 'warning.light' 
                                    : 'error.light',
                                }}
                              />
                            </TableCell>
                            <TableCell align="right">
                              {career.engagement.toLocaleString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )
              ) : (
                <EmptyState
                  title="Sin datos de ranking"
                  message="No hay datos suficientes para generar el ranking."
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Perfil Radar */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                Comparación de Perfiles
              </Typography>
              {comparisonProfiles.length > 0 ? (
                <RadarChart
                  data={comparisonProfiles}
                  height={350}
                  showLegend
                  id="career-radar-chart"
                />
              ) : (
                <EmptyState
                  title="Sin perfiles"
                  message="Seleccione carreras para comparar sus perfiles."
                />
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Matriz de correlaciones */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              {correlations ? (
                <CorrelationMatrixChart
                  data={correlations}
                  title="Matriz de Correlaciones entre Métricas"
                  height={400}
                  id="correlation-matrix-chart"
                />
              ) : (
                <EmptyState
                  title="Sin datos de correlación"
                  message="No hay suficientes datos para calcular correlaciones."
                />
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default BenchmarkingDashboard;
