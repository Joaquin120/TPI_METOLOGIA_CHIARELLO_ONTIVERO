"""Pruebas de la dependencia de contexto por petición (task 5.2, design D3/D4).

Se monta una ruta exclusiva de test sobre `create_app` para observar la
resolución del tenant y el wiring `ServicioTurnos → RepositorioTurnosSqlite`.
Regla dura 5: SQLite real en archivo temporal (`tmp_path`).
"""

import sqlite3
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencias import ContextoTurnos, contexto_turnos
from src.infrastructure.database import abrir_conexion
from src.infrastructure.seed import TENANT_DEFECTO


def _id_tenant_sembrado(ruta: Path) -> int:
    conexion = abrir_conexion(ruta)
    try:
        fila = conexion.execute(
            "SELECT id FROM tenant WHERE nombre = ?", (TENANT_DEFECTO,)
        ).fetchone()
        return fila[0]
    finally:
        conexion.close()


def _crear_segundo_tenant(ruta: Path, nombre: str = "Clínica Secundaria") -> int:
    """Crea un segundo tenant sintético por SQL directo (solo setup de prueba)."""
    conexion: sqlite3.Connection = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES (?)", (nombre,))
        conexion.commit()
        return conexion.execute(
            "SELECT id FROM tenant WHERE nombre = ?", (nombre,)
        ).fetchone()[0]
    finally:
        conexion.close()


def _app_con_ruta_de_contexto(
    ruta_db: Path, *, tenant_por_defecto: int | None = None
) -> FastAPI:
    app = create_app(ruta_db=ruta_db, tenant_por_defecto=tenant_por_defecto, sembrar=True)

    @app.get("/prueba/contexto")
    def _contexto(
        contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    ) -> dict[str, object]:
        return {
            "tenant_id": contexto.tenant_id,
            "turnos": len(contexto.servicio.turnos_registrados()),
        }

    return app


# ---------------------------------------------------------------------------
# Resolución de tenant (design D4)
# ---------------------------------------------------------------------------


def test_header_valido_resuelve_el_tenant(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_header.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_id = _id_tenant_sembrado(ruta)

    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"X-Tenant-ID": str(tenant_id)}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"tenant_id": tenant_id, "turnos": 0}


def test_sin_header_usa_el_tenant_por_defecto(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_default.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_id = _id_tenant_sembrado(ruta)

    aplicacion = _app_con_ruta_de_contexto(ruta, tenant_por_defecto=tenant_id)
    respuesta = TestClient(aplicacion).get("/prueba/contexto")

    assert respuesta.status_code == 200
    assert respuesta.json()["tenant_id"] == tenant_id


def test_sin_header_ni_default_devuelve_400(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_sin_tenant.db"
    app = _app_con_ruta_de_contexto(ruta)

    respuesta = TestClient(app).get("/prueba/contexto")

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "TENANT_NO_RESUELTO"
    assert respuesta.json()["error"]["message"]


def test_header_con_id_inexistente_devuelve_400(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_inexistente.db"
    app = _app_con_ruta_de_contexto(ruta)

    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"X-Tenant-ID": "9999"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "TENANT_NO_RESUELTO"
    assert "9999" in respuesta.json()["error"]["message"]


def test_header_no_numerico_devuelve_400(tmp_path: Path) -> None:
    """Un header que no es entero tampoco resuelve tenant (nunca opera a ciegas)."""
    ruta = tmp_path / "dependencias_header_invalido.db"
    app = _app_con_ruta_de_contexto(ruta)

    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"X-Tenant-ID": "clinica-a"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "TENANT_NO_RESUELTO"
    assert "clinica-a" in respuesta.json()["error"]["message"]


def test_header_gana_sobre_el_tenant_por_defecto(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_precedencia.db"
    _app_con_ruta_de_contexto(ruta)
    tenant_1 = _id_tenant_sembrado(ruta)
    tenant_2 = _crear_segundo_tenant(ruta)
    app = create_app(ruta_db=ruta, tenant_por_defecto=tenant_1, sembrar=True)

    @app.get("/prueba/contexto")
    def _contexto(
        contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    ) -> dict[str, int]:
        return {"tenant_id": contexto.tenant_id}

    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"X-Tenant-ID": str(tenant_2)}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["tenant_id"] == tenant_2


def test_triangula_dos_tenants_distintos(tmp_path: Path) -> None:
    """Triangulación: dos tenants válidos resuelven cada uno al suyo."""
    ruta = tmp_path / "dependencias_dos_tenants.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_1 = _id_tenant_sembrado(ruta)
    tenant_2 = _crear_segundo_tenant(ruta)
    cliente = TestClient(app)

    uno = cliente.get("/prueba/contexto", headers={"X-Tenant-ID": str(tenant_1)})
    dos = cliente.get("/prueba/contexto", headers={"X-Tenant-ID": str(tenant_2)})

    assert uno.json()["tenant_id"] == tenant_1
    assert dos.json()["tenant_id"] == tenant_2
    assert tenant_1 != tenant_2


def test_tenant_desde_entorno_se_usa_sin_parametro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La factoría lee `TURNO_TENANT_ID` cuando no recibe `tenant_por_defecto`."""
    ruta = tmp_path / "dependencias_env.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_id = _id_tenant_sembrado(ruta)
    monkeypatch.setenv("TURNO_TENANT_ID", str(tenant_id))

    aplicacion = create_app(ruta_db=ruta, sembrar=True)

    @aplicacion.get("/prueba/contexto")
    def _contexto(
        contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    ) -> dict[str, int]:
        return {"tenant_id": contexto.tenant_id}

    respuesta = TestClient(aplicacion).get("/prueba/contexto")

    assert respuesta.status_code == 200
    assert respuesta.json()["tenant_id"] == tenant_id
