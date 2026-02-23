/**
 * Servicio de Configuración de Alertas
 * Sistema OSINT EMI
 */

import api from './api';

export interface ConfigAlerta {
  id: number;
  nombre: string;
  tipo_alerta: string;
  umbral_valor: number;
  umbral_confianza: number;
  severidad_minima: string;
  activa: boolean;
  notificar_email: boolean;
  creado_por: number | null;
  fecha_creacion: string;
}

export const configuracionService = {
  async getConfiguraciones(): Promise<{ configuraciones: ConfigAlerta[]; total: number }> {
    const { data } = await api.get('/configuracion-alertas');
    return data;
  },

  async updateConfiguracion(id: number, config: Partial<ConfigAlerta>): Promise<{ message: string }> {
    const { data } = await api.put(`/configuracion-alertas/${id}`, config);
    return data;
  },

  async createConfiguracion(config: Partial<ConfigAlerta>): Promise<{ id: number; message: string }> {
    const { data } = await api.post('/configuracion-alertas', config);
    return data;
  },

  async deleteConfiguracion(id: number): Promise<{ message: string }> {
    const { data } = await api.delete(`/configuracion-alertas/${id}`);
    return data;
  },
};

export default configuracionService;
