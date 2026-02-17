/**
 * Tipos generales de API
 * Sistema OSINT EMI - Sprint 4
 */

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string>;
}

export interface User {
  id: number;
  username: string;
  email: string;
  nombre: string;
  name: string;
  rol: 'admin' | 'analista' | 'viewer';
  avatar?: string;
  avatarUrl?: string;
  lastLogin?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
}

export type OsintSource = 'facebook' | 'twitter' | 'instagram' | 'news' | 'web' | 'forums' | 'all';
export type OSINTSource = OsintSource; // Alias for compatibility

export interface SourceOption {
  value: OsintSource;
  label: string;
  icon: string;
}

export const OSINT_SOURCES: SourceOption[] = [
  { value: 'all', label: 'Todas las fuentes', icon: '🌐' },
  { value: 'facebook', label: 'Facebook', icon: '📘' },
  { value: 'twitter', label: 'Twitter/X', icon: '🐦' },
  { value: 'news', label: 'Noticias', icon: '📰' },
  { value: 'forums', label: 'Foros', icon: '💬' },
];

export interface Career {
  id: number | string;
  nombre?: string;
  name?: string;
  codigo?: string;
  facultad?: string;
  faculty?: string;
}

export const EMI_CAREERS: Career[] = [
  { id: 1, nombre: 'Ingeniería de Sistemas', codigo: 'SIS', facultad: 'Ingeniería' },
  { id: 2, nombre: 'Ingeniería Civil', codigo: 'CIV', facultad: 'Ingeniería' },
  { id: 3, nombre: 'Ingeniería Industrial', codigo: 'IND', facultad: 'Ingeniería' },
  { id: 4, nombre: 'Ingeniería Electrónica', codigo: 'ELE', facultad: 'Ingeniería' },
  { id: 5, nombre: 'Ingeniería Mecánica', codigo: 'MEC', facultad: 'Ingeniería' },
  { id: 6, nombre: 'Administración de Empresas', codigo: 'ADM', facultad: 'Ciencias Económicas' },
  { id: 7, nombre: 'Ingeniería Comercial', codigo: 'COM', facultad: 'Ciencias Económicas' },
  { id: 8, nombre: 'Auditoría', codigo: 'AUD', facultad: 'Ciencias Económicas' },
];

export type ExportFormat = 'png' | 'excel' | 'pdf';

export interface ExportOptions {
  format: ExportFormat;
  filename?: string;
  title?: string;
  includeFilters?: boolean;
  includeTimestamp?: boolean;
}
