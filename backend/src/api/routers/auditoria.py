"""Router de auditoría y trazabilidad operativa (C-09, RN-05, RN-06)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencias import (
    ContextoUsuario,
    obtener_repositorio_auditoria,
    requerir_rol,
)
from src.api.errores import ErrorRangoFechasInvalido
from src.api.esquemas import PATRON_FECHA, RegistroAuditoriaRespuesta
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


def _validar_rango_fechas(fecha_desde: str | None, fecha_hasta: str | None) -> None:
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ErrorRangoFechasInvalido(
            f"La fecha_desde '{fecha_desde}' no puede ser posterior a fecha_hasta '{fecha_hasta}'"
        )


@router.get("", response_model=list[RegistroAuditoriaRespuesta])
def listar_auditoria(
    usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_rol("Administrador")),
    ],
    repo: Annotated[
        RepositorioAuditoriaSqlite,
        Depends(obtener_repositorio_auditoria),
    ],
    fecha_desde: Annotated[
        str | None,
        Query(description="Fecha inicio YYYY-MM-DD", pattern=PATRON_FECHA),
    ] = None,
    fecha_hasta: Annotated[
        str | None,
        Query(description="Fecha fin YYYY-MM-DD", pattern=PATRON_FECHA),
    ] = None,
    usuario_id: Annotated[int | None, Query(description="ID del usuario")] = None,
    accion: Annotated[str | None, Query(description="Acción auditada")] = None,
    entidad: Annotated[str | None, Query(description="Entidad auditada")] = None,
) -> list[RegistroAuditoriaRespuesta]:
    """Consulta la bitácora de auditoría del tenant del administrador."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    registros = repo.listar(
        tenant_id=usuario.tenant_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
    )
    return [RegistroAuditoriaRespuesta.desde_dominio(r) for r in registros]
