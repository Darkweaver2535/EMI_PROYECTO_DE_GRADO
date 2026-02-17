/**
 * Servicio de Análisis de Sentimientos
 * Sistema OSINT EMI - Sprint 4
 */

import api from './api';
import {
  SentimentData,
  SentimentDistribution,
  SentimentFilters,
  SentimentKPIs,
  TopPost,
  SentimentTrendResponse,
} from '../types';

export interface GetTrendParams extends SentimentFilters {}

export interface GetDistributionParams {
  startDate: string;
  endDate: string;
}

export interface GetTopPostsParams {
  type: 'positive' | 'negative';
  limit?: number;
  startDate?: string;
  endDate?: string;
}

export const sentimentService = {
  /**
   * Obtiene datos de tendencia de sentimientos
   */
  async getTrend(params: GetTrendParams): Promise<SentimentData[]> {
    const { data } = await api.get<SentimentTrendResponse | SentimentData[]>('/ai/sentiments/trend', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        source: params.source || undefined,
        career: params.career || undefined,
      },
    });
    
    // Handle both response formats
    if (Array.isArray(data)) {
      return data;
    }
    return data.data;
  },

  /**
   * Obtiene distribución actual de sentimientos
   */
  async getDistribution(params: GetDistributionParams): Promise<SentimentDistribution> {
    const { data } = await api.get<SentimentDistribution>('/ai/sentiments/distribution', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene posts más positivos o negativos
   */
  async getTopPosts(params: GetTopPostsParams): Promise<TopPost[]> {
    const { data } = await api.get<TopPost[]>('/ai/sentiments/top-posts', {
      params: {
        type: params.type,
        limit: params.limit || 10,
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene KPIs calculados de sentimientos
   */
  async getKPIs(params: SentimentFilters): Promise<SentimentKPIs> {
    const { data } = await api.get<SentimentKPIs>('/ai/sentiments/kpis', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        source: params.source || undefined,
        career: params.career || undefined,
      },
    });
    return data;
  },

  /**
   * Analiza sentimiento de textos específicos
   */
  async analyzeTexts(texts: string[]): Promise<{ results: Array<{ text: string; sentiment: string; confidence: number }> }> {
    const { data } = await api.post('/ai/analyze-sentiments', { texts });
    return data;
  },

  /**
   * Calcula KPIs desde distribución localmente
   */
  calculateKPIsFromDistribution(distribution: SentimentDistribution): SentimentKPIs {
    const total = distribution.total || (distribution.positive + distribution.negative + distribution.neutral);
    
    if (total === 0) {
      return {
        positivePercent: 0,
        negativePercent: 0,
        neutralPercent: 0,
        satisfactionIndex: 0,
        totalPosts: 0,
        trend: 'stable',
      };
    }

    const positivePercent = (distribution.positive / total) * 100;
    const negativePercent = (distribution.negative / total) * 100;
    const neutralPercent = (distribution.neutral / total) * 100;
    const satisfactionIndex = positivePercent - negativePercent;

    return {
      positivePercent: Math.round(positivePercent * 10) / 10,
      negativePercent: Math.round(negativePercent * 10) / 10,
      neutralPercent: Math.round(neutralPercent * 10) / 10,
      satisfactionIndex: Math.round(satisfactionIndex * 10) / 10,
      totalPosts: total,
      trend: satisfactionIndex > 0 ? 'up' : satisfactionIndex < 0 ? 'down' : 'stable',
    };
  },
};

export default sentimentService;
