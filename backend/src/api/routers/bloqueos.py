"""Router de bloqueos temporales de sillones por mantenimiento (C-10, F-12, RN-07, RP-07)."""

from datetime import datetime
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencias import (
    ContextoRecursos,
    ContextoTurnos,
    ContextoUsuario,
    contexto_recursos,
    contexto_turnos,
    obtener_repositorio_auditoria,
    requerir_rol,
)
from src.api.errores import ErrorSillonNoEncontrado
from src.api.esquemas import (
    PATRON_FECHA,
    BloqueoCrear,
    BloqueoRespuesta,
)
from src.domain.models import RegistroAuditoria
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite

router = APIRouter(prefix="/bloqueos", tags=["bloqueos"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BloqueoRespuesta)
def crear_bloqueo(
    datos: BloqueoCrear,
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    recursos: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
    usuario: Annotated[ContextoUsuario, Depends(requerir_rol("Administrador"))],
) -> BloqueoRespuesta:
    """Registra un nuevo bloqueo de sillón validando que no existan turnos activos ni bloqueos previos."""
    sillon = recursos.sillones.obtener_por_id(datos.sillon_id)
    if sillon is None:
        raise ErrorSillonNoEncontrado(f"El sillón {datos.sillon_id} no existe en este centro")

    bloqueo = contexto.servicio.crear_bloqueo(
        tenant_id=usuario.tenant_id,
        sillon_id=datos.sillon_id,
        fecha=datos.fecha,
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
        motivo=datos.motivo,
        creado_por=usuario.id,
    )

    detalle = json.dumps(
        {
            "sillon_id": bloqueo.sillon_id,
            "fecha_hora_inicio": bloqueo.fecha_hora_inicio,
            "fecha_hora_fin": bloqueo.fecha_hora_fin,
            "motivo": bloqueo.motivo,
        },
        ensure_ascii=False,
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="CREAR_BLOQUEO_SILLON",
            entidad="bloqueo_sillon",
            entidad_id=bloqueo.id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return BloqueoRespuesta.desde_dominio(bloqueo)


@router.get("", response_model=list[BloqueoRespuesta])
def listar_bloqueos(
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Administrador", "Recepcionista"))
    ],
    sillon_id: Annotated[int | None, Query(description="ID del sillón")] = None,
    fecha_desde: Annotated[
        str | None, Query(description="Fecha inicio YYYY-MM-DD", pattern=PATRON_FECHA)
    ] = None,
    fecha_hasta: Annotated[
        str | None, Query(description="Fecha fin YYYY-MM-DD", pattern=PATRON_FECHA)
    ] = None,
) -> list[BloqueoRespuesta]:
    """Consulta la lista de bloqueos del tenant con filtros opcionales."""
    bloqueos = contexto.servicio.listar_bloqueos(
        sillon_id=sillon_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return [BloqueoRespuesta.desde_dominio(b) for b in bloqueos]


@router.delete("/{id}", response_model=dict[str, str])
def eliminar_bloqueo(
    id: int,
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
    usuario: Annotated[ContextoUsuario, Depends(requerir_rol("Administrador"))],
) -> dict[str, str]:
    """Elimina o cancela anticipadamente un bloqueo de sillón."""
    contexto.servicio.eliminar_bloqueo(id)

    detalle = json.dumps(
        {
            "bloqueo_id": id,
        },
        ensure_ascii=False,
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="ELIMINAR_BLOQUEO_SILLON",
            entidad="bloqueo_sillon",
            entidad_id=id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return {"mensaje": f"Bloqueo {id} eliminado exitosamente"}
