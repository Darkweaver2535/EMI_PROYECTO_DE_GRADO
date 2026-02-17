/**
 * Tests para contexts
 * Sistema OSINT EMI - Sprint 4
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { FilterProvider, useFilters } from '../../contexts/FilterContext';
import { ThemeProvider, useTheme as useThemeContext } from '../../contexts/ThemeContext';
import { AlertSeverity } from '../../types';

// Test component para FilterContext
const FilterTestComponent: React.FC = () => {
  const filters = useFilters();
  
  return (
    <div>
      <span data-testid="source">{filters.filters.source || 'all'}</span>
      <span data-testid="career">{filters.filters.career || 'all'}</span>
      <span data-testid="severity">{filters.filters.severity || 'all'}</span>
      <button onClick={() => filters.setFilter('source', 'twitter')}>Set Twitter</button>
      <button onClick={() => filters.setFilter('career', 'systems')}>Set Systems</button>
      <button onClick={() => filters.setFilter('severity', 'critica' as AlertSeverity)}>Set Critical</button>
      <button onClick={() => filters.resetFilters()}>Clear</button>
    </div>
  );
};

describe('FilterContext', () => {
  it('provides default values', () => {
    render(
      <FilterProvider>
        <FilterTestComponent />
      </FilterProvider>
    );

    expect(screen.getByTestId('source')).toHaveTextContent('all');
    expect(screen.getByTestId('career')).toHaveTextContent('all');
    expect(screen.getByTestId('severity')).toHaveTextContent('all');
  });

  it('updates source filter', () => {
    render(
      <FilterProvider>
        <FilterTestComponent />
      </FilterProvider>
    );

    fireEvent.click(screen.getByText('Set Twitter'));
    expect(screen.getByTestId('source')).toHaveTextContent('twitter');
  });

  it('updates career filter', () => {
    render(
      <FilterProvider>
        <FilterTestComponent />
      </FilterProvider>
    );

    fireEvent.click(screen.getByText('Set Systems'));
    expect(screen.getByTestId('career')).toHaveTextContent('systems');
  });

  it('updates severity filter', () => {
    render(
      <FilterProvider>
        <FilterTestComponent />
      </FilterProvider>
    );

    fireEvent.click(screen.getByText('Set Critical'));
    expect(screen.getByTestId('severity')).toHaveTextContent('critica');
  });

  it('clears all filters', () => {
    render(
      <FilterProvider>
        <FilterTestComponent />
      </FilterProvider>
    );

    // Set some filters first
    fireEvent.click(screen.getByText('Set Twitter'));
    fireEvent.click(screen.getByText('Set Systems'));
    
    // Clear all
    fireEvent.click(screen.getByText('Clear'));

    expect(screen.getByTestId('source')).toHaveTextContent('all');
    expect(screen.getByTestId('career')).toHaveTextContent('all');
  });
});

// Test component para ThemeContext
const ThemeTestComponent: React.FC = () => {
  const { mode, toggleTheme } = useThemeContext();
  
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <button onClick={toggleTheme}>Toggle Theme</button>
    </div>
  );
};

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    // Reset matchMedia mock
    window.matchMedia = jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }));
  });

  it('provides default light mode', () => {
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('mode')).toHaveTextContent('light');
  });

  it('toggles theme mode', () => {
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByText('Toggle Theme'));
    expect(screen.getByTestId('mode')).toHaveTextContent('dark');

    fireEvent.click(screen.getByText('Toggle Theme'));
    expect(screen.getByTestId('mode')).toHaveTextContent('light');
  });

  it('persists theme to localStorage', () => {
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );

    fireEvent.click(screen.getByText('Toggle Theme'));
    
    expect(localStorage.getItem('theme-mode')).toBe('dark');
  });

  it('reads theme from localStorage', () => {
    localStorage.setItem('theme-mode', 'dark');

    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('mode')).toHaveTextContent('dark');
  });

  it('respects system preference when no stored value', () => {
    window.matchMedia = jest.fn().mockImplementation(query => ({
      matches: query === '(prefers-color-scheme: dark)',
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }));

    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );

    expect(screen.getByTestId('mode')).toHaveTextContent('dark');
  });
});
