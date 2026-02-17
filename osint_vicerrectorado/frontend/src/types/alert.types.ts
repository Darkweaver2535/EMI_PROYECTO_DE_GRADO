/**
 * Tipos para Alertas y Anomalías
 * Sistema OSINT EMI - Sprint 4
 */

export type AlertSeverity = 'critica' | 'alta' | 'media' | 'baja' | 'critical' | 'high' | 'medium' | 'low';
export type AlertStatus = 'nueva' | 'en_proceso' | 'resuelta' | 'descartada' | 'pending' | 'resolved' | 'new';
export type AlertType = 
  | 'pico_negatividad' 
  | 'pico_volumen' 
  | 'caida_engagement' 
  | 'anomalia_temporal' 
  | 'patron_inusual'
  | string;

export interface Alert {
  id: number;
  tipo?: AlertType;
  type?: AlertType;
  severidad?: AlertSeverity;
  severity?: AlertSeverity;
  titulo?: string;
  title?: string;
  descripcion?: string;
  message?: string;
  fechaDeteccion?: string;
  createdAt?: string;
  fechaResolucion?: string;
  estado?: AlertStatus;
  status?: AlertStatus;
  valorObservado?: number;
  valorEsperado?: number;
  desviacion?: number;
  metricasAfectadas?: string[];
  postsRelacionados?: RelatedPost[];
  asignadoA?: string;
  comentarios?: AlertComment[];
  source?: string;
  resolution?: {
    date?: string;
    comment?: string;
  };
  [key: string]: unknown; // Allow indexing
}

export interface RelatedPost {
  id: number;
  text: string;
  sentiment: string;
  date: string;
  source: string;
}

export interface AlertComment {
  id: number;
  autor: string;
  texto: string;
  fecha: string;
}

export interface AlertFilters {
  severity?: AlertSeverity;
  status?: AlertStatus;
  type?: AlertType;
  days?: number;
}

export interface AlertStats {
  totalAlertas?: number;
  total: number;
  nuevas?: number;
  enProceso?: number;
  resueltas?: number;
  criticas?: number;
  critical: number;
  altas?: number;
  high: number;
  medias?: number;
  medium: number;
  bajas?: number;
  low: number;
  pending: number;
  resolved: number;
  lastHour: number;
  last24Hours?: number;
}

export interface AlertRiskTrend {
  date: string;
  riskScore: number;
  alertCount: number;
  criticalCount: number;
}

export interface ResolveAlertPayload {
  estado: AlertStatus;
  comentario?: string;
  asignadoA?: string;
}
