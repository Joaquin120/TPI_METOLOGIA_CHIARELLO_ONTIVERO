"""Modelos de dominio para la gestión de turnos odontológicos."""

from dataclasses import dataclass

# Constantes de estado del turno (fuente de verdad de `Turno.estado`).
# Se usan como texto plano — no un Enum — para preservar la igualdad literal
# `turno.estado == "CONFIRMADO"` y la persistencia futura como texto (design D1).
PENDIENTE = "PENDIENTE"
CONFIRMADO = "CONFIRMADO"
CANCELADO = "CANCELADO"
COMPLETADO = "COMPLETADO"

# Estados que siguen bloqueando profesional y sillón en `agendar_turno()`
# (RN-04: al cancelar/liberarse, el turno deja de ser activo) — design D4/D5.
ESTADOS_ACTIVOS = frozenset({PENDIENTE, CONFIRMADO})


@dataclass(frozen=True)
class Paciente:
    """Entidad de dominio que representa a una persona atendida en una clínica."""

    dni: str
    nombre: str
    telefono: str
    tenant_id: int
    id: int | None = None


@dataclass(frozen=True)
class Profesional:
    """Profesional de la salud que atiende turnos."""

    nombre: str
    id: int | None = None
    matricula: str | None = None
    especialidad: str | None = None
    activo: bool = True


@dataclass(frozen=True)
class Sillon:
    """Sillón/box odontológico en el que se realiza la atención."""

    nombre: str
    id: int | None = None
    equipamiento: str | None = None
    activo: bool = True


@dataclass(frozen=True)
class Turno:
    """Turno odontológico confirmado en un intervalo semiabierto [hora_inicio, hora_fin)."""

    profesional: Profesional
    sillon: Sillon
    fecha: str
    hora_inicio: str
    hora_fin: str
    paciente: str
    estado: str = CONFIRMADO
    id: int | None = None


@dataclass(frozen=True)
class RegistroAuditoria:
    """Entidad de dominio que representa un evento de auditoría del sistema (C-09)."""

    tenant_id: int
    usuario_id: int
    accion: str
    entidad: str
    fecha_hora: str
    entidad_id: int | None = None
    detalle: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class BloqueoSillon:
    """Entidad de dominio que representa un bloqueo temporal de un sillón/box (C-10, F-12, RN-07)."""

    tenant_id: int
    sillon_id: int
    fecha_hora_inicio: str  # formato 'YYYY-MM-DD HH:MM'
    fecha_hora_fin: str     # formato 'YYYY-MM-DD HH:MM'
    motivo: str
    creado_por: int | None = None
    creado_en: str | None = None
    id: int | None = None


