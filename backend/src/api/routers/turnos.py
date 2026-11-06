"""Router de turnos: alta y listado del tenant resuelto (design D5).

La API solo traduce HTTP ↔ dominio: la doble validación de profesional y sillón
y el estado inicial del alta viven en `ServicioTurnos` (`src.domain`). Aquí no se
importa `buscar_activos_solapables`, `ESTADOS_ACTIVOS` ni reglas de transición.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.api.dependencias import (
    ContextoTurnos,
    ContextoUsuario,
    contexto_turnos,
    requerir_rol,
)
from src.api.esquemas import TurnoCrear, TurnoRespuesta
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
) -> list[TurnoRespuesta]:
    """Devuelve solo los turnos del tenant resuelto (sin filtros ni paginación)."""
    return [
        TurnoRespuesta.desde_dominio(turno)
        for turno in contexto.servicio.turnos_registrados()
    ]
