/**
 * Tests para utilidades de fecha
 * Sistema OSINT EMI - Sprint 4
 */

import {
  formatDateForAPI,
  formatDateDisplay,
  formatTimeAgo,
  getDefaultDateRange,
  isDateInRange,
} from '../../utils/dateHelpers';

describe('dateHelpers', () => {
  describe('formatDateForAPI', () => {
    it('formats Date object to YYYY-MM-DD', () => {
      const date = new Date('2024-03-15T12:00:00');
      expect(formatDateForAPI(date)).toBe('2024-03-15');
    });

    it('returns string as-is if already formatted', () => {
      expect(formatDateForAPI('2024-03-15')).toBe('2024-03-15');
    });
  });

  describe('formatDateDisplay', () => {
    it('formats date for display (long format)', () => {
      const result = formatDateDisplay('2024-03-15');
      expect(result).toContain('2024');
      expect(result).toContain('15');
    });

    it('formats date for display (short format)', () => {
      const result = formatDateDisplay('2024-03-15', 'short');
      expect(result).toBeTruthy();
      expect(result.length).toBeLessThan(20);
    });

    it('handles invalid date gracefully', () => {
      expect(formatDateDisplay('invalid-date')).toBe('Fecha inválida');
    });
  });

  describe('formatTimeAgo', () => {
    it('returns "Justo ahora" for recent dates', () => {
      const now = new Date();
      expect(formatTimeAgo(now.toISOString())).toBe('Justo ahora');
    });

    it('returns minutes ago for dates within an hour', () => {
      const date = new Date(Date.now() - 30 * 60 * 1000); // 30 minutes ago
      expect(formatTimeAgo(date.toISOString())).toBe('Hace 30 minutos');
    });

    it('returns hours ago for dates within a day', () => {
      const date = new Date(Date.now() - 3 * 60 * 60 * 1000); // 3 hours ago
      expect(formatTimeAgo(date.toISOString())).toBe('Hace 3 horas');
    });

    it('returns days ago for dates within a week', () => {
      const date = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000); // 2 days ago
      expect(formatTimeAgo(date.toISOString())).toBe('Hace 2 días');
    });
  });

  describe('getDefaultDateRange', () => {
    it('returns correct date range for 30 days', () => {
      const { startDate, endDate } = getDefaultDateRange(30);
      const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      expect(diffDays).toBe(30);
    });

    it('returns correct date range for 7 days', () => {
      const { startDate, endDate } = getDefaultDateRange(7);
      const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      expect(diffDays).toBe(7);
    });

    it('endDate is today', () => {
      const { endDate } = getDefaultDateRange(30);
      const today = new Date();
      expect(endDate.toDateString()).toBe(today.toDateString());
    });
  });

  describe('isDateInRange', () => {
    it('returns true for date within range', () => {
      const date = new Date('2024-03-15');
      const start = new Date('2024-03-01');
      const end = new Date('2024-03-31');
      expect(isDateInRange(date, start, end)).toBe(true);
    });

    it('returns false for date outside range', () => {
      const date = new Date('2024-04-15');
      const start = new Date('2024-03-01');
      const end = new Date('2024-03-31');
      expect(isDateInRange(date, start, end)).toBe(false);
    });

    it('returns true for date on start boundary', () => {
      const date = new Date('2024-03-01');
      const start = new Date('2024-03-01');
      const end = new Date('2024-03-31');
      expect(isDateInRange(date, start, end)).toBe(true);
    });

    it('returns true for date on end boundary', () => {
      const date = new Date('2024-03-31');
      const start = new Date('2024-03-01');
      const end = new Date('2024-03-31');
      expect(isDateInRange(date, start, end)).toBe(true);
    });
  });
});
