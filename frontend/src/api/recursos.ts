import { clienteApi } from './cliente';
import { Profesional, Sillon, Bloqueo } from '../types';

export async function listarProfesionales(soloActivos: boolean = true): Promise<Profesional[]> {
  const query = soloActivos ? '?solo_activos=true' : '?solo_activos=false';
  return clienteApi.get<Profesional[]>(`/profesionales${query}`);
}

export async function listarSillones(soloActivos: boolean = true): Promise<Sillon[]> {
  const query = soloActivos ? '?solo_activos=true' : '?solo_activos=false';
  return clienteApi.get<Sillon[]>(`/sillones${query}`);
}

export async function listarBloqueos(filtros?: {
  sillon_id?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
}): Promise<Bloqueo[]> {
  const params = new URLSearchParams();
  if (filtros?.sillon_id) params.append('sillon_id', String(filtros.sillon_id));
  if (filtros?.fecha_desde) params.append('fecha_desde', filtros.fecha_desde);
  if (filtros?.fecha_hasta) params.append('fecha_hasta', filtros.fecha_hasta);

  const query = params.toString() ? `?${params.toString()}` : '';
  return clienteApi.get<Bloqueo[]>(`/bloqueos${query}`);
}
