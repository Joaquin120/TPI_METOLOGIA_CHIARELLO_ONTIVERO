"""Router de turnos: alta, listado y reprogramación del tenant resuelto (design D5).

La API solo traduce HTTP ↔ dominio: la doble validación de profesional y sillón
y el estado inicial del alta viven en `ServicioTurnos` (`src.domain`). Aquí no se
importa `buscar_activos_solapables`, `ESTADOS_ACTIVOS` ni reglas de transición.
"""

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
    obtener_usuario_actual,
    requerir_rol,
)
from src.api.errores import ErrorAccesoDenegado, ErrorTurnoNoEncontrado
from src.api.esquemas import (
    PATRON_FECHA,
    ReprogramarTurnoPeticion,
    TurnoCambioEstado,
    TurnoCrear,
    TurnoRespuesta,
)
from src.domain.models import Profesional, RegistroAuditoria, Sillon
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite

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


@router.patch("/turnos/{id}/reprogramar", response_model=TurnoRespuesta)
def reprogramar_turno(
    id: int,
    datos: ReprogramarTurnoPeticion,
    contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    recursos: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
    usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
) -> TurnoRespuesta:
    """Reprograma un turno in-place validando doble candado y registrando auditoría."""
    turno_previo = contexto.servicio.obtener_por_id(id)
    if turno_previo is None:
        raise ErrorTurnoNoEncontrado(f"El turno {id} no existe en este tenant")

    nuevo_profesional = None
    if datos.profesional_id is not None:
        nuevo_profesional = recursos.profesionales.obtener_por_id(datos.profesional_id)
        if nuevo_profesional is None:
            raise ErrorTurnoNoEncontrado(
                f"El profesional {datos.profesional_id} no existe en este centro"
            )

    nuevo_sillon = None
    if datos.sillon_id is not None:
        nuevo_sillon = recursos.sillones.obtener_por_id(datos.sillon_id)
        if nuevo_sillon is None:
            raise ErrorTurnoNoEncontrado(
                f"El sillón {datos.sillon_id} no existe en este centro"
            )

    turno_actualizado = contexto.servicio.reprogramar(
        turno_id=id,
        nueva_fecha=datos.fecha,
        nueva_hora_inicio=datos.hora_inicio,
        nueva_hora_fin=datos.hora_fin,
        nuevo_profesional=nuevo_profesional,
        nuevo_sillon=nuevo_sillon,
    )

    detalle = json.dumps(
        {
            "anterior": {
                "fecha": turno_previo.fecha,
                "hora_inicio": turno_previo.hora_inicio,
                "hora_fin": turno_previo.hora_fin,
                "profesional": turno_previo.profesional.nombre,
                "sillon": turno_previo.sillon.nombre,
            },
            "nuevo": {
                "fecha": turno_actualizado.fecha,
                "hora_inicio": turno_actualizado.hora_inicio,
                "hora_fin": turno_actualizado.hora_fin,
                "profesional": turno_actualizado.profesional.nombre,
                "sillon": turno_actualizado.sillon.nombre,
                "motivo": datos.motivo,
            },
        },
        ensure_ascii=False,
    )

    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="REPROGRAMAR_TURNO",
            entidad="turno",
            entidad_id=turno_actualizado.id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return TurnoRespuesta.desde_dominio(turno_actualizado)
