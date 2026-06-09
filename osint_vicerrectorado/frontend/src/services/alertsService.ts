/**
 * Servicio de Alertas y Anomalías
 * Sistema OSINT EMI - Sprint 4
 */

import api from './api';
import { Alert, AlertFilters, AlertStats, AlertSeverity, AlertType } from '../types';

export interface GetAlertsParams extends AlertFilters {
  page?: number;
  limit?: number;
  startDate?: string;
  endDate?: string;
  source?: string;
}

export interface GetAlertStatsParams {
  startDate: string;
  endDate: string;
}

export interface ResolveAlertParams {
  alertId: string;
  resolution: string;
  resolvedBy?: string;
}

export interface CreateAlertParams {
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  source?: string;
  metadata?: Record<string, unknown>;
}

export const alertsService = {
  /**
   * Obtiene lista de alertas con filtros
   */
  async getAlerts(params: GetAlertsParams): Promise<{ alerts: Alert[]; total: number; page: number; pages: number }> {
    const { data } = await api.get('/ai/alerts', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
        severity: params.severity || undefined,
        type: params.type || undefined,
        status: params.status || undefined,
        source: params.source || undefined,
        page: params.page || 1,
        limit: params.limit || 20,
      },
    });
    return data;
  },

  /**
   * Obtiene una alerta específica por ID
   */
  async getAlertById(alertId: string): Promise<Alert> {
    const { data } = await api.get<Alert>(`/ai/alerts/${alertId}`);
    return data;
  },

  /**
   * Resuelve/cierra una alerta
   */
  async resolveAlert(params: ResolveAlertParams): Promise<Alert> {
    const { data } = await api.put<Alert>(`/ai/alerts/${params.alertId}/resolve`, {
      resolution: params.resolution,
      resolved_by: params.resolvedBy,
    });
    return data;
  },

  /**
   * Marca una alerta como vista
   */
  async markAsRead(alertId: string): Promise<Alert> {
    const { data } = await api.put<Alert>(`/ai/alerts/${alertId}/read`);
    return data;
  },

  /**
   * Obtiene estadísticas de alertas
   */
  async getAlertStats(params: GetAlertStatsParams): Promise<AlertStats> {
    const { data } = await api.get<AlertStats>('/ai/alerts/stats', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Obtiene alertas activas (no resueltas)
   */
  async getActiveAlerts(limit?: number): Promise<Alert[]> {
    const { data } = await api.get<Alert[]>('/ai/alerts/active', {
      params: { limit: limit || 10 },
    });
    return data;
  },

  /**
   * Obtiene historial de anomalías detectadas
   */
  async getAnomalies(params: { startDate: string; endDate: string }): Promise<{
    anomalies: Array<{
      date: string;
      metric: string;
      expected: number;
      actual: number;
      deviation: number;
    }>;
  }> {
    const { data } = await api.get('/ai/alerts/anomalies', {
      params: {
        start_date: params.startDate,
        end_date: params.endDate,
      },
    });
    return data;
  },

  /**
   * Crea una nueva alerta manual
   */
  async createAlert(params: CreateAlertParams): Promise<Alert> {
    const { data } = await api.post<Alert>('/ai/alerts', params);
    return data;
  },

  /**
   * Elimina una alerta
   */
  async deleteAlert(alertId: string): Promise<void> {
    await api.delete(`/ai/alerts/${alertId}`);
  },

  /**
   * Obtiene conteo de alertas por severidad
   */
  async getAlertCountBySeverity(): Promise<Record<AlertSeverity, number>> {
    const { data } = await api.get('/ai/alerts/count-by-severity');
    return data;
  },

  /**
   * Calcula estadísticas desde lista de alertas localmente
   */
  calculateStatsFromAlerts(alerts: Alert[]): AlertStats {
    let criticas = 0, altas = 0, medias = 0, bajas = 0;
    let nuevas = 0, enProceso = 0, resueltas = 0;

    alerts.forEach(alert => {
      // Count by severity (acepta nombres en español o inglés)
      switch (alert.severidad ?? alert.severity) {
        case 'critica':
        case 'critical':
          criticas++;
          break;
        case 'alta':
        case 'high':
          altas++;
          break;
        case 'media':
        case 'medium':
          medias++;
          break;
        case 'baja':
        case 'low':
          bajas++;
          break;
      }

      // Count by status
      switch (alert.estado ?? alert.status) {
        case 'nueva':
        case 'new':
        case 'pending':
          nuevas++;
          break;
        case 'en_proceso':
          enProceso++;
          break;
        case 'resuelta':
        case 'resolved':
        case 'descartada':
          resueltas++;
          break;
      }
    });

    return {
      // Nombres en español (UI legada)
      totalAlertas: alerts.length,
      nuevas, enProceso, resueltas,
      criticas, altas, medias, bajas,
      // Nombres en inglés (requeridos por AlertStats)
      total: alerts.length,
      critical: criticas,
      high: altas,
      medium: medias,
      low: bajas,
      pending: nuevas,
      resolved: resueltas,
      lastHour: 0,
    };
  },

  /**
   * Determina el color según la severidad
   */
  getSeverityColor(severity: AlertSeverity): string {
    const colors: Partial<Record<AlertSeverity, string>> = {
      critica: '#d32f2f', critical: '#d32f2f',
      alta: '#f57c00', high: '#f57c00',
      media: '#fbc02d', medium: '#fbc02d',
      baja: '#388e3c', low: '#388e3c',
    };
    return colors[severity] || '#757575';
  },
};

export default alertsService;
