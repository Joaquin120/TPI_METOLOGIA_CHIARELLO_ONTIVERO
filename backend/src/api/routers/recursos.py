"""Router de recursos clínicos: consulta y administración de profesionales y sillones (C-06, C-09b, F-04, F-05, F-10).

Permite listar, crear y actualizar los recursos disponibles dentro del tenant.
La administración (POST y PUT) está restringida exclusivamente a usuarios con rol Administrador.
"""

from datetime import datetime
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencias import (
    ContextoRecursos,
    ContextoUsuario,
    contexto_recursos,
    obtener_repositorio_auditoria,
    requerir_rol,
)
from src.api.errores import (
    ErrorNombreProfesionalDuplicado,
    ErrorNombreSillonDuplicado,
    ErrorProfesionalNoEncontrado,
    ErrorSillonNoEncontrado,
)
from src.api.esquemas import (
    ProfesionalActualizar,
    ProfesionalCrear,
    ProfesionalRespuesta,
    SillonActualizar,
    SillonCrear,
    SillonRespuesta,
)
from src.domain.exceptions import RecursoDuplicadoError
from src.domain.models import RegistroAuditoria
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite

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


@router.post(
    "/profesionales",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfesionalRespuesta,
)
def crear_profesional(
    datos: ProfesionalCrear,
    contexto: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    usuario: Annotated[ContextoUsuario, Depends(requerir_rol("Administrador"))],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
) -> ProfesionalRespuesta:
    """Registra un nuevo profesional en el tenant (exclusivo Administrador)."""
    try:
        creado = contexto.profesionales.crear(
            nombre=datos.nombre,
            matricula=datos.matricula,
            especialidad=datos.especialidad,
            activo=datos.activo,
        )
    except RecursoDuplicadoError as exc:
        raise ErrorNombreProfesionalDuplicado(str(exc)) from exc

    detalle = json.dumps(
        {
            "nombre": creado.nombre,
            "matricula": creado.matricula,
            "especialidad": creado.especialidad,
            "activo": creado.activo,
        },
        ensure_ascii=False,
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="CREAR_PROFESIONAL",
            entidad="profesional",
            entidad_id=creado.id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return ProfesionalRespuesta.desde_dominio(creado)


@router.put(
    "/profesionales/{id}",
    status_code=status.HTTP_200_OK,
    response_model=ProfesionalRespuesta,
)
def actualizar_profesional(
    id: int,
    datos: ProfesionalActualizar,
    contexto: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    usuario: Annotated[ContextoUsuario, Depends(requerir_rol("Administrador"))],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
) -> ProfesionalRespuesta:
    """Actualiza los datos de un profesional en el tenant (exclusivo Administrador)."""
    try:
        actualizado = contexto.profesionales.actualizar(
            id_=id,
            nombre=datos.nombre,
            matricula=datos.matricula,
            especialidad=datos.especialidad,
            activo=datos.activo,
        )
    except RecursoDuplicadoError as exc:
        raise ErrorNombreProfesionalDuplicado(str(exc)) from exc

    if actualizado is None:
        raise ErrorProfesionalNoEncontrado(f"El profesional {id} no existe en este centro")

    detalle = json.dumps(
        {
            "nombre": actualizado.nombre,
            "matricula": actualizado.matricula,
            "especialidad": actualizado.especialidad,
            "activo": actualizado.activo,
        },
        ensure_ascii=False,
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="MODIFICAR_PROFESIONAL",
            entidad="profesional",
            entidad_id=actualizado.id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return ProfesionalRespuesta.desde_dominio(actualizado)


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


@router.post(
    "/sillones",
    status_code=status.HTTP_201_CREATED,
    response_model=SillonRespuesta,
)
def crear_sillon(
    datos: SillonCrear,
    contexto: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    usuario: Annotated[ContextoUsuario, Depends(requerir_rol("Administrador"))],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
) -> SillonRespuesta:
    """Registra un nuevo sillón en el tenant (exclusivo Administrador)."""
    try:
        creado = contexto.sillones.crear(
            nombre=datos.nombre,
            equipamiento=datos.equipamiento,
            activo=datos.activo,
        )
    except RecursoDuplicadoError as exc:
        raise ErrorNombreSillonDuplicado(str(exc)) from exc

    detalle = json.dumps(
        {
            "nombre": creado.nombre,
            "equipamiento": creado.equipamiento,
            "activo": creado.activo,
        },
        ensure_ascii=False,
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="CREAR_SILLON",
            entidad="sillon",
            entidad_id=creado.id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return SillonRespuesta.desde_dominio(creado)


@router.put(
    "/sillones/{id}",
    status_code=status.HTTP_200_OK,
    response_model=SillonRespuesta,
)
def actualizar_sillon(
    id: int,
    datos: SillonActualizar,
    contexto: Annotated[ContextoRecursos, Depends(contexto_recursos)],
    usuario: Annotated[ContextoUsuario, Depends(requerir_rol("Administrador"))],
    repo_auditoria: Annotated[
        RepositorioAuditoriaSqlite, Depends(obtener_repositorio_auditoria)
    ],
) -> SillonRespuesta:
    """Actualiza los datos de un sillón en el tenant (exclusivo Administrador)."""
    try:
        actualizado = contexto.sillones.actualizar(
            id_=id,
            nombre=datos.nombre,
            equipamiento=datos.equipamiento,
            activo=datos.activo,
        )
    except RecursoDuplicadoError as exc:
        raise ErrorNombreSillonDuplicado(str(exc)) from exc

    if actualizado is None:
        raise ErrorSillonNoEncontrado(f"El sillón {id} no existe en este centro")

    detalle = json.dumps(
        {
            "nombre": actualizado.nombre,
            "equipamiento": actualizado.equipamiento,
            "activo": actualizado.activo,
        },
        ensure_ascii=False,
    )
    repo_auditoria.registrar(
        RegistroAuditoria(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            accion="MODIFICAR_SILLON",
            entidad="sillon",
            entidad_id=actualizado.id,
            detalle=detalle,
            fecha_hora=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    )

    return SillonRespuesta.desde_dominio(actualizado)
