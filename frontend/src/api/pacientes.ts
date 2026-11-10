import { clienteApi } from './cliente';
import { Paciente, PacienteCrearPeticion } from '../types';

export async function listarPacientes(filtros?: { dni?: string; nombre?: string }): Promise<Paciente[]> {
  const params = new URLSearchParams();
  if (filtros?.dni) params.append('dni', filtros.dni);
  if (filtros?.nombre) params.append('nombre', filtros.nombre);

  const query = params.toString() ? `?${params.toString()}` : '';
  return clienteApi.get<Paciente[]>(`/pacientes${query}`);
}

export async function crearPaciente(paciente: PacienteCrearPeticion): Promise<Paciente> {
  return clienteApi.post<Paciente>('/pacientes', paciente);
}
