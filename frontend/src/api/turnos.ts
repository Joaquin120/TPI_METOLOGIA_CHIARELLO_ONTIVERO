import { clienteApi } from './cliente';
import { Turno, TurnoCrearPeticion, ReprogramarTurnoPeticion } from '../types';

export async function listarTurnos(filtros?: {
  fecha?: string;
  profesional_id?: number;
  sillon_id?: number;
}): Promise<Turno[]> {
  const params = new URLSearchParams();
  if (filtros?.fecha) params.append('fecha', filtros.fecha);
  if (filtros?.profesional_id) params.append('profesional_id', String(filtros.profesional_id));
  if (filtros?.sillon_id) params.append('sillon_id', String(filtros.sillon_id));

  const query = params.toString() ? `?${params.toString()}` : '';
  return clienteApi.get<Turno[]>(`/turnos${query}`);
}

export async function crearTurno(turno: TurnoCrearPeticion): Promise<Turno> {
  return clienteApi.post<Turno>('/turnos', turno);
}

export async function cambiarEstadoTurno(
  id: number,
  accion: 'confirmar' | 'cancelar' | 'completar'
): Promise<Turno> {
  return clienteApi.patch<Turno>(`/turnos/${id}/estado`, { accion });
}

export async function reprogramarTurno(
  id: number,
  datos: ReprogramarTurnoPeticion
): Promise<Turno> {
  return clienteApi.patch<Turno>(`/turnos/${id}/reprogramar`, datos);
}
