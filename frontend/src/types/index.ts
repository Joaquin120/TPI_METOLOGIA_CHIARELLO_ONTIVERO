export type Rol = 'Administrador' | 'Recepcionista' | 'Profesional';

export interface Usuario {
  id: number;
  email: string;
  rol: Rol;
  tenant_id: number;
  nombre?: string;
  activo?: boolean;
  profesional_id?: number | null;
}

export interface Credenciales {
  email: string;
  password: string;
  tenant_id?: number;
}

export interface TokenRespuesta {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRespuesta {
  access_token: string;
  token_type: string;
  expires_in?: number;
  usuario: Usuario;
}

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface ErrorEnvelope {
  error: ApiError;
}

export type EstadoTurno = 'PENDIENTE' | 'CONFIRMADO' | 'CANCELADO' | 'COMPLETADO';

export interface Turno {
  id: number | null;
  paciente: string;
  profesional: string;
  sillon: string;
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
  estado: EstadoTurno;
}

export interface TurnoCrearPeticion {
  paciente: string;
  profesional: string;
  sillon: string;
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
}

export interface ReprogramarTurnoPeticion {
  fecha: string;
  hora_inicio: string;
  hora_fin: string;
  profesional_id?: number | null;
  sillon_id?: number | null;
  motivo?: string | null;
}

export interface Paciente {
  id: number;
  tenant_id: number;
  dni: string;
  nombre: string;
  telefono: string;
}

export interface PacienteCrearPeticion {
  dni: string;
  nombre: string;
  telefono: string;
}

export interface Profesional {
  id: number;
  nombre: string;
  matricula?: string | null;
  especialidad?: string | null;
  activo: boolean;
}

export interface Sillon {
  id: number;
  nombre: string;
  equipamiento?: string | null;
  activo: boolean;
}

export interface Bloqueo {
  id: number;
  tenant_id: number;
  sillon_id: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  motivo: string;
  creado_por?: number | null;
  creado_en?: string | null;
}

export interface RegistroAuditoria {
  id: number;
  tenant_id: number;
  usuario_id: number;
  accion: string;
  entidad: string;
  entidad_id?: number | null;
  detalle?: string | null;
  fecha_hora: string;
}
