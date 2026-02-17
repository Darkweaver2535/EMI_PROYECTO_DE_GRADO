/**
 * Tipos para el Módulo de Reportes
 * Sistema de Analítica OSINT - EMI Bolivia
 * Sprint 5: Reportes y Estadísticas
 */

// ============================================================================
// TIPOS DE REPORTES
// ============================================================================

export type PDFReportType = 'executive' | 'alerts' | 'statistical' | 'career';
export type ExcelReportType = 'sentiment_dataset' | 'pivot_table' | 'anomalies' | 'combined';
export type ReportFileType = 'pdf' | 'excel';

export type ScheduleFrequency = 'daily' | 'weekly' | 'monthly';
export type TaskStatus = 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE';

// ============================================================================
// INTERFACES DE REPORTES
// ============================================================================

export interface ReportParams {
  start_date?: string;
  end_date?: string;
  severity?: string;
  days?: number;
  semester?: string;
  career_id?: number;
  career_name?: string;
  dimension?: 'career' | 'source' | 'month';
  threshold?: number;
  filters?: Record<string, any>;
  sections?: string[];
  include_sections?: string[];
}

export interface GenerateReportRequest {
  report_type: PDFReportType | ExcelReportType;
  params: ReportParams;
  async?: boolean;
}

export interface GenerateReportResponse {
  success: boolean;
  task_id?: string;
  message?: string;
  status_url?: string;
  error?: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  progress: number;
  message: string;
  result?: {
    success: boolean;
    file_path?: string;
    error?: string;
  };
  download_url?: string;
  error?: boolean;
}

export interface ReportFile {
  filename: string;
  file_type: ReportFileType;
  report_type: string;
  size_bytes: number;
  size_mb: number;
  created_at: string;
  download_url: string;
}

export interface ReportsHistoryResponse {
  success: boolean;
  reports: ReportFile[];
  total: number;
  error?: string;
}

// ============================================================================
// INTERFACES DE PROGRAMACIÓN
// ============================================================================

