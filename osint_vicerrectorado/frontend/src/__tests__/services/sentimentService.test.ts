/**
 * Tests para servicios
 * Sistema OSINT EMI - Sprint 4
 */

import { sentimentService } from '../../services/sentimentService';
import { SentimentDistribution } from '../../types';

describe('sentimentService', () => {
  describe('calculateKPIsFromDistribution', () => {
    it('calculates correct percentages for balanced distribution', () => {
      const distribution: SentimentDistribution = {
        positive: 100,
        negative: 100,
        neutral: 100,
        total: 300,
      };

      const kpis = sentimentService.calculateKPIsFromDistribution(distribution);

      expect(kpis.positivePercent).toBeCloseTo(33.3, 0);
      expect(kpis.negativePercent).toBeCloseTo(33.3, 0);
      expect(kpis.neutralPercent).toBeCloseTo(33.3, 0);
      expect(kpis.satisfactionIndex).toBe(0);
      expect(kpis.totalPosts).toBe(300);
      expect(kpis.trend).toBe('stable');
    });

    it('calculates positive trend correctly', () => {
      const distribution: SentimentDistribution = {
        positive: 200,
        negative: 50,
        neutral: 50,
        total: 300,
      };

      const kpis = sentimentService.calculateKPIsFromDistribution(distribution);

      expect(kpis.positivePercent).toBeGreaterThan(kpis.negativePercent);
      expect(kpis.satisfactionIndex).toBeGreaterThan(0);
      expect(kpis.trend).toBe('up');
    });

    it('calculates negative trend correctly', () => {
      const distribution: SentimentDistribution = {
        positive: 50,
        negative: 200,
        neutral: 50,
        total: 300,
      };

      const kpis = sentimentService.calculateKPIsFromDistribution(distribution);

      expect(kpis.negativePercent).toBeGreaterThan(kpis.positivePercent);
      expect(kpis.satisfactionIndex).toBeLessThan(0);
      expect(kpis.trend).toBe('down');
    });

    it('handles zero total correctly', () => {
      const distribution: SentimentDistribution = {
        positive: 0,
        negative: 0,
        neutral: 0,
        total: 0,
      };

      const kpis = sentimentService.calculateKPIsFromDistribution(distribution);

      expect(kpis.positivePercent).toBe(0);
      expect(kpis.negativePercent).toBe(0);
      expect(kpis.neutralPercent).toBe(0);
      expect(kpis.satisfactionIndex).toBe(0);
      expect(kpis.totalPosts).toBe(0);
      expect(kpis.trend).toBe('stable');
    });

    it('calculates total from distribution if not provided', () => {
      const distribution: SentimentDistribution = {
        positive: 100,
        negative: 50,
        neutral: 50,
      };

      const kpis = sentimentService.calculateKPIsFromDistribution(distribution);

      expect(kpis.totalPosts).toBe(200);
    });
  });
});
