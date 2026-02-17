/**
 * Servicio de Alertas y Anomalías
 * Sistema OSINT EMI - Sprint 4
 */

import api from './api';
import { Alert, AlertFilters, AlertStats, AlertSeverity, AlertType } from '../types';

export interface GetAlertsParams extends AlertFilters {
  page?: number;
  limit?: number;
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
    const stats: AlertStats = {
      totalAlertas: alerts.length,
      nuevas: 0,
      enProceso: 0,
      resueltas: 0,
      criticas: 0,
      altas: 0,
      medias: 0,
      bajas: 0,
    };

    alerts.forEach(alert => {
      // Count by severity
      switch (alert.severidad) {
        case 'critica':
          stats.criticas++;
          break;
        case 'alta':
          stats.altas++;
          break;
        case 'media':
          stats.medias++;
          break;
        case 'baja':
          stats.bajas++;
          break;
      }

      // Count by status
      switch (alert.estado) {
        case 'nueva':
          stats.nuevas++;
          break;
        case 'en_proceso':
          stats.enProceso++;
          break;
        case 'resuelta':
        case 'descartada':
          stats.resueltas++;
          break;
      }
    });

    return stats;
  },

  /**
   * Determina el color según la severidad
   */
  getSeverityColor(severity: AlertSeverity): string {
    const colors: Record<AlertSeverity, string> = {
      critica: '#d32f2f',
      alta: '#f57c00',
      media: '#fbc02d',
      baja: '#388e3c',
    };
    return colors[severity] || '#757575';
  },
};

export default alertsService;
