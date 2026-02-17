/**
 * Servicio de Análisis de Reputación
 * Sistema OSINT EMI - Sprint 4
 */

import api from './api';
import {
  WordCloudWord,
  HeatmapData,
  CompetitorData,
  TopicCluster,
} from '../types';

export interface GetWordCloudParams {
  startDate: string;
  endDate: string;
  source?: string;
  minFrequency?: number;
}

export interface GetHeatmapParams {
  startDate: string;
  endDate: string;
}

export interface GetTopicsParams {
  startDate: string;
  endDate: string;
  minClusterSize?: number;
}

export interface GetCompetitorsParams {
  startDate: string;
  endDate: string;
}

export const reputationService = {
  /**
   * Obtiene datos para nube de palabras
   */
  async getWordCloud(params: GetWordCloudParams): Promise<WordCloudWord[]> {
    const { data } = await api.get<WordCloudWord[]>('/ai/reputation/wordcloud', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        source: params.source || undefined,
        min_frequency: params.minFrequency || 3,
      },
    });
    return data;
  },

  /**
   * Obtiene clusters temáticos
   */
  async getTopics(params: GetTopicsParams): Promise<TopicCluster[]> {
    const { data } = await api.get<TopicCluster[]>('/ai/reputation/topics', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        min_cluster_size: params.minClusterSize || 5,
      },
    });
    return data;
  },

  /**
   * Obtiene datos para heatmap de actividad
   */
  async getHeatmap(params: GetHeatmapParams): Promise<HeatmapData[]> {
    const { data } = await api.get<HeatmapData[]>('/ai/reputation/heatmap', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene análisis comparativo con competidores
   */
  async getCompetitors(params: GetCompetitorsParams): Promise<CompetitorData[]> {
    const { data } = await api.get<CompetitorData[]>('/ai/reputation/competitors', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene métricas generales de reputación
   */
  async getReputationMetrics(params: { startDate: string; endDate: string }): Promise<{
    overallScore: number;
    mentionVolume: number;
    sentimentScore: number;
    engagementRate: number;
    reachEstimate: number;
    trend: 'up' | 'down' | 'stable';
  }> {
    const { data } = await api.get('/ai/reputation/metrics', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Genera nube de palabras desde datos locales
   */
  generateWordCloudFromText(texts: string[], maxWords?: number): WordCloudWord[] {
    if (!texts || texts.length === 0) return [];

    const wordCounts: Record<string, number> = {};
    const stopWords = new Set([
      'el', 'la', 'de', 'en', 'y', 'a', 'que', 'es', 'un', 'una',
      'los', 'las', 'del', 'al', 'por', 'con', 'para', 'se', 'su',
      'como', 'más', 'pero', 'muy', 'sin', 'sobre', 'este', 'esta',
      'the', 'and', 'or', 'is', 'in', 'to', 'of', 'for', 'a', 'an',
    ]);

    texts.forEach(text => {
      const words = text.toLowerCase()
        .replace(/[^\w\sáéíóúüñ]/gi, '')
        .split(/\s+/)
        .filter(word => word.length > 2 && !stopWords.has(word));

      words.forEach(word => {
        wordCounts[word] = (wordCounts[word] || 0) + 1;
      });
    });

    return Object.entries(wordCounts)
      .map(([text, value]) => ({ text, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, maxWords || 100);
  },
};

export default reputationService;
