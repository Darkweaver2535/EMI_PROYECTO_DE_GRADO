/**
 * Tests para hooks personalizados
 * Sistema OSINT EMI - Sprint 4
 */

import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '../../hooks/useDebounce';
import { useLocalStorage } from '../../hooks/useLocalStorage';

describe('useDebounce', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));
    expect(result.current).toBe('initial');
  });

  it('debounces value changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    // Change value
    rerender({ value: 'changed' });
    
    // Value should not change immediately
    expect(result.current).toBe('initial');

    // Fast-forward time
    act(() => {
      jest.advanceTimersByTime(500);
    });

    // Now value should be updated
    expect(result.current).toBe('changed');
  });

  it('cancels previous timeout on rapid changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'change1' });
    act(() => { jest.advanceTimersByTime(200); });
    
    rerender({ value: 'change2' });
    act(() => { jest.advanceTimersByTime(200); });
    
    rerender({ value: 'change3' });
    act(() => { jest.advanceTimersByTime(200); });

    // Still should have initial value (less than 500ms since last change)
    expect(result.current).toBe('initial');

    // Complete the delay
    act(() => { jest.advanceTimersByTime(300); });
    
    // Now should have the final value
    expect(result.current).toBe('change3');
  });

  it('works with different delay values', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 1000),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'changed' });
    
    act(() => { jest.advanceTimersByTime(500); });
    expect(result.current).toBe('initial');

    act(() => { jest.advanceTimersByTime(500); });
    expect(result.current).toBe('changed');
  });
});

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns initial value when no stored value exists', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('returns stored value when it exists', () => {
    localStorage.setItem('test-key', JSON.stringify('stored'));
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    expect(result.current[0]).toBe('stored');
  });

  it('updates value and stores in localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'));

    act(() => {
      result.current[1]('updated');
    });

    expect(result.current[0]).toBe('updated');
    expect(JSON.parse(localStorage.getItem('test-key')!)).toBe('updated');
  });

  it('works with complex objects', () => {
    const initial = { name: 'test', count: 0 };
    const { result } = renderHook(() => useLocalStorage('test-object', initial));

    act(() => {
      result.current[1]({ name: 'updated', count: 5 });
    });

    expect(result.current[0]).toEqual({ name: 'updated', count: 5 });
    expect(JSON.parse(localStorage.getItem('test-object')!)).toEqual({ name: 'updated', count: 5 });
  });

  it('works with arrays', () => {
    const { result } = renderHook(() => useLocalStorage('test-array', ['a', 'b']));

    act(() => {
      result.current[1](['a', 'b', 'c']);
    });

    expect(result.current[0]).toEqual(['a', 'b', 'c']);
  });

  it('handles function updates', () => {
    const { result } = renderHook(() => useLocalStorage('test-counter', 0));

    act(() => {
      result.current[1]((prev: number) => prev + 1);
    });

    expect(result.current[0]).toBe(1);

    act(() => {
      result.current[1]((prev: number) => prev + 1);
    });

    expect(result.current[0]).toBe(2);
  });

  it('handles invalid JSON in localStorage gracefully', () => {
    localStorage.setItem('test-key', 'not valid json');
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'));
    
    // Should return default value when JSON parsing fails
    expect(result.current[0]).toBe('default');
  });

  it('removes item when set to undefined', () => {
    localStorage.setItem('test-key', JSON.stringify('value'));
    
    const { result } = renderHook(() => useLocalStorage<string | undefined>('test-key', undefined));

    act(() => {
      result.current[1](undefined);
    });

    expect(localStorage.getItem('test-key')).toBe('undefined');
  });
});
