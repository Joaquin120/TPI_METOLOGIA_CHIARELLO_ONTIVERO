"""Router de recursos clínicos: consulta de profesionales y sillones (C-06, F-04, F-05, PA-01).

Permite listar los recursos disponibles dentro del tenant del usuario autenticado.
El filtrado por activo permite a la recepción obtener solo recursos operativos.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencias import (
    ContextoRecursos,
    ContextoUsuario,
    contexto_recursos,
    requerir_rol,
)
from src.api.esquemas import ProfesionalRespuesta, SillonRespuesta

router = APIRouter(tags=["recursos"])


@router.get("/profesionales", response_model=list[ProfesionalRespuesta])
def listar_profesionales(
    contexto: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    _usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_rol("Administrador", "Recepcionista", "Profesional")),
    ],
    solo_activos: Annotated[
        bool,
        Query(description="Si es True, devuelve solo profesionales activos (default: True)"),
    ] = True,
) -> list[ProfesionalRespuesta]:
    """Devuelve los profesionales del tenant autenticado con sus datos operativos."""
    profesionales = contexto.profesionales.listar(solo_activos=solo_activos)
    return [ProfesionalRespuesta.desde_dominio(p) for p in profesionales]


@router.get("/sillones", response_model=list[SillonRespuesta])
def listar_sillones(
    contexto: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    _usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_rol("Administrador", "Recepcionista", "Profesional")),
    ],
    solo_activos: Annotated[
        bool,
        Query(description="Si es True, devuelve solo sillones activos (default: True)"),
    ] = True,
) -> list[SillonRespuesta]:
    """Devuelve los sillones del tenant autenticado con su equipamiento y estado."""
    sillones = contexto.sillones.listar(solo_activos=solo_activos)
    return [SillonRespuesta.desde_dominio(s) for s in sillones]

