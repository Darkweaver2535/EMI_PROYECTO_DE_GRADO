/**
 * Tests para alertsService
 * Sistema OSINT EMI - Sprint 4
 */

import { alertsService } from '../../services/alertsService';
import { Alert, AlertSeverity, AlertStatus } from '../../types';

describe('alertsService', () => {
  describe('calculateStatsFromAlerts', () => {
    const createAlert = (severidad: AlertSeverity, estado: AlertStatus): Alert => ({
      id: Math.floor(Math.random() * 1000),
      tipo: 'pico_negatividad',
      severidad,
      titulo: 'Test Alert',
      descripcion: 'Test description',
      fechaDeteccion: new Date().toISOString(),
      estado,
      valorObservado: 100,
      valorEsperado: 50,
      desviacion: 2,
      metricasAfectadas: ['sentimiento'],
    });

    it('calculates stats for mixed alerts', () => {
      const alerts: Alert[] = [
        createAlert('critica', 'nueva'),
        createAlert('critica', 'resuelta'),
        createAlert('alta', 'nueva'),
        createAlert('media', 'en_proceso'),
        createAlert('baja', 'nueva'),
        createAlert('baja', 'resuelta'),
      ];

      const stats = alertsService.calculateStatsFromAlerts(alerts);

      expect(stats.totalAlertas).toBe(6);
      expect(stats.criticas).toBe(2);
      expect(stats.altas).toBe(1);
      expect(stats.medias).toBe(1);
      expect(stats.bajas).toBe(2);
      expect(stats.resueltas).toBe(2);
      expect(stats.nuevas).toBe(3);
    });

    it('calculates stats for empty array', () => {
      const stats = alertsService.calculateStatsFromAlerts([]);

      expect(stats.totalAlertas).toBe(0);
      expect(stats.criticas).toBe(0);
      expect(stats.altas).toBe(0);
      expect(stats.medias).toBe(0);
      expect(stats.bajas).toBe(0);
      expect(stats.resueltas).toBe(0);
      expect(stats.nuevas).toBe(0);
    });

    it('counts all critical alerts correctly', () => {
      const alerts: Alert[] = [
        createAlert('critica', 'nueva'),
        createAlert('critica', 'nueva'),
        createAlert('critica', 'en_proceso'),
      ];

      const stats = alertsService.calculateStatsFromAlerts(alerts);

      expect(stats.totalAlertas).toBe(3);
      expect(stats.criticas).toBe(3);
      expect(stats.nuevas).toBe(2);
      expect(stats.enProceso).toBe(1);
    });

    it('handles all resolved alerts', () => {
      const alerts: Alert[] = [
        createAlert('alta', 'resuelta'),
        createAlert('media', 'resuelta'),
        createAlert('baja', 'resuelta'),
      ];

      const stats = alertsService.calculateStatsFromAlerts(alerts);

      expect(stats.totalAlertas).toBe(3);
      expect(stats.resueltas).toBe(3);
      expect(stats.nuevas).toBe(0);
    });
  });
});
