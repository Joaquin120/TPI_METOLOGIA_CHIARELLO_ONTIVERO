"""Router de turnos: alta y listado del tenant resuelto (design D5).

La API solo traduce HTTP ↔ dominio: la doble validación de profesional y sillón
y el estado inicial del alta viven en `ServicioTurnos` (`src.domain`). Aquí no se
importa `buscar_activos_solapables`, `ESTADOS_ACTIVOS` ni reglas de transición.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencias import (
    ContextoTurnos,
    ContextoUsuario,
    contexto_turnos,
    obtener_usuario_actual,
    requerir_rol,
)
from src.api.errores import ErrorAccesoDenegado, ErrorTurnoNoEncontrado
from src.api.esquemas import (
    PATRON_FECHA,
    TurnoCambioEstado,
    TurnoCrear,
    TurnoRespuesta,
)
from src.domain.models import Profesional, Sillon

router = APIRouter(tags=["turnos"])


def _argumentos_de_dominio(datos: TurnoCrear) -> dict[str, object]:
    """Mapea el contrato por nombres a los argumentos de `agendar_turno`."""
    return {
        "paciente": datos.paciente,
        "fecha": datos.fecha,
        "hora_inicio": datos.hora_inicio,
        "hora_fin": datos.hora_fin,
        "profesional": Profesional(nombre=datos.profesional),
        "sillon": Sillon(nombre=datos.sillon),
    }


@router.post(
    "/turnos", status_code=status.HTTP_201_CREATED, response_model=TurnoRespuesta
)
def crear_turno(
    datos: TurnoCrear,
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
) -> TurnoRespuesta:
    """Delega el alta en el dominio y serializa el turno creado."""
    turno = contexto.servicio.agendar_turno(**_argumentos_de_dominio(datos))
    return TurnoRespuesta.desde_dominio(turno)


@router.get("/turnos", response_model=list[TurnoRespuesta])
def listar_turnos(
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    usuario: Annotated[ContextoUsuario, Depends(obtener_usuario_actual)],
    fecha: Annotated[
        str | None, Query(pattern=PATRON_FECHA, description="Fecha YYYY-MM-DD")
    ] = None,
    profesional_id: Annotated[
        int | None, Query(description="ID del profesional")
    ] = None,
    sillon_id: Annotated[int | None, Query(description="ID del sillón")] = None,
) -> list[TurnoRespuesta]:
    """Devuelve turnos del tenant resuelto aplicando filtros opcionales."""
    if usuario.rol == "Profesional":
        if usuario.profesional_id is None:
            raise ErrorAccesoDenegado("Usuario profesional sin recurso asociado")
        if profesional_id is not None and profesional_id != usuario.profesional_id:
            raise ErrorAccesoDenegado(
                "El profesional solo puede consultar su propia agenda"
            )
        profesional_id = usuario.profesional_id

    return [
        TurnoRespuesta.desde_dominio(turno)
        for turno in contexto.servicio.turnos_registrados(
            fecha=fecha,
            profesional_id=profesional_id,
            sillon_id=sillon_id,
        )
    ]


@router.patch("/turnos/{id}/estado", response_model=TurnoRespuesta)
def cambiar_estado_turno(
    id: int,
    datos: TurnoCambioEstado,
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
) -> TurnoRespuesta:
    """Cambia el estado de un turno delegando la transición al dominio."""
    turno = contexto.servicio.obtener_por_id(id)
    if turno is None:
        raise ErrorTurnoNoEncontrado(f"El turno {id} no existe en este tenant")

    if datos.accion == "confirmar":
        actualizado = contexto.servicio.confirmar(turno)
    elif datos.accion == "cancelar":
        actualizado = contexto.servicio.cancelar(turno)
    else:
        actualizado = contexto.servicio.completar(turno)

    return TurnoRespuesta.desde_dominio(actualizado)

