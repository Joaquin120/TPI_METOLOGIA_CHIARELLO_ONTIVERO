"""Pruebas de `GET /api/v1/health` (task 6.1, spec `exponer-api-turnos`).

El health check no requiere tenant ni toca datos de negocio.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.infrastructure.database import abrir_conexion


def _contar_turnos(ruta: Path) -> int:
    conexion: sqlite3.Connection = abrir_conexion(ruta)
    try:
        return conexion.execute("SELECT COUNT(*) FROM turno").fetchone()[0]
    finally:
        conexion.close()


@pytest.fixture()
def app_y_ruta(tmp_path: Path):
    ruta = tmp_path / "health.db"
    return create_app(ruta_db=ruta, sembrar=True), ruta


def test_health_responde_200_sin_tenant(app_y_ruta) -> None:
    app, _ruta = app_y_ruta

    respuesta = TestClient(app).get("/api/v1/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_health_con_tenant_valido_sigue_siendo_200(app_y_ruta) -> None:
    """Triangulación: un header válido no altera la respuesta de salud."""
    app, ruta = app_y_ruta
    conexion = abrir_conexion(ruta)
    try:
        tenant_id = conexion.execute("SELECT id FROM tenant").fetchone()[0]
    finally:
        conexion.close()

    respuesta = TestClient(app).get(
        "/api/v1/health", headers={"X-Tenant-ID": str(tenant_id)}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_health_con_tenant_invalido_no_cae_ni_crea_turnos(app_y_ruta) -> None:
    """Health no consulta la base de negocio ni crea turnos."""
    app, ruta = app_y_ruta
    antes = _contar_turnos(ruta)

    respuesta = TestClient(app).get(
        "/api/v1/health", headers={"X-Tenant-ID": "9999"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
    assert _contar_turnos(ruta) == antes == 0
