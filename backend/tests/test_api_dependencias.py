"""Pruebas de la dependencia de contexto por petición autenticada (C-04, task 4.2).

Se monta una ruta de test sobre `create_app` para observar la resolución
del tenant desde el token JWT y el wiring `ServicioTurnos → RepositorioTurnosSqlite`.
Regla dura 5: SQLite real en archivo temporal (`tmp_path`).
"""

from datetime import timedelta
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.dependencias import ContextoTurnos, contexto_turnos
from src.api.seguridad import crear_token_acceso
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
    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES (?)", (nombre,))
        conexion.commit()
        return conexion.execute(
            "SELECT id FROM tenant WHERE nombre = ?", (nombre,)
        ).fetchone()[0]
    finally:
        conexion.close()


def _app_con_ruta_de_contexto(ruta_db: Path) -> FastAPI:
    app = create_app(ruta_db=ruta_db, sembrar=True)

    @app.get("/prueba/contexto")
    def _contexto(
        contexto: Annotated[ContextoTurnos, Depends(contexto_turnos)],
    ) -> dict[str, object]:
        return {
            "tenant_id": contexto.tenant_id,
            "turnos": len(contexto.servicio.turnos_registrados()),
        }

    return app


def _token(tenant_id: int, rol: str = "Recepcionista") -> str:
    return crear_token_acceso({
        "sub": "1",
        "email": f"test@{tenant_id}.com",
        "tenant_id": tenant_id,
        "rol": rol,
    })


# ---------------------------------------------------------------------------
# Resolución de tenant vía sesión autenticada (C-04)
# ---------------------------------------------------------------------------


def test_token_valido_resuelve_el_tenant_de_la_sesion(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_jwt.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_id = _id_tenant_sembrado(ruta)

    token = _token(tenant_id)
    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"tenant_id": tenant_id, "turnos": 0}


def test_sin_token_devuelve_401(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_sin_token.db"
    app = _app_con_ruta_de_contexto(ruta)

    respuesta = TestClient(app).get("/prueba/contexto")

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "NO_AUTENTICADO"


def test_token_expirado_devuelve_401(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_token_expirado.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_id = _id_tenant_sembrado(ruta)

    token = crear_token_acceso(
        {"sub": "1", "email": "a@a.com", "tenant_id": tenant_id, "rol": "Recepcionista"},
        duracion=timedelta(seconds=-10),
    )
    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "TOKEN_EXPIRADO"


def test_token_con_tenant_inexistente_devuelve_400(tmp_path: Path) -> None:
    ruta = tmp_path / "dependencias_tenant_inexistente.db"
    app = _app_con_ruta_de_contexto(ruta)

    token = _token(99999)
    respuesta = TestClient(app).get(
        "/prueba/contexto", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "TENANT_NO_RESUELTO"
    assert "99999" in respuesta.json()["error"]["message"]


def test_triangula_dos_tenants_distintos_por_token(tmp_path: Path) -> None:
    """Triangulación: dos tokens de tenants válidos resuelven cada uno al suyo."""
    ruta = tmp_path / "dependencias_dos_tenants.db"
    app = _app_con_ruta_de_contexto(ruta)
    tenant_1 = _id_tenant_sembrado(ruta)
    tenant_2 = _crear_segundo_tenant(ruta)
    cliente = TestClient(app)

    token_1 = _token(tenant_1)
    token_2 = _token(tenant_2)

    uno = cliente.get("/prueba/contexto", headers={"Authorization": f"Bearer {token_1}"})
    dos = cliente.get("/prueba/contexto", headers={"Authorization": f"Bearer {token_2}"})

    assert uno.json()["tenant_id"] == tenant_1
    assert dos.json()["tenant_id"] == tenant_2
    assert tenant_1 != tenant_2
