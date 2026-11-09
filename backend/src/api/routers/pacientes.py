"""Router de pacientes: alta y consulta en el tenant autenticado (C-07, RN-05, RN-06)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencias import (
    ContextoUsuario,
    get_repositorio_pacientes,
    requerir_rol,
)
from src.api.esquemas import (
    PacienteCrear,
    PacienteRespuesta,
)
from src.domain.models import Paciente
from src.repositories.pacientes_sqlite import RepositorioPacientesSqlite

router = APIRouter(tags=["pacientes"])


@router.post(
    "/pacientes",
    status_code=status.HTTP_201_CREATED,
    response_model=PacienteRespuesta,
)
def crear_paciente(
    datos: PacienteCrear,
    usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_rol("Administrador", "Recepcionista")),
    ],
    repo: Annotated[
        RepositorioPacientesSqlite,
        Depends(get_repositorio_pacientes),
    ],
) -> PacienteRespuesta:
    """Registra un nuevo paciente en el tenant del usuario autenticado."""
    paciente = Paciente(
        dni=datos.dni,
        nombre=datos.nombre,
        telefono=datos.telefono,
        tenant_id=usuario.tenant_id,
    )
    creado = repo.crear(paciente)
    return PacienteRespuesta.desde_dominio(creado)


@router.get("/pacientes", response_model=list[PacienteRespuesta])
def listar_pacientes(
    usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_rol("Administrador", "Recepcionista", "Profesional")),
    ],
    repo: Annotated[
        RepositorioPacientesSqlite,
        Depends(get_repositorio_pacientes),
    ],
    dni: Annotated[str | None, Query(description="Filtrar por DNI")] = None,
    nombre: Annotated[str | None, Query(description="Filtrar por nombre")] = None,
) -> list[PacienteRespuesta]:
    """Consulta los pacientes del tenant autenticado con filtros opcionales."""
    pacientes = repo.listar(
        tenant_id=usuario.tenant_id,
        filtro_nombre=nombre,
        filtro_dni=dni,
    )
    return [PacienteRespuesta.desde_dominio(p) for p in pacientes]
