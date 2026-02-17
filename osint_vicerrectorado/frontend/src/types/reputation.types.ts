/**
 * Tipos para Reputación Institucional
 * Sistema OSINT EMI - Sprint 4
 */

export interface WordCloudWord {
  text: string;
  value: number;
  [key: string]: unknown; // Allow indexing
}

export interface TopicData {
  topic: string;
  mentions: number;
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
  trend: 'up' | 'down' | 'stable';
}

export interface TopicCluster {
  id: number;
  name: string;
  keywords: string[];
  size: number;
  count?: number;
  sentiment: number;
  trend: 'up' | 'down' | 'stable';
}

export interface HeatmapCell {
  day: number; // 0-6 (Domingo-Sábado)
  hour: number; // 0-23
  value: number;
}

// HeatmapData can be either a cell or a container with cells
export interface HeatmapData {
  cells?: HeatmapCell[];
  maxValue?: number;
  minValue?: number;
  // Direct cell properties (when used as individual data points)
  day?: number;
  hour?: number;
  value?: number;
}

export interface CompetitorData {
  name: string;
  satisfactionScore: number;
  mentionsCount: number;
  mentions?: number;
  positiveRatio: number;
  sentiment?: number;
  color: string;
}

export interface TimelineEvent {
  id: number;
  date: string;
  title: string;
  description: string;
  mentions: number;
  sentiment: 'positive' | 'negative' | 'neutral' | 'mixed';
  importance: 'high' | 'medium' | 'low';
}

export interface ReputationFilters {
  period: number; // días
  career?: string;
}

export interface ReputationSummary {
  overallScore: number;
  totalMentions: number;
  sentimentDistribution: {
    positive: number;
    negative: number;
    neutral: number;
  };
  topTopics: TopicData[];
  competitorRanking: number;
}
