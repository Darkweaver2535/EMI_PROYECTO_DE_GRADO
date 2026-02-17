/**
 * Tipos para Benchmarking Académico
 * Sistema OSINT EMI - Sprint 4
 */

export interface CareerRanking {
  id?: number | string;
  nombre?: string;
  careerName: string;
  careerId?: number | string;
  codigo?: string;
  satisfactionScore?: number;
  rank: number;
  totalOpinions?: number;
  trend?: 'up' | 'down' | 'stable';
  change?: number; // cambio vs período anterior
  mentions?: number;
  sentiment?: number;
  engagement?: number;
}

export interface CareerRadarProfile {
  carrera: string;
  dimensions: RadarDimension[];
}

export interface RadarDimension {
  dimension: string;
  value: number;
  maxValue: number;
  label: string;
}

export interface RadarProfileData {
  subject?: string;
  value?: number;
  fullMark?: number;
  careerName: string;
  careerId?: number | string;
  metrics: Record<string, number>;
}

export interface CorrelationCell {
  variable1: string;
  variable2: string;
  correlation: number;
  pValue: number;
  significance: 'high' | 'medium' | 'low' | 'none';
}

export interface CorrelationMatrix {
  variables: string[];
  cells?: CorrelationCell[];
  values: number[][];
}

export interface CareerTrend {
  carrera: string;
  data: {
    period: string;
    score: number;
  }[];
}

export interface BenchmarkingFilters {
  semester?: string;
  metric?: string;
  careerIds?: number[];
}

export interface BenchmarkingSummary {
  topCarreras: CareerRanking[];
  bottomCarreras: CareerRanking[];
  averageScore: number;
  totalCareers: number;
  significantCorrelations: CorrelationCell[];
}

export interface CareerComparison {
  careerId: string;
  careerName: string;
  metrics: Record<string, number>;
  period: string;
}

export interface AcademicIndicator {
  id: string;
  name: string;
  description: string;
  unit: string;
}

export const ACADEMIC_INDICATORS: AcademicIndicator[] = [
  { id: 'teaching', name: 'Calidad Docente', description: 'Evaluación de la enseñanza', unit: 'pts' },
  { id: 'infrastructure', name: 'Infraestructura', description: 'Calidad de instalaciones', unit: 'pts' },
  { id: 'attention', name: 'Atención Estudiantil', description: 'Servicios de apoyo', unit: 'pts' },
  { id: 'resources', name: 'Recursos Académicos', description: 'Materiales y biblioteca', unit: 'pts' },
  { id: 'employability', name: 'Empleabilidad', description: 'Inserción laboral', unit: '%' },
];
