"""Pruebas de la factoría `create_app` (task 5.1, design D3).

Regla dura 5: SQLite real en archivo temporal (`tmp_path`), migrado y sembrado.
Regla dura 3: solo datos sintéticos.
"""

import importlib
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.exceptions import TransicionInvalidaError
from src.infrastructure.database import abrir_conexion


def _contar(conexion: sqlite3.Connection, tabla: str) -> int:
    return conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def _introspeccion(ruta: Path) -> dict[str, object]:
    conexion = abrir_conexion(ruta)
    try:
        return {
            "migraciones": [
                fila[0]
                for fila in conexion.execute("SELECT version FROM schema_migrations")
            ],
            "tenants": _contar(conexion, "tenant"),
            "profesionales": _contar(conexion, "profesional"),
            "sillones": _contar(conexion, "sillon"),
        }
    finally:
        conexion.close()


def test_create_app_devuelve_fastapi_y_migra_la_base(tmp_path: Path) -> None:
    """La factoría devuelve una app y deja la base migrada con el seed pedido."""
    ruta = tmp_path / "api_app.db"

    app = create_app(ruta_db=ruta, sembrar=True)

    assert isinstance(app, FastAPI)
    estado = _introspeccion(ruta)
    assert "001_init.sql" in estado["migraciones"]
    assert estado["tenants"] == 1
    assert estado["profesionales"] == 2
    assert estado["sillones"] == 2


def test_create_app_sin_sembrar_no_inserta_datos(tmp_path: Path) -> None:
    """Triangulación: `sembrar=False` migra el esquema pero no siembra datos."""
    ruta = tmp_path / "api_app_sin_seed.db"

    create_app(ruta_db=ruta, sembrar=False)

    estado = _introspeccion(ruta)
    assert "001_init.sql" in estado["migraciones"]
    assert estado["tenants"] == 0
    assert estado["profesionales"] == 0


def test_create_app_con_seed_es_idempotente(tmp_path: Path) -> None:
    """Triangulación: una segunda factoría sobre la misma base no duplica el seed."""
    ruta = tmp_path / "api_app_idempotente.db"

    create_app(ruta_db=ruta, sembrar=True)
    create_app(ruta_db=ruta, sembrar=True)

    estado = _introspeccion(ruta)
    assert estado["tenants"] == 1
    assert estado["profesionales"] == 2
    assert estado["sillones"] == 2


def test_create_app_guarda_configuracion_en_state(tmp_path: Path) -> None:
    """La configuración vive en `app.state`, no en estado global de módulo."""
    ruta = tmp_path / "api_app_state.db"

    app = create_app(ruta_db=ruta, tenant_por_defecto=7, sembrar=True)

    assert Path(app.state.ruta_db) == ruta
    assert app.state.tenant_por_defecto == 7


def test_create_app_ignora_tenant_de_entorno_no_numerico(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un `TURNO_TENANT_ID` inválido no configura un tenant fantasma."""
    monkeypatch.setenv("TURNO_TENANT_ID", "no-es-un-entero")

    app = create_app(ruta_db=tmp_path / "api_app_env_invalido.db")

    assert app.state.tenant_por_defecto is None


def test_modulo_app_no_expone_una_app_global() -> None:
    """No hay `app = create_app()` a nivel de módulo (uvicorn debe usar --factory)."""
    modulo = importlib.import_module("src.api.app")
    assert not hasattr(modulo, "app")


# ---------------------------------------------------------------------------
# Task 8.1 — `TransicionInvalidaError` mapeada a 409 mediante ruta de test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("estado", ["CANCELADO", "COMPLETADO"])
def test_transicion_invalida_se_mapea_a_409(tmp_path: Path, estado: str) -> None:
    """Triangulación: la transición inválida desde estados finales devuelve 409."""
    ruta = tmp_path / f"api_transicion_{estado}.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    mensaje = (
        f"No se puede aplicar 'completar' sobre un turno en estado '{estado}'"
    )

    @app.get(f"/prueba/transicion/{estado}")
    def _transicion() -> dict[str, str]:
        raise TransicionInvalidaError(mensaje)

    respuesta = TestClient(app).get(f"/prueba/transicion/{estado}")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "error": {"code": "TRANSICION_INVALIDA", "message": mensaje}
    }


def test_ruta_de_prueba_de_transicion_no_existe_en_produccion(tmp_path: Path) -> None:
    """La ruta que provoca la transición es exclusiva de test, no de producción."""
    app = create_app(ruta_db=tmp_path / "api_sin_ruta_de_prueba.db", sembrar=True)

    respuesta = TestClient(app).get("/prueba/transicion/CANCELADO")

    assert respuesta.status_code == 404
