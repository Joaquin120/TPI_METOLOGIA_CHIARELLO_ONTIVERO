"""Esquemas Pydantic del contrato HTTP (design D5).

Contrato por **nombres** de recurso, igual que el dominio y
`RepositorioTurnosSqlite`: no se inventan `*_id` que el dominio aún no acepta.
`extra="forbid"` impide que el cliente inyecte `tenant_id` (el tenant lo resuelve
la capa de presentación). No se valida `hora_inicio < hora_fin` (RP-01 abierta).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from src.domain.models import BloqueoSillon, EntradaListaEspera, Paciente, Profesional, RegistroAuditoria, Sillon, Turno

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
FechaSintetica = Annotated[str, Field(pattern=PATRON_FECHA, description="Fecha YYYY-MM-DD")]
HoraSintetica = Annotated[str, Field(pattern=PATRON_HORA, description="Hora HH:MM")]


class TurnoCrear(BaseModel):
    """Cuerpo de `POST /api/v1/turnos` (contrato por nombres, design D5)."""

    model_config = ConfigDict(extra="forbid")

    paciente: TextoRequerido
    profesional: TextoRequerido
    sillon: TextoRequerido
    fecha: Annotated[TextoRequerido, Field(pattern=PATRON_FECHA)]
    hora_inicio: Annotated[TextoRequerido, Field(pattern=PATRON_HORA)]
    hora_fin: Annotated[TextoRequerido, Field(pattern=PATRON_HORA)]
    telefono: str | None = None


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


class MetricasTurnosRespuesta(BaseModel):
    """Salida de `GET /api/v1/metricas/turnos` (C-08)."""

    total: int
    por_estado: dict[str, int]
    tasa_cancelacion: float
    fecha_desde: str | None = None
    fecha_hasta: str | None = None


class MetricaProfesionalItem(BaseModel):
    """Item de distribución de turnos por profesional."""

    profesional_id: int
    nombre: str
    total_turnos: int


class MetricaSillonItem(BaseModel):
    """Item de distribución de turnos por sillón."""

    sillon_id: int
    nombre: str
    total_turnos: int


class MetricasRecursosRespuesta(BaseModel):
    """Salida de `GET /api/v1/metricas/recursos` (C-08)."""

    profesionales: list[MetricaProfesionalItem]
    sillones: list[MetricaSillonItem]
    fecha_desde: str | None = None
    fecha_hasta: str | None = None


class RegistroAuditoriaRespuesta(BaseModel):
    """Salida de cada ítem de `GET /api/v1/auditoria` (C-09)."""

    id: int
    tenant_id: int
    usuario_id: int
    accion: str
    entidad: str
    entidad_id: int | None = None
    detalle: str | None = None
    fecha_hora: str

    @classmethod
    def desde_dominio(
        cls, registro: RegistroAuditoria
    ) -> "RegistroAuditoriaRespuesta":
        if registro.id is None:
            raise ValueError("El registro de auditoría debe tener un id asignado")
        return cls(
            id=registro.id,
            tenant_id=registro.tenant_id,
            usuario_id=registro.usuario_id,
            accion=registro.accion,
            entidad=registro.entidad,
            entidad_id=registro.entidad_id,
            detalle=registro.detalle,
            fecha_hora=registro.fecha_hora,
        )


class ReprogramarTurnoPeticion(BaseModel):
    """Cuerpo de `PATCH /api/v1/turnos/{id}/reprogramar` (C-08b)."""

    model_config = ConfigDict(extra="forbid")

    fecha: Annotated[str, Field(pattern=PATRON_FECHA)]
    hora_inicio: Annotated[str, Field(pattern=PATRON_HORA)]
    hora_fin: Annotated[str, Field(pattern=PATRON_HORA)]
    profesional_id: int | None = None
    sillon_id: int | None = None
    motivo: str | None = None

    @model_validator(mode="after")
    def validar_consistencia_horaria(self) -> "ReprogramarTurnoPeticion":
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("hora_inicio debe ser anterior a hora_fin")
        return self


class ProfesionalCrear(BaseModel):
    """Cuerpo de `POST /api/v1/profesionales` (C-09b)."""

    model_config = ConfigDict(extra="forbid")

    nombre: TextoRequerido
    matricula: str | None = None
    especialidad: str | None = None
    activo: bool = True


class ProfesionalActualizar(BaseModel):
    """Cuerpo de `PUT /api/v1/profesionales/{id}` (C-09b)."""

    model_config = ConfigDict(extra="forbid")

    nombre: TextoRequerido
    matricula: str | None = None
    especialidad: str | None = None
    activo: bool


class SillonCrear(BaseModel):
    """Cuerpo de `POST /api/v1/sillones` (C-09b)."""

    model_config = ConfigDict(extra="forbid")

    nombre: TextoRequerido
    equipamiento: str | None = None
    activo: bool = True


class SillonActualizar(BaseModel):
    """Cuerpo de `PUT /api/v1/sillones/{id}` (C-09b)."""

    model_config = ConfigDict(extra="forbid")

    nombre: TextoRequerido
    equipamiento: str | None = None
    activo: bool


class BloqueoCrear(BaseModel):
    """Cuerpo de `POST /api/v1/bloqueos` (C-10)."""

    model_config = ConfigDict(extra="forbid")

    sillon_id: int
    fecha: Annotated[TextoRequerido, Field(pattern=PATRON_FECHA)]
    hora_inicio: Annotated[TextoRequerido, Field(pattern=PATRON_HORA)]
    hora_fin: Annotated[TextoRequerido, Field(pattern=PATRON_HORA)]
    telefono: str | None = None
    motivo: TextoRequerido

    @model_validator(mode="after")
    def validar_consistencia_horaria(self) -> "BloqueoCrear":
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("hora_inicio debe ser anterior a hora_fin")
        return self


class BloqueoRespuesta(BaseModel):
    """Salida de `POST /api/v1/bloqueos` y de cada ítem de `GET /api/v1/bloqueos`."""

    id: int
    tenant_id: int
    sillon_id: int
    fecha_hora_inicio: str
    fecha_hora_fin: str
    motivo: str
    creado_por: int | None = None
    creado_en: str | None = None

    @classmethod
    def desde_dominio(cls, bloqueo: BloqueoSillon) -> "BloqueoRespuesta":
        if bloqueo.id is None:
            raise ValueError("El bloqueo debe tener un id asignado")
        return cls(
            id=bloqueo.id,
            tenant_id=bloqueo.tenant_id,
            sillon_id=bloqueo.sillon_id,
            fecha_hora_inicio=bloqueo.fecha_hora_inicio,
            fecha_hora_fin=bloqueo.fecha_hora_fin,
            motivo=bloqueo.motivo,
            creado_por=bloqueo.creado_por,
            creado_en=bloqueo.creado_en,
        )


class WebhookWhatsAppPeticion(BaseModel):
    """Cuerpo de solicitud recibido en el webhook de WhatsApp (C-14)."""

    model_config = ConfigDict(extra="ignore")

    accion: Literal["CONFIRMAR", "CANCELAR", "confirmar", "cancelar"]
    turno_id: int
    telefono: str | None = None
    motivo: str | None = None


class WebhookWhatsAppRespuesta(BaseModel):
    """Respuesta devuelta tras procesar un evento de webhook de WhatsApp."""

    mensaje: str
    turno_id: int
    estado_actual: str
    accion_procesada: str


class EntradaListaEsperaCrear(BaseModel):
    """Cuerpo de solicitud para registrar una entrada en lista de espera (C-15, F-08)."""

    model_config = ConfigDict(extra="forbid")

    paciente_nombre: TextoRequerido
    paciente_telefono: TelefonoSintetico
    fecha_deseada: FechaSintetica
    motivo: TextoRequerido
    profesional_nombre: str | None = None
    franja_horaria: str | None = None


class EntradaListaEsperaRespuesta(BaseModel):
    """Respuesta para entradas en lista de espera."""

    id: int
    tenant_id: int
    paciente_nombre: str
    paciente_telefono: str
    fecha_deseada: str
    motivo: str
    profesional_nombre: str | None = None
    franja_horaria: str | None = None
    estado: str
    creado_en: str | None = None

    @classmethod
    def desde_dominio(cls, entrada: EntradaListaEspera) -> "EntradaListaEsperaRespuesta":
        if entrada.id is None:
            raise ValueError("La entrada debe tener un id asignado")
        return cls(
            id=entrada.id,
            tenant_id=entrada.tenant_id,
            paciente_nombre=entrada.paciente_nombre,
            paciente_telefono=entrada.paciente_telefono,
            fecha_deseada=entrada.fecha_deseada,
            motivo=entrada.motivo,
            profesional_nombre=entrada.profesional_nombre,
            franja_horaria=entrada.franja_horaria,
            estado=entrada.estado,
            creado_en=entrada.creado_en,
        )


class AsignarTurnoListaEspera(BaseModel):
    """Cuerpo de solicitud para asignar un turno definitivo desde lista de espera (C-15)."""

    model_config = ConfigDict(extra="forbid")

    profesional_id: int
    sillon_id: int
    fecha: FechaSintetica
    hora_inicio: HoraSintetica
    hora_fin: HoraSintetica








