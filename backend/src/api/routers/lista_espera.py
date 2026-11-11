"""Router REST para la gestión de Lista de Espera y asignación a turnos (C-15, F-08, PA-14)."""

from datetime import datetime
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencias import (
    ContextoListaEspera,
    ContextoRecursos,
    ContextoTurnos,
    ContextoUsuario,
    contexto_lista_espera,
    contexto_recursos,
    contexto_turnos,
    obtener_repositorio_auditoria,
    requerir_rol,
)
from src.api.errores import (
    ErrorEntradaListaEsperaNoEncontrada,
    ErrorProfesionalNoEncontrado,
    ErrorSillonNoEncontrado,
)
from src.api.esquemas import (
    PATRON_FECHA,
    AsignarTurnoListaEspera,
    EntradaListaEsperaCrear,
    EntradaListaEsperaRespuesta,
    TurnoRespuesta,
)
from src.domain.models import RegistroAuditoria
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite

router = APIRouter(prefix="/lista-espera", tags=["lista-espera"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EntradaListaEsperaRespuesta,
)
def registrar_en_lista_espera(
    datos: EntradaListaEsperaCrear,
    contexto: Annotated[ContextoListaEspera, Depends(contexto_lista_espera)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
) -> EntradaListaEsperaRespuesta:
    """Registra una solicitud de paciente en lista de espera."""
    entrada = contexto.servicio.registrar(
        paciente_nombre=datos.paciente_nombre,
        paciente_telefono=datos.paciente_telefono,
        fecha_deseada=datos.fecha_deseada,
        motivo=datos.motivo,
        profesional_nombre=datos.profesional_nombre,
        franja_horaria=datos.franja_horaria,
    )
    return EntradaListaEsperaRespuesta.desde_dominio(entrada)


@router.get(
    "/candidatos",
    response_model=list[EntradaListaEsperaRespuesta],
)
def consultar_candidatos(
    contexto: Annotated[ContextoListaEspera, Depends(contexto_lista_espera)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
    fecha: Annotated[str, Query(pattern=PATRON_FECHA, description="Fecha YYYY-MM-DD")],
    profesional_nombre: Annotated[str | None, Query(description="Nombre del profesional")] = None,
) -> list[EntradaListaEsperaRespuesta]:
    """Obtiene candidatos prioritarios en lista de espera en estricto orden FIFO (PA-14)."""
    candidatos = contexto.servicio.buscar_candidatos(
        fecha=fecha,
        profesional_nombre=profesional_nombre,
    )
    return [EntradaListaEsperaRespuesta.desde_dominio(c) for c in candidatos]


@router.get(
    "",
    response_model=list[EntradaListaEsperaRespuesta],
)
def listar_lista_espera(
    contexto: Annotated[ContextoListaEspera, Depends(contexto_lista_espera)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
    fecha: Annotated[str | None, Query(pattern=PATRON_FECHA, description="Fecha YYYY-MM-DD")] = None,
    profesional_nombre: Annotated[str | None, Query(description="Nombre del profesional")] = None,
    estado: Annotated[str | None, Query(description="Estado de la entrada")] = None,
) -> list[EntradaListaEsperaRespuesta]:
    """Lista las entradas registradas aplicando filtros opcionales."""
    entradas = contexto.servicio.listar(
        fecha=fecha,
        profesional_nombre=profesional_nombre,
        estado=estado,
    )
    return [EntradaListaEsperaRespuesta.desde_dominio(e) for e in entradas]


@router.patch(
    "/{entrada_id}/cancelar",
    response_model=EntradaListaEsperaRespuesta,
)
def cancelar_entrada(
    entrada_id: int,
    contexto: Annotated[ContextoListaEspera, Depends(contexto_lista_espera)],
    _usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
) -> EntradaListaEsperaRespuesta:
    """Cancela una entrada en lista de espera."""
    try:
        entrada = contexto.servicio.cancelar(entrada_id)
        return EntradaListaEsperaRespuesta.desde_dominio(entrada)
    except ValueError as exc:
        raise ErrorEntradaListaEsperaNoEncontrada(str(exc)) from exc


@router.post(
    "/{entrada_id}/asignar",
    status_code=status.HTTP_201_CREATED,
    response_model=TurnoRespuesta,
)
def asignar_turno_desde_lista_espera(
    entrada_id: int,
    datos: AsignarTurnoListaEspera,
    contexto_espera: Annotated[ContextoListaEspera, Depends(contexto_lista_espera)],
    contexto_turnos: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    recursos: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
    usuario: Annotated[
        ContextoUsuario, Depends(requerir_rol("Recepcionista", "Administrador"))
    ],
) -> TurnoRespuesta:
    """Convierte una entrada de lista de espera en turno confirmado y audita la operación (RN-01, RN-08, C-09)."""
    entrada = contexto_espera.servicio.obtener_por_id(entrada_id)
    if entrada is None:
        raise ErrorEntradaListaEsperaNoEncontrada(f"Entrada {entrada_id} no encontrada")

    profesional = recursos.profesionales.obtener_por_id(datos.profesional_id)
    if profesional is None:
        raise ErrorProfesionalNoEncontrado(f"El profesional {datos.profesional_id} no existe")

    sillon = recursos.sillones.obtener_por_id(datos.sillon_id)
    if sillon is None:
        raise ErrorSillonNoEncontrado(f"El sillón {datos.sillon_id} no existe")

    # 1. Agendar el turno validando todas las reglas físicas del sillón y profesional (RN-01, RN-08)
    turno = contexto_turnos.servicio.agendar_turno(
        paciente=entrada.paciente_nombre,
        fecha=datos.fecha,
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
        profesional=profesional,
        sillon=sillon,
        telefono_paciente=entrada.paciente_telefono,
    )

    # 2. Transicionar la entrada a ASIGNADO
    contexto_espera.servicio.marcar_asignado(entrada_id)

    # 3. Registrar auditoría formal (C-09)
    detalle = json.dumps(
        {
            "entrada_lista_espera_id": entrada_id,
            "turno_id": turno.id,
            "paciente": entrada.paciente_nombre,
            "profesional_id": profesional.id,
            "sillon_id": sillon.id,
            "fecha": datos.fecha,
            "hora_inicio": datos.hora_inicio,
            "hora_fin": datos.hora_fin,
        }
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="ASIGNAR_TURNO_LISTA_ESPERA",
            entidad="lista_espera",
            entidad_id=entrada_id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    )

    return TurnoRespuesta.desde_dominio(turno)
