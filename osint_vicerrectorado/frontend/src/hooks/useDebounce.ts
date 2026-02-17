/**
 * Hook useDebounce
 * Sistema OSINT EMI - Sprint 4
 */

import { useState, useEffect } from 'react';

/**
 * Hook para hacer debounce de un valor
 * @param value - Valor a debounce
 * @param delay - Tiempo de espera en ms
 * @returns Valor con debounce aplicado
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default useDebounce;
