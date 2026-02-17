/**
 * Context de Filtros Globales
 * Sistema OSINT EMI - Sprint 4
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';
import { OSINTSource, Career, AlertSeverity } from '../types';
import { formatDateForAPI, getDefaultDateRange } from '../utils';

export interface FilterState {
  dateRange: {
    startDate: string;
    endDate: string;
  };
  source: OSINTSource | 'all';
  career: string | 'all';
  severity: AlertSeverity | 'all';
  searchQuery: string;
}

interface FilterContextType {
  filters: FilterState;
  setDateRange: (startDate: string, endDate: string) => void;
  setSource: (source: OSINTSource | 'all') => void;
  setCareer: (career: string | 'all') => void;
  setSeverity: (severity: AlertSeverity | 'all') => void;
  setSearchQuery: (query: string) => void;
  resetFilters: () => void;
  getApiParams: () => {
    startDate: string;
    endDate: string;
    source?: OSINTSource;
    career?: string;
    severity?: AlertSeverity;
  };
}

const defaultDateRange = getDefaultDateRange(30);

const defaultFilters: FilterState = {
  dateRange: {
    startDate: formatDateForAPI(defaultDateRange.startDate),
    endDate: formatDateForAPI(defaultDateRange.endDate),
  },
  source: 'all',
  career: 'all',
  severity: 'all',
  searchQuery: '',
};

const FilterContext = createContext<FilterContextType | undefined>(undefined);

interface FilterProviderProps {
  children: ReactNode;
}

export const FilterProvider: React.FC<FilterProviderProps> = ({ children }) => {
  const [filters, setFilters] = useState<FilterState>(defaultFilters);

  const setDateRange = useCallback((startDate: string, endDate: string) => {
    setFilters(prev => ({
      ...prev,
      dateRange: { startDate, endDate },
    }));
  }, []);

  const setSource = useCallback((source: OSINTSource | 'all') => {
    setFilters(prev => ({
      ...prev,
      source,
    }));
  }, []);

  const setCareer = useCallback((career: string | 'all') => {
    setFilters(prev => ({
      ...prev,
      career,
    }));
  }, []);

  const setSeverity = useCallback((severity: AlertSeverity | 'all') => {
    setFilters(prev => ({
      ...prev,
      severity,
    }));
  }, []);

  const setSearchQuery = useCallback((searchQuery: string) => {
    setFilters(prev => ({
      ...prev,
      searchQuery,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(defaultFilters);
  }, []);

  const getApiParams = useCallback(() => {
    return {
      startDate: filters.dateRange.startDate,
      endDate: filters.dateRange.endDate,
      ...(filters.source !== 'all' && { source: filters.source }),
      ...(filters.career !== 'all' && { career: filters.career }),
      ...(filters.severity !== 'all' && { severity: filters.severity }),
    };
  }, [filters]);

  const value = useMemo(
    () => ({
      filters,
      setDateRange,
      setSource,
      setCareer,
      setSeverity,
      setSearchQuery,
      resetFilters,
      getApiParams,
    }),
    [filters, setDateRange, setSource, setCareer, setSeverity, setSearchQuery, resetFilters, getApiParams]
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
};

export const useFilters = (): FilterContextType => {
  const context = useContext(FilterContext);
  if (context === undefined) {
    throw new Error('useFilters must be used within a FilterProvider');
  }
  return context;
};

export default FilterContext;
