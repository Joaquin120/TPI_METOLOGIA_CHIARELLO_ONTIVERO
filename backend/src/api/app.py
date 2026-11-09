"""Factoría de la app FastAPI y composition root (design D3).

No hay `app = create_app()` a nivel de módulo: uvicorn debe arrancar con

    uvicorn src.api.app:create_app --factory

Cada petición de negocio abre su propia conexión SQLite (ver
`src.api.dependencias`); la factoría solo hace el arranque (migrar/sembrar) y
guarda la configuración en `app.state`.
"""

import os

from fastapi import FastAPI

from src.api.errores import registrar_manejadores_de_errores
from src.api.routers import auth, health, metricas, pacientes, recursos, turnos
from src.infrastructure.config import ruta_base_de_datos
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import sembrar_datos_iniciales

PREFIJO_API = "/api/v1"


def _tenant_desde_entorno() -> int | None:
    """Lee `TURNO_TENANT_ID` (design D4, D-05: nunca hardcodeado)."""
    crudo = os.environ.get("TURNO_TENANT_ID")
    if not crudo:
        return None
    try:
        return int(crudo)
    except ValueError:
        return None


def create_app(
    *,
    ruta_db: str | os.PathLike[str] | None = None,
    tenant_por_defecto: int | None = None,
    sembrar: bool = False,
) -> FastAPI:
    """Ensambla la app: migración de arranque, seed opcional y configuración."""
    ruta_resuelta = ruta_db if ruta_db is not None else ruta_base_de_datos()
    tenant_resuelto = (
        tenant_por_defecto
        if tenant_por_defecto is not None
        else _tenant_desde_entorno()
    )

    conexion = abrir_conexion(ruta_resuelta)
    try:
        migrar(conexion)
        if sembrar:
            sembrar_datos_iniciales(conexion)
    finally:
        conexion.close()

    app = FastAPI(title="Turnos Odontología API", version="0.1.0")
    app.state.ruta_db = ruta_resuelta
    app.state.tenant_por_defecto = tenant_resuelto

    registrar_manejadores_de_errores(app)
    app.include_router(health.router, prefix=PREFIJO_API)
    app.include_router(auth.router, prefix=PREFIJO_API)
    app.include_router(turnos.router, prefix=PREFIJO_API)
    app.include_router(recursos.router, prefix=PREFIJO_API)
    app.include_router(pacientes.router, prefix=PREFIJO_API)
    app.include_router(metricas.router, prefix=PREFIJO_API)

    return app
