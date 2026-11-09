"""Contexto de petición: conexión, tenant y servicio (design D3/D4).

Cada petición de negocio abre su propia conexión SQLite (`yield` + `finally:
close()`), resuelve el tenant y compone el servicio con el adaptador SQLite.
`_resolver_tenant` es el único seam que `C-04` reemplazará por el tenant de la
sesión/JWT.
"""

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, Header, Request

from src.api.errores import (
    ErrorAccesoDenegado,
    ErrorNoAutenticado,
    ErrorTenantNoResuelto,
    ErrorTokenExpirado,
    ErrorTokenInvalido,
)
from src.api.seguridad import (
    TokenExpiradoError,
    TokenInvalidoError,
    decodificar_token_acceso,
)
from src.domain.services import ServicioTurnos
from src.infrastructure.database import abrir_conexion
from src.repositories.recursos import (
    RepositorioProfesionales,
    RepositorioSillones,
)
from src.repositories.turnos_sqlite import RepositorioTurnosSqlite


@dataclass(frozen=True)
class ContextoUsuario:
    """Usuario autenticado resuelto a partir del token JWT (C-04)."""

    id: int
    email: str
    tenant_id: int
    rol: str
    profesional_id: int | None = None


def obtener_usuario_actual(request: Request) -> ContextoUsuario:
    """Extrae y valida el token Bearer del header Authorization."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise ErrorNoAutenticado("Cabecera Authorization Bearer ausente")

    token = auth_header[7:].strip()
    try:
        payload = decodificar_token_acceso(token)
    except TokenExpiradoError as exc:
        raise ErrorTokenExpirado("El token ha expirado") from exc
    except TokenInvalidoError as exc:
        raise ErrorTokenInvalido("Token inválido") from exc

    try:
        usuario_id = int(payload["sub"])
        tenant_id = int(payload["tenant_id"])
        email = str(payload["email"])
        rol = str(payload["rol"])
        profesional_id = payload.get("profesional_id")
        if profesional_id is not None:
            profesional_id = int(profesional_id)
    except (KeyError, ValueError, TypeError) as exc:
        raise ErrorTokenInvalido("Claims del token incompletos o corruptos") from exc

    return ContextoUsuario(
        id=usuario_id,
        email=email,
        tenant_id=tenant_id,
        rol=rol,
        profesional_id=profesional_id,
    )


def requerir_rol(*roles_permitidos: str):
    """Fábrica de dependencias que valida si el usuario posee alguno de los roles."""

    def _verificar_rol(
        usuario: ContextoUsuario = Depends(obtener_usuario_actual),
    ) -> ContextoUsuario:
        if usuario.rol not in roles_permitidos:
            raise ErrorAccesoDenegado(
                f"El rol '{usuario.rol}' no tiene permisos para esta acción"
            )
        return usuario

    return _verificar_rol


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
    usuario: ContextoUsuario = Depends(obtener_usuario_actual),
) -> Iterator[ContextoTurnos]:
    """Dependencia de FastAPI: conexión por petición, tenant desde el usuario autenticado y servicio."""
    conexion = abrir_conexion(request.app.state.ruta_db)
    try:
        tenant_id = usuario.tenant_id
        fila = conexion.execute(
            "SELECT 1 FROM tenant WHERE id = ?", (tenant_id,)
        ).fetchone()
        if fila is None:
            raise ErrorTenantNoResuelto(f"El tenant {tenant_id} no existe")
        servicio = ServicioTurnos(
            RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
        )
        yield ContextoTurnos(servicio=servicio, tenant_id=tenant_id)
    finally:
        conexion.close()


@dataclass(frozen=True)
class ContextoRecursos:
    """Repositorios de recursos ya cableados al tenant resuelto de la petición (C-06)."""

    profesionales: RepositorioProfesionales
    sillones: RepositorioSillones
    tenant_id: int


def contexto_recursos(
    request: Request,
    usuario: ContextoUsuario = Depends(obtener_usuario_actual),
) -> Iterator[ContextoRecursos]:
    """Dependencia de FastAPI: conexión por petición y repositorios de recursos del tenant."""
    conexion = abrir_conexion(request.app.state.ruta_db)
    try:
        tenant_id = usuario.tenant_id
        fila = conexion.execute(
            "SELECT 1 FROM tenant WHERE id = ?", (tenant_id,)
        ).fetchone()
        if fila is None:
            raise ErrorTenantNoResuelto(f"El tenant {tenant_id} no existe")
        yield ContextoRecursos(
            profesionales=RepositorioProfesionales(conexion, tenant_id=tenant_id),
            sillones=RepositorioSillones(conexion, tenant_id=tenant_id),
            tenant_id=tenant_id,
        )
    finally:
        conexion.close()

