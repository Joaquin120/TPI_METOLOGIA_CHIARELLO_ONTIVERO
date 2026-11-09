"""Router de métricas y reportes operativos (C-08, RN-05, RN-06)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencias import (
    ContextoUsuario,
    obtener_repositorio_metricas,
    requerir_roles,
)
from src.api.errores import ErrorRangoFechasInvalido
from src.api.esquemas import (
    PATRON_FECHA,
    MetricasRecursosRespuesta,
    MetricasTurnosRespuesta,
)
from src.repositories.metricas_sqlite import RepositorioMetricasSqlite

router = APIRouter(prefix="/metricas", tags=["metricas"])


def _validar_rango_fechas(fecha_desde: str | None, fecha_hasta: str | None) -> None:
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ErrorRangoFechasInvalido(
            f"La fecha_desde '{fecha_desde}' no puede ser posterior a fecha_hasta '{fecha_hasta}'"
        )


@router.get("/turnos", response_model=MetricasTurnosRespuesta)
def obtener_metricas_turnos(
    usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_roles("Administrador", "Recepcionista")),
    ],
    repo: Annotated[
        RepositorioMetricasSqlite,
        Depends(obtener_repositorio_metricas),
    ],
    fecha_desde: Annotated[
        str | None,
        Query(description="Fecha inicio YYYY-MM-DD", pattern=PATRON_FECHA),
    ] = None,
    fecha_hasta: Annotated[
        str | None,
        Query(description="Fecha fin YYYY-MM-DD", pattern=PATRON_FECHA),
    ] = None,
) -> MetricasTurnosRespuesta:
    """Devuelve métricas agregadas de turnos para el tenant autenticado."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    datos = repo.obtener_metricas_turnos(
        tenant_id=usuario.tenant_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return MetricasTurnosRespuesta(**datos)


@router.get("/recursos", response_model=MetricasRecursosRespuesta)
def obtener_metricas_recursos(
    usuario: Annotated[
        ContextoUsuario,
        Depends(requerir_roles("Administrador", "Recepcionista")),
    ],
    repo: Annotated[
        RepositorioMetricasSqlite,
        Depends(obtener_repositorio_metricas),
    ],
    fecha_desde: Annotated[
        str | None,
        Query(description="Fecha inicio YYYY-MM-DD", pattern=PATRON_FECHA),
    ] = None,
    fecha_hasta: Annotated[
        str | None,
        Query(description="Fecha fin YYYY-MM-DD", pattern=PATRON_FECHA),
    ] = None,
) -> MetricasRecursosRespuesta:
    """Devuelve distribución de turnos por profesional y sillón para el tenant autenticado."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    datos = repo.obtener_metricas_recursos(
        tenant_id=usuario.tenant_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return MetricasRecursosRespuesta(**datos)
