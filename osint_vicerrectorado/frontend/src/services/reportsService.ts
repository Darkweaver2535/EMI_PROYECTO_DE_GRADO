/**
 * Servicio de API para el Módulo de Reportes
 * Sistema de Analítica OSINT - EMI Bolivia
 * Sprint 5: Reportes y Estadísticas
 */

import axios, { AxiosResponse } from 'axios';
import {
  GenerateReportRequest,
  GenerateReportResponse,
  TaskStatusResponse,
  ReportsHistoryResponse,
  SchedulesListResponse,
  ScheduleResponse,
  CreateScheduleRequest,
  UpdateScheduleRequest,
  ExecutionHistoryResponse,
  SendEmailRequest,
  SendEmailResponse,
  StatsResponse,
  PDFReportType,
  ExcelReportType,
  ReportParams
} from '../types/reports.types';

// Base URL de la API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const REPORTS_API = `${API_BASE_URL}/api/reports`;

// Instancia de Axios configurada
const apiClient = axios.create({
  baseURL: REPORTS_API,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 60000 // 60 segundos para generación de reportes
});

// Interceptor para manejar errores
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============================================================================
// GENERACIÓN DE REPORTES
// ============================================================================

/**
 * Genera un reporte PDF de forma asíncrona
 */
export const generatePDFReport = async (
  reportType: PDFReportType,
  params: ReportParams,
  async: boolean = true
): Promise<GenerateReportResponse> => {
  const response: AxiosResponse<GenerateReportResponse> = await apiClient.post('/generate/pdf', {
    report_type: reportType,
    params,
    async
  });
  return response.data;
};

/**
 * Genera un reporte Excel de forma asíncrona
 */
export const generateExcelReport = async (
  reportType: ExcelReportType,
  params: ReportParams,
  async: boolean = true
): Promise<GenerateReportResponse> => {
  const response: AxiosResponse<GenerateReportResponse> = await apiClient.post('/generate/excel', {
    report_type: reportType,
    params,
    async
  });
  return response.data;
};

/**
 * Genera cualquier tipo de reporte
 */
export const generateReport = async (
  request: GenerateReportRequest
): Promise<GenerateReportResponse> => {
  const isPDF = ['executive', 'alerts', 'statistical', 'career'].includes(request.report_type);
  const endpoint = isPDF ? '/generate/pdf' : '/generate/excel';
  
  const response: AxiosResponse<GenerateReportResponse> = await apiClient.post(endpoint, request);
  return response.data;
};

// ============================================================================
// ESTADO DE TAREAS
// ============================================================================

/**
 * Consulta el estado de una tarea de generación
 */
export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
  const response: AxiosResponse<TaskStatusResponse> = await apiClient.get(`/status/${taskId}`);
  return response.data;
};

/**
 * Polling del estado de una tarea hasta que complete
 */
export const pollTaskStatus = async (
  taskId: string,
  onProgress?: (status: TaskStatusResponse) => void,
  intervalMs: number = 1000,
  maxAttempts: number = 300
): Promise<TaskStatusResponse> => {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    
    const checkStatus = async () => {
      try {
        const status = await getTaskStatus(taskId);
        
        if (onProgress) {
          onProgress(status);
        }
        
        if (status.status === 'SUCCESS' || status.status === 'FAILURE') {
          resolve(status);
          return;
        }
        
        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error('Timeout: La tarea tardó demasiado'));
          return;
        }
        
        setTimeout(checkStatus, intervalMs);
      } catch (error) {
        reject(error);
      }
    };
    
    checkStatus();
  });
};

// ============================================================================
// DESCARGA Y HISTORIAL
// ============================================================================

/**
 * Descarga un reporte
 */
export const downloadReport = async (filename: string): Promise<Blob> => {
  const response = await apiClient.get(`/download/${filename}`, {
    responseType: 'blob'
  });
  return response.data;
};

/**
 * Descarga y guarda un reporte
 */
