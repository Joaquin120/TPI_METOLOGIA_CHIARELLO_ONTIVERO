import { clienteApi } from './cliente';
import { RegistroAuditoria } from '../types';

export async function listarAuditoria(filtros?: {
  usuario_id?: number;
  accion?: string;
  entidad?: string;
}): Promise<RegistroAuditoria[]> {
  const params = new URLSearchParams();
  if (filtros?.usuario_id) params.append('usuario_id', String(filtros.usuario_id));
  if (filtros?.accion) params.append('accion', filtros.accion);
  if (filtros?.entidad) params.append('entidad', filtros.entidad);

  const query = params.toString() ? `?${params.toString()}` : '';
  return clienteApi.get<RegistroAuditoria[]>(`/auditoria${query}`);
}
