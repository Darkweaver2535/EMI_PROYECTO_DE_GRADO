/**
 * Servicio de Análisis DeepSeek (capa post-BERT)
 * Sistema OSINT EMI
 */

import api from './api';

export interface DeepSeekTemaCritico {
  tema: string;
  severidad: string;
  descripcion: string;
}

export interface DeepSeekCarreraDestacada {
  careerId?: string;
  careerName?: string;
  observacion?: string;
  menciones?: number;
}

export interface DeepSeekInsights {
  disponible: boolean;
  mensaje?: string;
  resumenEjecutivo?: string;
  sentimientoGeneral?: string;
  temasCriticos?: DeepSeekTemaCritico[];
  recomendaciones?: string[];
  carrerasDestacadas?: DeepSeekCarreraDestacada[];
  totalAnalizados?: number;
  fecha?: string;
}

export interface DeepSeekStatus {
  analizados: number;
  total: number;
  pendientes: number;
  ejecutando: boolean;
  ultimoResultado: Record<string, unknown> | null;
}

export const deepseekService = {
  /** Resumen ejecutivo agregado generado por DeepSeek. */
  async getInsights(): Promise<DeepSeekInsights> {
    const { data } = await api.get<DeepSeekInsights>('/ai/deepseek/insights');
    return data;
  },

  /** Estado: cuántos ítems se analizaron vs pendientes. */
  async getStatus(): Promise<DeepSeekStatus> {
    const { data } = await api.get<DeepSeekStatus>('/ai/deepseek/status');
    return data;
  },

  /** Dispara el análisis DeepSeek en segundo plano. */
  async ejecutar(force = false): Promise<{ status: string; mensaje: string }> {
    const { data } = await api.post('/ai/deepseek/ejecutar', { force });
    return data;
  },
};

export default deepseekService;
