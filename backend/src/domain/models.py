"""Modelos de dominio para la gestión de turnos odontológicos."""

from dataclasses import dataclass, field

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


class TipoMensajeWhatsApp:
    """Tipos de mensajes gestionados por el subsistema de WhatsApp (C-14, F-07)."""

    ALTA_TURNO = "ALTA_TURNO"
    RECORDATORIO = "RECORDATORIO"
    CONFIRMACION = "CONFIRMACION"
    CANCELACION = "CANCELACION"
    VACANTE_LISTA_ESPERA = "VACANTE_LISTA_ESPERA"


@dataclass(frozen=True)
class MensajeWhatsApp:
    """Mensaje a ser despachado a través de WhatsApp."""

    destinatario_telefono: str
    contenido: str
    tipo: str = TipoMensajeWhatsApp.ALTA_TURNO
    turno_id: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoEnvio:
    """Resultado devuelto por el proveedor de mensajería externa."""

    exitoso: bool
    mensaje_id: str | None = None
    error: str | None = None


class EstadoListaEspera:
    """Estados del ciclo de vida de una entrada en lista de espera (C-15, F-08)."""

    PENDIENTE = "PENDIENTE"
    NOTIFICADO = "NOTIFICADO"
    ASIGNADO = "ASIGNADO"
    CANCELADO = "CANCELADO"


@dataclass(frozen=True)
class EntradaListaEspera:
    """Entrada de paciente en lista de espera ante vacantes o sobreturnos."""

    paciente_nombre: str
    paciente_telefono: str
    fecha_deseada: str
    motivo: str
    tenant_id: int = 1
    profesional_nombre: str | None = None
    franja_horaria: str | None = None
    estado: str = EstadoListaEspera.PENDIENTE
    creado_en: str | None = None
    id: int | None = None



