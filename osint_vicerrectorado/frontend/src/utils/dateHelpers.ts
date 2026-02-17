/**
 * Utilidades para formateo de fechas
 * Sistema OSINT EMI - Sprint 4
 */

import { format, parseISO, subDays, startOfDay, endOfDay, isValid } from 'date-fns';
import { es } from 'date-fns/locale';

export const formatDate = (date: string | Date, formatStr = 'dd/MM/yyyy'): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Fecha inválida';
    return format(dateObj, formatStr, { locale: es });
  } catch {
    return 'Fecha inválida';
  }
};

export const formatDateTime = (date: string | Date): string => {
  return formatDate(date, "dd/MM/yyyy HH:mm");
};

export const formatDateShort = (date: string | Date): string => {
  return formatDate(date, 'dd MMM');
};

export const formatDateLong = (date: string | Date): string => {
  return formatDate(date, "EEEE, dd 'de' MMMM 'de' yyyy");
};

export const formatRelativeDate = (date: string | Date): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Fecha inválida';
    
    const now = new Date();
    const diffMs = now.getTime() - dateObj.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Hace un momento';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours} h`;
    if (diffDays < 7) return `Hace ${diffDays} días`;
    return formatDate(dateObj);
  } catch {
    return 'Fecha inválida';
  }
};

export const getDateRangePresets = () => [
  {
    label: 'Últimos 7 días',
    startDate: format(subDays(new Date(), 7), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
  },
  {
    label: 'Últimos 30 días',
    startDate: format(subDays(new Date(), 30), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
  },
  {
    label: 'Últimos 90 días',
    startDate: format(subDays(new Date(), 90), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
  },
  {
    label: 'Este año',
    startDate: format(new Date(new Date().getFullYear(), 0, 1), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
  },
];

export const toISODateString = (date: Date | string): string => {
  if (typeof date === 'string') return date;
  return format(startOfDay(date), 'yyyy-MM-dd');
};

export const toISODateTimeString = (date: Date): string => {
  return date.toISOString();
};

export const getStartOfDay = (date: Date | string): Date => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  return startOfDay(dateObj);
};

export const getEndOfDay = (date: Date | string): Date => {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  return endOfDay(dateObj);
};

export const DAY_NAMES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
export const DAY_NAMES_FULL = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

export const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => 
  `${i.toString().padStart(2, '0')}:00`
);

export const getCurrentSemester = (): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const semester = month < 6 ? 'I' : 'II';
  return `${year}-${semester}`;
};

export const getSemesters = (years = 3): string[] => {
  const semesters: string[] = [];
  const currentYear = new Date().getFullYear();
  
  for (let y = currentYear; y >= currentYear - years; y--) {
    semesters.push(`${y}-II`);
    semesters.push(`${y}-I`);
  }
  
  return semesters;
};

// Alias functions for compatibility
export const formatDateForAPI = toISODateString;
export const formatDateDisplay = formatDate;
export const formatTimeAgo = formatRelativeDate;

export const getDefaultDateRange = (days = 30): { startDate: string; endDate: string } => {
  return {
    startDate: format(subDays(new Date(), days), 'yyyy-MM-dd'),
    endDate: format(new Date(), 'yyyy-MM-dd'),
  };
};

export const isDateInRange = (date: string | Date, startDate: string, endDate: string): boolean => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    const start = parseISO(startDate);
    const end = parseISO(endDate);
    return dateObj >= start && dateObj <= end;
  } catch {
    return false;
  }
};
