/**
 * Servicio de Usuarios
 * Sistema OSINT EMI
 */

import api from './api';

export interface UsuarioPermisos {
  osint: boolean;
  posts: boolean;
  dashboards: boolean;
  nlp: boolean;
  evaluacion: boolean;
  usuarios: boolean;
  configuracion: boolean;
}

export interface UsuarioData {
  id?: number;
  username: string;
  email: string;
  nombre_completo: string;
  rol: 'administrador' | 'vicerrector' | 'uebu';
  cargo?: string;
  activo?: boolean;
  password?: string;
  ultimo_login?: string;
  fecha_creacion?: string;
  permisos?: UsuarioPermisos;
}

export interface RolInfo {
  id: string;
  nombre: string;
  descripcion: string;
}

export const usuariosService = {
  async getUsuarios(): Promise<{ usuarios: UsuarioData[]; total: number }> {
    const { data } = await api.get('/usuarios');
    return data;
  },

  async getUsuario(id: number): Promise<UsuarioData> {
    const { data } = await api.get(`/usuarios/${id}`);
    return data;
  },

  async createUsuario(usuario: UsuarioData): Promise<{ id: number; message: string }> {
    const { data } = await api.post('/usuarios', usuario);
    return data;
  },

  async updateUsuario(id: number, usuario: Partial<UsuarioData>): Promise<{ message: string }> {
    const { data } = await api.put(`/usuarios/${id}`, usuario);
    return data;
  },

  async deleteUsuario(id: number): Promise<{ message: string }> {
    const { data } = await api.delete(`/usuarios/${id}`);
    return data;
  },

  async getRoles(): Promise<{ roles: RolInfo[] }> {
    const { data } = await api.get('/usuarios/roles');
    return data;
  },

  async getLogs(limit?: number): Promise<{ logs: Array<{
    id: number;
    usuario: string;
    nombre_usuario: string;
    accion: string;
    detalle: string;
    ip: string;
    fecha: string;
  }>; total: number }> {
    const { data } = await api.get('/logs', { params: { limit: limit || 50 } });
    return data;
  },
};

export default usuariosService;
