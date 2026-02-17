/**
 * Tipos para Análisis de Sentimiento
 * Sistema OSINT EMI - Sprint 4
 */

export interface SentimentData {
  date: string;
  positive: number;
  negative: number;
  neutral: number;
  [key: string]: unknown; // Allow indexing
}

export interface SentimentDistribution {
  positive: number;
  negative: number;
  neutral: number;
  total: number;
}

export type SentimentType = 'Positivo' | 'Negativo' | 'Neutral';

export interface TopPost {
  id: number;
  text: string;
  sentiment: SentimentType;
  sentimentScore?: number;
  confidence: number;
  source: string;
  date: string;
  engagement?: number;
  url?: string;
  [key: string]: unknown; // Allow indexing
}

export interface SentimentKPIs {
  positivePercent: number;
  negativePercent: number;
  neutralPercent: number;
  satisfactionIndex: number;
  totalPosts: number;
  trend: 'up' | 'down' | 'stable';
  periodComparison?: {
    previousPositive: number;
    previousNegative: number;
    change: number;
  };
}

export interface SentimentFilters {
  startDate: string;
  endDate: string;
  source?: string;
  career?: string;
}

export interface SentimentTrendResponse {
  data: SentimentData[];
  summary: SentimentKPIs;
}
