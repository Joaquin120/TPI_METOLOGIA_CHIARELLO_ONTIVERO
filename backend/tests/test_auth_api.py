"""Tests de integración para la API de autenticación (C-04, task 3.3)."""

from datetime import timedelta
from fastapi.testclient import TestClient
import pytest

from src.api.app import create_app
from src.api.seguridad import crear_token_acceso, hashear_password
from src.infrastructure.database import abrir_conexion


@pytest.fixture
def cliente(tmp_path) -> TestClient:
    """Instancia TestClient contra SQLite real sembrada con datos iniciales."""
    ruta_db = tmp_path / "test_auth_api.db"
    app = create_app(ruta_db=ruta_db, sembrar=True)
    with TestClient(app) as test_client:
        yield test_client


def test_login_exitoso_devuelve_token_y_metadata(cliente: TestClient) -> None:
    resp = cliente.post(
        "/api/v1/auth/login",
        json={"email": "recepcion@ejemplo.com", "password": "secreto123"},
    )
    assert resp.status_code == 200
    datos = resp.json()
    assert "access_token" in datos
    assert datos["token_type"] == "bearer"
    assert datos["expires_in"] > 0


def test_login_con_password_incorrecta_devuelve_401(cliente: TestClient) -> None:
    resp = cliente.post(
        "/api/v1/auth/login",
        json={"email": "recepcion@ejemplo.com", "password": "password_incorrecta"},
    )
    assert resp.status_code == 401
    assert resp.json() == {
        "error": {
            "code": "CREDENCIALES_INVALIDAS",
            "message": "Credenciales inválidas",
        }
    }


def test_login_usuario_inexistente_devuelve_401(cliente: TestClient) -> None:
    resp = cliente.post(
        "/api/v1/auth/login",
        json={"email": "nadie@ejemplo.com", "password": "secreto123"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "CREDENCIALES_INVALIDAS"


def test_login_usuario_inactivo_devuelve_401(cliente: TestClient) -> None:
    # Desactivar usuario recepcion
    ruta_db = cliente.app.state.ruta_db
    con = abrir_conexion(ruta_db)
    con.execute("UPDATE usuario SET activo = 0 WHERE email = 'recepcion@ejemplo.com'")
    con.commit()
    con.close()

    resp = cliente.post(
        "/api/v1/auth/login",
        json={"email": "recepcion@ejemplo.com", "password": "secreto123"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "CREDENCIALES_INVALIDAS"


def test_obtener_perfil_me_autenticado(cliente: TestClient) -> None:
    login_resp = cliente.post(
        "/api/v1/auth/login",
        json={"email": "admin@ejemplo.com", "password": "secreto123"},
    )
    token = login_resp.json()["access_token"]

    resp = cliente.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    perfil = resp.json()
    assert perfil["email"] == "admin@ejemplo.com"
    assert perfil["rol"] == "Administrador"
    assert perfil["tenant_id"] == 1
    assert perfil["id"] is not None


def test_obtener_perfil_sin_token_devuelve_401(cliente: TestClient) -> None:
    resp = cliente.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NO_AUTENTICADO"


def test_obtener_perfil_token_expirado_devuelve_401(cliente: TestClient) -> None:
    claims = {"sub": "1", "email": "admin@ejemplo.com", "tenant_id": 1, "rol": "Administrador"}
    token_expirado = crear_token_acceso(claims, duracion=timedelta(seconds=-10))

    resp = cliente.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_expirado}"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_EXPIRADO"


def test_obtener_perfil_token_invalido_devuelve_401(cliente: TestClient) -> None:
    resp = cliente.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token.totalmente.falso"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "TOKEN_INVALIDO"

