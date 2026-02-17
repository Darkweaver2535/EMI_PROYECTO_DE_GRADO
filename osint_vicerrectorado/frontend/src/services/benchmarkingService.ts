/**
 * Servicio de Benchmarking
 * Sistema OSINT EMI - Sprint 4
 */

import api from './api';
import {
  CareerRanking,
  CorrelationMatrix,
  RadarProfileData,
  CareerComparison,
} from '../types';

export interface GetCareerRankingParams {
  startDate: string;
  endDate: string;
  metric?: 'sentiment' | 'mentions' | 'engagement' | 'overall';
  limit?: number;
}

export interface GetCorrelationParams {
  startDate: string;
  endDate: string;
  variables?: string[];
}

export interface GetRadarProfileParams {
  careerId: string;
  startDate: string;
  endDate: string;
}

export interface GetComparisonParams {
  careerIds: string[];
  startDate: string;
  endDate: string;
}

export const benchmarkingService = {
  /**
   * Obtiene ranking de carreras por métrica
   */
  async getCareerRanking(params: GetCareerRankingParams): Promise<CareerRanking[]> {
    const { data } = await api.get<CareerRanking[]>('/ai/benchmarking/careers', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        metric: params.metric || 'overall',
        limit: params.limit || 20,
      },
    });
    return data;
  },

  /**
   * Obtiene matriz de correlaciones
   */
  async getCorrelations(params: GetCorrelationParams): Promise<CorrelationMatrix> {
    const { data } = await api.get<CorrelationMatrix>('/ai/benchmarking/correlations', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        variables: params.variables?.join(','),
      },
    });
    return data;
  },

  /**
   * Obtiene perfil radar de una carrera
   */
  async getRadarProfile(params: GetRadarProfileParams): Promise<RadarProfileData> {
    const { data } = await api.get<RadarProfileData>(`/ai/benchmarking/careers/${params.careerId}/profile`, {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene comparación entre múltiples carreras
   */
  async getCareerComparison(params: GetComparisonParams): Promise<CareerComparison[]> {
    const { data } = await api.get<CareerComparison[]>('/ai/benchmarking/compare', {
      params: {
        career_ids: params.careerIds.join(','),
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene tendencias históricas de una carrera
   */
  async getCareerTrends(params: {
    careerId: string;
    startDate: string;
    endDate: string;
    interval?: 'day' | 'week' | 'month';
  }): Promise<Array<{
    date: string;
    mentions: number;
    sentiment: number;
    engagement: number;
  }>> {
    const { data } = await api.get(`/ai/benchmarking/careers/${params.careerId}/trends`, {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        interval: params.interval || 'day',
      },
    });
    return data;
  },

  /**
   * Obtiene lista de todas las carreras disponibles
   */
  async getCareers(): Promise<Array<{ id: string; name: string; faculty: string }>> {
    const { data } = await api.get('/careers');
    return data;
  },

  /**
   * Obtiene métricas agregadas de todas las carreras
   */
  async getAggregateMetrics(params: { startDate: string; endDate: string }): Promise<{
    totalMentions: number;
    avgSentiment: number;
    topCareer: string;
    bottomCareer: string;
    medianEngagement: number;
  }> {
    const { data } = await api.get('/ai/benchmarking/aggregate', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Normaliza puntuaciones para comparación justa
   */
  normalizeScores(rankings: CareerRanking[]): CareerRanking[] {
    if (rankings.length === 0) return [];
    if (rankings.length === 1) {
      return rankings.map(r => ({ ...r, satisfactionScore: 100 }));
    }

    const scores = rankings.map(r => r.satisfactionScore);
    const min = Math.min(...scores);
    const max = Math.max(...scores);
    const range = max - min || 1;

    return rankings.map(r => ({
      ...r,
      satisfactionScore: Math.round(((r.satisfactionScore - min) / range) * 100),
    }));
  },

  /**
   * Calcula score overall de una carrera
   */
  calculateOverallScore(
    metrics: Record<string, number>,
    weights: Record<string, number>
  ): number {
    let totalWeight = 0;
    let weightedSum = 0;

    Object.keys(weights).forEach(key => {
      if (metrics[key] !== undefined) {
        weightedSum += metrics[key] * weights[key];
        totalWeight += weights[key];
      }
    });

    return totalWeight > 0 ? Math.round(weightedSum / totalWeight * totalWeight) : 0;
  },

  /**
   * Genera datos para gráfico radar desde perfil
   */
  formatRadarData(profile: RadarProfileData): Array<{ metric: string; value: number; fullMark: number }> {
    return Object.entries(profile.metrics).map(([metric, value]) => ({
      metric: formatMetricName(metric),
      value: typeof value === 'number' ? value : 0,
      fullMark: 100,
    }));
  },
};

/**
 * Formatea nombre de métrica para visualización
 */
function formatMetricName(metric: string): string {
  const names: Record<string, string> = {
    sentiment: 'Sentimiento',
    mentions: 'Menciones',
    engagement: 'Engagement',
    reach: 'Alcance',
    visibility: 'Visibilidad',
    reputation: 'Reputación',
    growth: 'Crecimiento',
  };
  return names[metric] || metric.charAt(0).toUpperCase() + metric.slice(1);
}

export default benchmarkingService;