export interface ReportSchedule {
  id: number;
  name: string;
  report_type: PDFReportType | ExcelReportType;
  frequency: ScheduleFrequency;
  day_of_week?: number; // 0=Lunes, 6=Domingo
  day_of_month?: number; // 1-31
  hour: number;
  minute: number;
  params: ReportParams;
  recipients: string[];
  enabled: boolean;
  cron_expression: string;
  next_run?: string;
  last_run?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateScheduleRequest {
  name: string;
  report_type: PDFReportType | ExcelReportType;
  frequency: ScheduleFrequency;
  day_of_week?: number;
  day_of_month?: number;
  hour: number;
  minute?: number;
  params?: ReportParams;
  recipients: string[];
  enabled?: boolean;
}

export interface UpdateScheduleRequest extends Partial<CreateScheduleRequest> {}

export interface SchedulesListResponse {
  success: boolean;
  schedules: ReportSchedule[];
  total: number;
  error?: string;
}

export interface ScheduleResponse {
  success: boolean;
  schedule?: ReportSchedule;
  schedule_id?: number;
  message?: string;
  error?: string;
}

// ============================================================================
// INTERFACES DE EJECUCIÓN
// ============================================================================

export interface ExecutionLog {
  id: number;
  config_id: number;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed';
  file_path?: string;
  error_message?: string;
  email_sent: boolean;
}

export interface ExecutionHistoryResponse {
  success: boolean;
  history: ExecutionLog[];
  total: number;
  error?: string;
}

// ============================================================================
// INTERFACES DE EMAIL
// ============================================================================

export interface SendEmailRequest {
  recipients: string[];
  subject: string;
  body?: string;
  attachment: string;
}

export interface SendEmailResponse {
  success: boolean;
  task_id?: string;
  message?: string;
  status_url?: string;
  error?: string;
}

// ============================================================================
// INTERFACES DE ESTADÍSTICAS
// ============================================================================

export interface ReportsStats {
  reports: {
    pdf_count: number;
    excel_count: number;
    total_count: number;
    total_size_mb: number;
  };
  schedules: {
    total: number;
    active: number;
    inactive: number;
  };
  executions: {
    total: number;
    successful: number;
    failed: number;
    success_rate: number;
  };
}

export interface StatsResponse {
  success: boolean;
  stats?: ReportsStats;
  error?: string;
}

// ============================================================================
// INTERFACES DE UI
// ============================================================================

export interface ReportOption {
  value: PDFReportType | ExcelReportType;
  label: string;
  description: string;
  format: 'pdf' | 'excel';
  icon: string;
  requiredParams: string[];
}

export interface FrequencyOption {
  value: ScheduleFrequency;
  label: string;
  description: string;
}

export interface DayOption {
  value: number;
  label: string;
}

// ============================================================================
// CONSTANTES
// ============================================================================

export const PDF_REPORT_OPTIONS: ReportOption[] = [
  {
    value: 'executive',
    label: 'Reporte Ejecutivo',
    description: 'Resumen semanal con KPIs, gráficos y recomendaciones (8-12 páginas)',
    format: 'pdf',
    icon: '📊',
    requiredParams: ['start_date', 'end_date']
  },
  {
    value: 'alerts',
    label: 'Reporte de Alertas',
    description: 'Alertas críticas con detalle y acciones recomendadas (4-6 páginas)',
    format: 'pdf',
    icon: '🚨',
    requiredParams: []
  },
  {
    value: 'statistical',
    label: 'Anuario Estadístico',
    description: 'Análisis semestral completo con todos los indicadores (30-50 páginas)',
    format: 'pdf',
    icon: '📚',
    requiredParams: ['semester']
  },
  {
    value: 'career',
    label: 'Reporte por Carrera',
    description: 'Análisis detallado de una carrera específica (10-15 páginas)',
    format: 'pdf',
    icon: '🎓',
    requiredParams: ['career_id', 'career_name']
  }
];

export const EXCEL_REPORT_OPTIONS: ReportOption[] = [
  {
    value: 'sentiment_dataset',
    label: 'Dataset de Sentimientos',
    description: 'Datos completos de sentimiento con múltiples hojas de análisis',
    format: 'excel',
    icon: '📈',
    requiredParams: []
  },
  {
    value: 'pivot_table',
    label: 'Tabla Pivote',
    description: 'Análisis agregado por dimensión (carrera, fuente o mes)',
    format: 'excel',
    icon: '🔄',
    requiredParams: ['dimension']
  },
  {
    value: 'anomalies',
    label: 'Reporte de Anomalías',
    description: 'Detección de patrones anómalos en los datos',
    format: 'excel',
    icon: '⚠️',
    requiredParams: []
  },
  {
    value: 'combined',
    label: 'Reporte Combinado',
    description: 'Análisis completo con todas las métricas en un solo archivo',
    format: 'excel',
    icon: '📋',
    requiredParams: []
  }
];

export const FREQUENCY_OPTIONS: FrequencyOption[] = [
  {
    value: 'daily',
    label: 'Diario',
    description: 'Se ejecuta todos los días a la hora especificada'
  },
  {
    value: 'weekly',
    label: 'Semanal',
    description: 'Se ejecuta una vez por semana en el día especificado'
  },
  {
    value: 'monthly',
    label: 'Mensual',
    description: 'Se ejecuta una vez al mes en el día especificado'
  }
];

export const DAYS_OF_WEEK: DayOption[] = [
  { value: 0, label: 'Lunes' },
  { value: 1, label: 'Martes' },
  { value: 2, label: 'Miércoles' },
  { value: 3, label: 'Jueves' },
  { value: 4, label: 'Viernes' },
  { value: 5, label: 'Sábado' },
  { value: 6, label: 'Domingo' }
];

export const CAREER_OPTIONS = [
  { id: 1, name: 'Ingeniería de Sistemas' },
  { id: 2, name: 'Ingeniería Civil' },
  { id: 3, name: 'Ingeniería Industrial' },
  { id: 4, name: 'Ingeniería Mecatrónica' },
  { id: 5, name: 'Ingeniería Ambiental' },
  { id: 6, name: 'Ingeniería Petrolera' },
  { id: 7, name: 'Ingeniería Comercial' },
  { id: 8, name: 'Ingeniería de Telecomunicaciones' }
];

export const SEMESTER_OPTIONS = [
  { value: 'I-2024', label: 'Primer Semestre 2024' },
  { value: 'II-2023', label: 'Segundo Semestre 2023' },
  { value: 'I-2023', label: 'Primer Semestre 2023' },
  { value: 'II-2022', label: 'Segundo Semestre 2022' }
];
