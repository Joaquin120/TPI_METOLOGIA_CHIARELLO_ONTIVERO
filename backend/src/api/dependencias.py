"""Contexto de petición: conexión, tenant y servicio (design D3/D4).

Cada petición de negocio abre su propia conexión SQLite (`yield` + `finally:
close()`), resuelve el tenant y compone el servicio con el adaptador SQLite.
`_resolver_tenant` es el único seam que `C-04` reemplazará por el tenant de la
sesión/JWT.
"""

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Header, Request

from src.api.errores import ErrorTenantNoResuelto
from src.domain.services import ServicioTurnos
from src.infrastructure.database import abrir_conexion
from src.repositories.turnos_sqlite import RepositorioTurnosSqlite


@dataclass(frozen=True)
class ContextoTurnos:
    """Servicio de dominio ya cableado al tenant resuelto de la petición."""

    servicio: ServicioTurnos
    tenant_id: int


def _resolver_tenant(
    conexion: sqlite3.Connection,
    x_tenant_id: str | None,
    tenant_por_defecto: int | None,
) -> int:
    """Aplica la precedencia header → default y valida el tenant contra la tabla.

    La validación contra `tenant` evita operar con un tenant fantasma (regla
    dura 8). Cualquier fallo se traduce a `ErrorTenantNoResuelto` (400).
    """
    if x_tenant_id is not None:
        try:
            tenant_id = int(x_tenant_id)
        except ValueError as exc:
            raise ErrorTenantNoResuelto(
                f"El tenant '{x_tenant_id}' no es un identificador válido"
            ) from exc
    elif tenant_por_defecto is not None:
        tenant_id = tenant_por_defecto
    else:
        raise ErrorTenantNoResuelto("No se pudo resolver el tenant de la petición")

    fila = conexion.execute(
        "SELECT 1 FROM tenant WHERE id = ?", (tenant_id,)
    ).fetchone()
    if fila is None:
        raise ErrorTenantNoResuelto(f"El tenant {tenant_id} no existe")
    return tenant_id


def contexto_turnos(
    request: Request,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> Iterator[ContextoTurnos]:
    """Dependencia de FastAPI: conexión por petición, tenant y servicio."""
    conexion = abrir_conexion(request.app.state.ruta_db)
    try:
        tenant_id = _resolver_tenant(
            conexion, x_tenant_id, request.app.state.tenant_por_defecto
        )
        servicio = ServicioTurnos(
            RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
        )
        yield ContextoTurnos(servicio=servicio, tenant_id=tenant_id)
    finally:
        conexion.close()