export const downloadAndSaveReport = async (filename: string): Promise<void> => {
  const blob = await downloadReport(filename);
  
  // Crear link de descarga
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

/**
 * Obtiene el historial de reportes generados
 */
export const getReportsHistory = async (
  type?: 'pdf' | 'excel' | 'all',
  days?: number,
  limit?: number
): Promise<ReportsHistoryResponse> => {
  const params = new URLSearchParams();
  if (type) params.append('type', type);
  if (days) params.append('days', days.toString());
  if (limit) params.append('limit', limit.toString());
  
  const response: AxiosResponse<ReportsHistoryResponse> = await apiClient.get(
    `/history?${params.toString()}`
  );
  return response.data;
};

/**
 * Elimina un reporte
 */
export const deleteReport = async (filename: string): Promise<{ success: boolean; message?: string }> => {
  const response = await apiClient.delete(`/delete/${filename}`);
  return response.data;
};

// ============================================================================
// PROGRAMACIONES (SCHEDULES)
// ============================================================================

/**
 * Obtiene todas las programaciones
 */
export const getSchedules = async (): Promise<SchedulesListResponse> => {
  const response: AxiosResponse<SchedulesListResponse> = await apiClient.get('/schedules');
  return response.data;
};

/**
 * Obtiene una programación específica
 */
export const getSchedule = async (scheduleId: number): Promise<ScheduleResponse> => {
  const response: AxiosResponse<ScheduleResponse> = await apiClient.get(`/schedules/${scheduleId}`);
  return response.data;
};

/**
 * Crea una nueva programación
 */
export const createSchedule = async (
  schedule: CreateScheduleRequest
): Promise<ScheduleResponse> => {
  const response: AxiosResponse<ScheduleResponse> = await apiClient.post('/schedules', schedule);
  return response.data;
};

/**
 * Actualiza una programación existente
 */
export const updateSchedule = async (
  scheduleId: number,
  updates: UpdateScheduleRequest
): Promise<ScheduleResponse> => {
  const response: AxiosResponse<ScheduleResponse> = await apiClient.put(
    `/schedules/${scheduleId}`,
    updates
  );
  return response.data;
};

/**
 * Elimina una programación
 */
export const deleteSchedule = async (scheduleId: number): Promise<ScheduleResponse> => {
  const response: AxiosResponse<ScheduleResponse> = await apiClient.delete(
    `/schedules/${scheduleId}`
  );
  return response.data;
};

/**
 * Activa o desactiva una programación
 */
export const toggleSchedule = async (
  scheduleId: number
): Promise<{ success: boolean; enabled?: boolean; message?: string }> => {
  const response = await apiClient.post(`/schedules/${scheduleId}/toggle`);
  return response.data;
};

/**
 * Ejecuta una programación inmediatamente
 */
export const runScheduleNow = async (scheduleId: number): Promise<GenerateReportResponse> => {
  const response: AxiosResponse<GenerateReportResponse> = await apiClient.post(
    `/schedules/${scheduleId}/run`
  );
  return response.data;
};

/**
 * Obtiene el historial de ejecuciones de una programación
 */
export const getScheduleHistory = async (
  scheduleId: number,
  limit?: number
): Promise<ExecutionHistoryResponse> => {
  const params = limit ? `?limit=${limit}` : '';
  const response: AxiosResponse<ExecutionHistoryResponse> = await apiClient.get(
    `/schedules/${scheduleId}/history${params}`
  );
  return response.data;
};

// ============================================================================
// EMAIL
// ============================================================================

/**
 * Envía un reporte por email
 */
export const sendReportEmail = async (request: SendEmailRequest): Promise<SendEmailResponse> => {
  const response: AxiosResponse<SendEmailResponse> = await apiClient.post('/send', request);
  return response.data;
};

// ============================================================================
// ESTADÍSTICAS
// ============================================================================

/**
 * Obtiene estadísticas del módulo de reportes
 */
export const getReportsStats = async (): Promise<StatsResponse> => {
  const response: AxiosResponse<StatsResponse> = await apiClient.get('/stats');
  return response.data;
};

// ============================================================================
// UTILIDADES
// ============================================================================

/**
 * Formatea el tamaño de archivo
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Obtiene el ícono según el tipo de reporte
 */
export const getReportIcon = (reportType: string): string => {
  const icons: Record<string, string> = {
    executive: '📊',
    alerts: '🚨',
    statistical: '📚',
    career: '🎓',
    sentiment_dataset: '📈',
    pivot_table: '🔄',
    anomalies: '⚠️',
    combined: '📋',
    other: '📄'
  };
  return icons[reportType] || icons.other;
};

/**
 * Obtiene el nombre legible del tipo de reporte
 */
export const getReportTypeName = (reportType: string): string => {
  const names: Record<string, string> = {
    executive: 'Reporte Ejecutivo',
    alerts: 'Reporte de Alertas',
    statistical: 'Anuario Estadístico',
    career: 'Reporte por Carrera',
    sentiment_dataset: 'Dataset de Sentimientos',
    pivot_table: 'Tabla Pivote',
    anomalies: 'Reporte de Anomalías',
    combined: 'Reporte Combinado',
    other: 'Otro'
  };
  return names[reportType] || names.other;
};

/**
 * Obtiene el color del badge según el estado
 */
export const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    PENDING: 'yellow',
    STARTED: 'blue',
    PROGRESS: 'blue',
    SUCCESS: 'green',
    FAILURE: 'red',
    running: 'blue',
    completed: 'green',
    failed: 'red'
  };
  return colors[status] || 'gray';
};

/**
 * Formatea la frecuencia de programación
 */
export const formatFrequency = (
  frequency: string,
  dayOfWeek?: number,
  dayOfMonth?: number,
  hour?: number,
  minute?: number
): string => {
  const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
  const time = `${hour?.toString().padStart(2, '0')}:${(minute || 0).toString().padStart(2, '0')}`;
  
  switch (frequency) {
    case 'daily':
      return `Diario a las ${time}`;
    case 'weekly':
      return `${days[dayOfWeek || 0]} a las ${time}`;
    case 'monthly':
      return `Día ${dayOfMonth} de cada mes a las ${time}`;
    default:
      return frequency;
  }
};

// Export default object
const reportsService = {
  // Generación
  generatePDFReport,
  generateExcelReport,
  generateReport,
  
  // Estado
  getTaskStatus,
  pollTaskStatus,
  
  // Descarga e historial
  downloadReport,
  downloadAndSaveReport,
  getReportsHistory,
  deleteReport,
  
  // Programaciones
  getSchedules,
  getSchedule,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  toggleSchedule,
  runScheduleNow,
  getScheduleHistory,
  
  // Email
  sendReportEmail,
  
  // Estadísticas
  getReportsStats,
  
  // Utilidades
  formatFileSize,
  getReportIcon,
  getReportTypeName,
  getStatusColor,
  formatFrequency
};

export default reportsService;
