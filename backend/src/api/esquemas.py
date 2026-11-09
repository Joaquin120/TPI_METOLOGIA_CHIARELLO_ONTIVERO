"""Esquemas Pydantic del contrato HTTP (design D5).

Contrato por **nombres** de recurso, igual que el dominio y
`RepositorioTurnosSqlite`: no se inventan `*_id` que el dominio aún no acepta.
`extra="forbid"` impide que el cliente inyecte `tenant_id` (el tenant lo resuelve
la capa de presentación). No se valida `hora_inicio < hora_fin` (RP-01 abierta).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.domain.models import Paciente, Profesional, Sillon, Turno

# `YYYY-MM-DD` (ISO-8601, fecha completa).
PATRON_FECHA = r"^\d{4}-\d{2}-\d{2}$"
# `HH:MM` 24 h estricto: 00-23 : 00-59.
PATRON_HORA = r"^([01]\d|2[0-3]):[0-5]\d$"
# DNI de 8 dígitos numéricos (RN-06).
PATRON_DNI = r"^\d{8}$"
# Teléfono estándar (longitud 7 a 20 caracteres numéricos y separadores).
PATRON_TELEFONO = r"^\+?[0-9\s\-\(\)]{7,20}$"

# Campo de texto obligatorio y no vacío: se recortan extremos, pero se conservan
# los espacios internos de nombres como "Paciente Ficticio 2".
TextoRequerido = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
DniSintetico = Annotated[str, Field(pattern=PATRON_DNI, description="DNI ficticio de 8 dígitos")]
TelefonoSintetico = Annotated[str, Field(pattern=PATRON_TELEFONO, description="Formato de teléfono")]


class TurnoCrear(BaseModel):
    """Cuerpo de `POST /api/v1/turnos` (contrato por nombres, design D5)."""

    model_config = ConfigDict(extra="forbid")

    paciente: TextoRequerido
    profesional: TextoRequerido
    sillon: TextoRequerido
    fecha: Annotated[TextoRequerido, Field(pattern=PATRON_FECHA)]
    hora_inicio: Annotated[TextoRequerido, Field(pattern=PATRON_HORA)]
    hora_fin: Annotated[TextoRequerido, Field(pattern=PATRON_HORA)]


class TurnoRespuesta(BaseModel):
    """Salida de `POST /api/v1/turnos` y de cada ítem de `GET /api/v1/turnos`."""

    id: int | None
    paciente: str
    profesional: str
    sillon: str
    fecha: str
    hora_inicio: str
    hora_fin: str
    estado: str

    @classmethod
    def desde_dominio(cls, turno: Turno) -> "TurnoRespuesta":
        """Mapea 1:1 desde la entidad de dominio (sin ids de recurso)."""
        return cls(
            id=turno.id,
            paciente=turno.paciente,
            profesional=turno.profesional.nombre,
            sillon=turno.sillon.nombre,
            fecha=turno.fecha,
            hora_inicio=turno.hora_inicio,
            hora_fin=turno.hora_fin,
            estado=turno.estado,
        )


class TurnoCambioEstado(BaseModel):
    """Cuerpo de `PATCH /api/v1/turnos/{id}/estado` (C-05)."""

    model_config = ConfigDict(extra="forbid")

    accion: Literal["confirmar", "cancelar", "completar"]


class LoginSolicitud(BaseModel):
    """Cuerpo de `POST /api/v1/auth/login` (C-04, task 3.1)."""

    model_config = ConfigDict(extra="forbid")

    email: TextoRequerido
    password: str = Field(min_length=1)
    tenant_id: int | None = None


class TokenRespuesta(BaseModel):
    """Salida de `POST /api/v1/auth/login` (C-04, task 3.1)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UsuarioPerfilRespuesta(BaseModel):
    """Salida de `GET /api/v1/auth/me` (C-04, task 3.1)."""

    id: int
    email: str
    tenant_id: int
    rol: str
    profesional_id: int | None = None


class ProfesionalRespuesta(BaseModel):
    """Salida de cada ítem de `GET /api/v1/profesionales` (C-06, design D4)."""

    id: int
    nombre: str
    matricula: str | None = None
    especialidad: str | None = None
    activo: bool

    @classmethod
    def desde_dominio(cls, profesional: Profesional) -> "ProfesionalRespuesta":
        if profesional.id is None:
            raise ValueError("El profesional debe tener un id asignado")
        return cls(
            id=profesional.id,
            nombre=profesional.nombre,
            matricula=profesional.matricula,
            especialidad=profesional.especialidad,
            activo=profesional.activo,
        )


class SillonRespuesta(BaseModel):
    """Salida de cada ítem de `GET /api/v1/sillones` (C-06, design D4)."""

    id: int
    nombre: str
    equipamiento: str | None = None
    activo: bool

    @classmethod
    def desde_dominio(cls, sillon: Sillon) -> "SillonRespuesta":
        if sillon.id is None:
            raise ValueError("El sillón debe tener un id asignado")
        return cls(
            id=sillon.id,
            nombre=sillon.nombre,
            equipamiento=sillon.equipamiento,
            activo=sillon.activo,
        )


class PacienteCrear(BaseModel):
    """Cuerpo de `POST /api/v1/pacientes` (C-07)."""

    model_config = ConfigDict(extra="forbid")

    dni: DniSintetico
    nombre: TextoRequerido
    telefono: TelefonoSintetico


class PacienteRespuesta(BaseModel):
    """Salida de `POST /api/v1/pacientes` y `GET /api/v1/pacientes` (C-07)."""

    id: int
    tenant_id: int
    dni: str
    nombre: str
    telefono: str

    @classmethod
    def desde_dominio(cls, paciente: Paciente) -> "PacienteRespuesta":
        if paciente.id is None:
            raise ValueError("El paciente debe tener un id asignado")
        return cls(
            id=paciente.id,
            tenant_id=paciente.tenant_id,
            dni=paciente.dni,
            nombre=paciente.nombre,
            telefono=paciente.telefono,
        )


class PacienteFiltro(BaseModel):
    """Filtros opcionales para `GET /api/v1/pacientes`."""

    dni: str | None = None
    nombre: str | None = None


