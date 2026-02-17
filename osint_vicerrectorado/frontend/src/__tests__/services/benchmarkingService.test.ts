/**
 * Tests para benchmarkingService
 * Sistema OSINT EMI - Sprint 4
 */

import { benchmarkingService } from '../../services/benchmarkingService';
import { CareerRanking } from '../../types';

describe('benchmarkingService', () => {
  describe('normalizeScores', () => {
    it('normalizes scores to 0-100 range', () => {
      const rankings: CareerRanking[] = [
        { id: 1, nombre: 'Career A', codigo: 'CA', satisfactionScore: 10, rank: 1, totalOpinions: 100, trend: 'stable', change: 0 },
        { id: 2, nombre: 'Career B', codigo: 'CB', satisfactionScore: 50, rank: 2, totalOpinions: 100, trend: 'stable', change: 0 },
        { id: 3, nombre: 'Career C', codigo: 'CC', satisfactionScore: 100, rank: 3, totalOpinions: 100, trend: 'stable', change: 0 },
      ];

      const normalized = benchmarkingService.normalizeScores(rankings);

      expect(normalized[0].satisfactionScore).toBe(0); // min becomes 0
      expect(normalized[2].satisfactionScore).toBe(100); // max becomes 100
      expect(normalized[1].satisfactionScore).toBeCloseTo(44.4, 0); // middle value
    });

    it('handles single item', () => {
      const rankings: CareerRanking[] = [
        { id: 1, nombre: 'Career A', codigo: 'CA', satisfactionScore: 75, rank: 1, totalOpinions: 100, trend: 'stable', change: 0 },
      ];

      const normalized = benchmarkingService.normalizeScores(rankings);

      expect(normalized[0].satisfactionScore).toBe(100); // single value becomes 100
    });

    it('handles empty array', () => {
      const normalized = benchmarkingService.normalizeScores([]);
      expect(normalized).toHaveLength(0);
    });

    it('handles all same scores', () => {
      const rankings: CareerRanking[] = [
        { id: 1, nombre: 'Career A', codigo: 'CA', satisfactionScore: 50, rank: 1, totalOpinions: 100, trend: 'stable', change: 0 },
        { id: 2, nombre: 'Career B', codigo: 'CB', satisfactionScore: 50, rank: 2, totalOpinions: 100, trend: 'stable', change: 0 },
        { id: 3, nombre: 'Career C', codigo: 'CC', satisfactionScore: 50, rank: 3, totalOpinions: 100, trend: 'stable', change: 0 },
      ];

      const normalized = benchmarkingService.normalizeScores(rankings);

      // When all scores are equal, they should all be 100 (max)
      normalized.forEach(item => {
        expect(item.satisfactionScore).toBe(100);
      });
    });
  });

  describe('calculateOverallScore', () => {
    it('calculates weighted average', () => {
      const metrics = {
        sentiment: 80,
        reputation: 60,
        engagement: 40,
        growth: 100,
      };

      const weights = {
        sentiment: 0.25,
        reputation: 0.25,
        engagement: 0.25,
        growth: 0.25,
      };

      const score = benchmarkingService.calculateOverallScore(metrics, weights);

      expect(score).toBe(70); // (80 + 60 + 40 + 100) / 4
    });

    it('handles different weights', () => {
      const metrics = {
        sentiment: 100,
        reputation: 0,
      };

      const weights = {
        sentiment: 0.8,
        reputation: 0.2,
      };

      const score = benchmarkingService.calculateOverallScore(metrics, weights);

      expect(score).toBe(80); // 100 * 0.8 + 0 * 0.2
    });

    it('handles missing metrics', () => {
      const metrics = {
        sentiment: 80,
      };

      const weights = {
        sentiment: 0.5,
        reputation: 0.5,
      };

      const score = benchmarkingService.calculateOverallScore(metrics, weights);

      expect(score).toBe(40); // Only sentiment contributes
    });

    it('handles empty metrics', () => {
      const score = benchmarkingService.calculateOverallScore({}, {});
      expect(score).toBe(0);
    });
  });
});
