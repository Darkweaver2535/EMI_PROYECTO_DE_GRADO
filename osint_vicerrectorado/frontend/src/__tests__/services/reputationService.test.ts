/**
 * Tests para reputationService
 * Sistema OSINT EMI - Sprint 4
 */

import { reputationService } from '../../services/reputationService';

describe('reputationService', () => {
  describe('generateWordCloudFromText', () => {
    it('generates word cloud from text array', () => {
      const texts = ['universidad excelente universidad buena calidad universidad'];

      const words = reputationService.generateWordCloudFromText(texts);

      expect(words.length).toBeGreaterThan(0);
      
      const universidadWord = words.find(w => w.text.toLowerCase() === 'universidad');
      expect(universidadWord).toBeDefined();
      expect(universidadWord!.value).toBe(3);
    });

    it('filters out short words', () => {
      const texts = ['el la un una de en a EMI bueno'];

      const words = reputationService.generateWordCloudFromText(texts);

      // Short words (el, la, un, una, de, en, a) should be filtered
      const shortWords = words.filter(w => w.text.length <= 2);
      expect(shortWords.length).toBe(0);
    });

    it('handles empty array', () => {
      const words = reputationService.generateWordCloudFromText([]);
      expect(words).toHaveLength(0);
    });

    it('converts to lowercase', () => {
      const texts = ['UNIVERSIDAD Universidad UniverSidad'];

      const words = reputationService.generateWordCloudFromText(texts);

      const universidadWord = words.find(w => w.text === 'universidad');
      expect(universidadWord).toBeDefined();
      expect(universidadWord!.value).toBe(3);
    });

    it('respects maxWords limit', () => {
      const texts = ['palabra1 palabra2 palabra3 palabra4 palabra5 palabra6 palabra7 palabra8 palabra9 palabra10 palabra11'];

      const words = reputationService.generateWordCloudFromText(texts, 5);

      expect(words.length).toBeLessThanOrEqual(5);
    });

    it('sorts by frequency descending', () => {
      const texts = ['raro raro raro comun comun unico'];

      const words = reputationService.generateWordCloudFromText(texts);

      expect(words[0].text).toBe('raro');
      expect(words[0].value).toBe(3);
      expect(words[1].text).toBe('comun');
      expect(words[1].value).toBe(2);
    });
  });
});
