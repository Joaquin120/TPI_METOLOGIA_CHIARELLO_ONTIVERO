"""Tests de integración para RBAC y aislamiento multi-tenant (C-04, task 4.3)."""

from datetime import timedelta
from fastapi.testclient import TestClient
import pytest

from src.api.app import create_app
from src.api.seguridad import crear_token_acceso
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import sembrar_datos_iniciales


@pytest.fixture
def app_dos_tenants(tmp_path):
    ruta_db = tmp_path / "rbac_tenancy.db"
    con = abrir_conexion(ruta_db)
    migrar(con)
    sembrar_datos_iniciales(con)

    # Crear segundo tenant y segundo usuario en tenant 2
    con.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Dental Sur')")
    con.execute("INSERT INTO profesional (tenant_id, nombre) VALUES (2, 'Dr. Sur')")
    con.execute("INSERT INTO sillon (tenant_id, nombre) VALUES (2, 'Sillón Sur')")
    con.execute(
        """
        INSERT INTO usuario (tenant_id, email, password_hash, rol, activo)
        VALUES (2, 'recepcion@sur.com', 'hash', 'Recepcionista', 1)
        """
    )
    con.commit()
    con.close()

    return create_app(ruta_db=ruta_db)


@pytest.fixture
def cliente(app_dos_tenants) -> TestClient:
    with TestClient(app_dos_tenants) as test_client:
        yield test_client


def test_recepcionista_y_administrador_pueden_crear_turnos(cliente: TestClient) -> None:
    token_recepcion = crear_token_acceso({
        "sub": "1",
        "email": "recepcion@ejemplo.com",
        "tenant_id": 1,
        "rol": "Recepcionista",
        "profesional_id": None,
    })

    payload = {
        "paciente": "Paciente Ficticio",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-10",
        "hora_inicio": "09:00",
        "hora_fin": "09:30",
    }

    resp = cliente.post(
        "/api/v1/turnos",
        json=payload,
        headers={"Authorization": f"Bearer {token_recepcion}"},
    )
    assert resp.status_code == 201
    assert resp.json()["estado"] == "CONFIRMADO"

    token_admin = crear_token_acceso({
        "sub": "2",
        "email": "admin@ejemplo.com",
        "tenant_id": 1,
        "rol": "Administrador",
        "profesional_id": None,
    })

    payload2 = {
        "paciente": "Paciente Ficticio 2",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-10",
        "hora_inicio": "10:00",
        "hora_fin": "10:30",
    }
    resp2 = cliente.post(
        "/api/v1/turnos",
        json=payload2,
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp2.status_code == 201


def test_profesional_no_puede_crear_turnos_devuelve_403(cliente: TestClient) -> None:
    token_prof = crear_token_acceso({
        "sub": "3",
        "email": "dr.ejemplo@ejemplo.com",
        "tenant_id": 1,
        "rol": "Profesional",
        "profesional_id": 1,
    })

    payload = {
        "paciente": "Paciente Ficticio",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-10",
        "hora_inicio": "11:00",
        "hora_fin": "11:30",
    }
    resp = cliente.post(
        "/api/v1/turnos",
        json=payload,
        headers={"Authorization": f"Bearer {token_prof}"},
    )
    assert resp.status_code == 403
    assert resp.json() == {
        "error": {
            "code": "ACCESO_DENEGADO",
            "message": "El rol 'Profesional' no tiene permisos para esta acción",
        }
    }


def test_aislamiento_entre_tenants_en_turnos(cliente: TestClient) -> None:
    token_t1 = crear_token_acceso({
        "sub": "1",
        "email": "recepcion@ejemplo.com",
        "tenant_id": 1,
        "rol": "Recepcionista",
        "profesional_id": None,
    })

    token_t2 = crear_token_acceso({
        "sub": "4",
        "email": "recepcion@sur.com",
        "tenant_id": 2,
        "rol": "Recepcionista",
        "profesional_id": None,
    })

    # Crear turno en Tenant 1
    resp = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Ficticio T1",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-10",
            "hora_inicio": "14:00",
            "hora_fin": "14:30",
        },
        headers={"Authorization": f"Bearer {token_t1}"},
    )
    assert resp.status_code == 201

    # Crear turno en Tenant 2
    resp_t2 = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Ficticio T2",
            "profesional": "Dr. Sur",
            "sillon": "Sillón Sur",
            "fecha": "2026-11-10",
            "hora_inicio": "14:00",
            "hora_fin": "14:30",
        },
        headers={"Authorization": f"Bearer {token_t2}"},
    )
    assert resp_t2.status_code == 201

    # Tenant 1 solo ve sus turnos
    listado_t1 = cliente.get(
        "/api/v1/turnos",
        headers={"Authorization": f"Bearer {token_t1}"},
    ).json()
    assert len(listado_t1) == 1
    assert listado_t1[0]["paciente"] == "Paciente Ficticio T1"

    # Tenant 2 solo ve sus turnos
    listado_t2 = cliente.get(
        "/api/v1/turnos",
        headers={"Authorization": f"Bearer {token_t2}"},
    ).json()
    assert len(listado_t2) == 1
    assert listado_t2[0]["paciente"] == "Paciente Ficticio T2"

    # Inyección de cabecera arbitraria no altera el tenant resuelto por JWT
    listado_hack = cliente.get(
        "/api/v1/turnos",
        headers={"Authorization": f"Bearer {token_t1}", "X-Tenant-ID": "2"},
    ).json()
    assert len(listado_hack) == 1
    assert listado_hack[0]["paciente"] == "Paciente Ficticio T1"


# ---------------------------------------------------------------------------
# C-05: Task 3.2 - Restricción de agenda para rol Profesional
# ---------------------------------------------------------------------------


def test_profesional_solo_ve_sus_propios_turnos_en_get_turnos(cliente: TestClient) -> None:
    """Task 3.2: el profesional solo visualiza los turnos donde profesional_id coincide con su identidad."""
    token_recepcion = crear_token_acceso({
        "sub": "1",
        "email": "recepcion@ejemplo.com",
        "tenant_id": 1,
        "rol": "Recepcionista",
        "profesional_id": None,
    })

    # Crear turno para Dr. Ejemplo (prof 1)
    cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente de Prof 1",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-15",
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
        },
        headers={"Authorization": f"Bearer {token_recepcion}"},
    )

    # Crear turno para Dra. Ejemplo (prof 2)
    cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente de Prof 2",
            "profesional": "Dra. Ejemplo",
            "sillon": "Sillón 2",
            "fecha": "2026-11-15",
            "hora_inicio": "11:00",
            "hora_fin": "11:30",
        },
        headers={"Authorization": f"Bearer {token_recepcion}"},
    )

    token_prof1 = crear_token_acceso({
        "sub": "3",
        "email": "prof1@ejemplo.com",
        "tenant_id": 1,
        "rol": "Profesional",
        "profesional_id": 1,
    })

    resp = cliente.get("/api/v1/turnos", headers={"Authorization": f"Bearer {token_prof1}"})
    assert resp.status_code == 200
    turnos = resp.json()
    assert len(turnos) == 1
    assert turnos[0]["profesional"] == "Dr. Ejemplo"
    assert turnos[0]["paciente"] == "Paciente de Prof 1"


def test_profesional_consultando_otro_profesional_devuelve_403(cliente: TestClient) -> None:
    """Task 3.2: intentar consultar la agenda de otro profesional responde 403 ACCESO_DENEGADO."""
    token_prof1 = crear_token_acceso({
        "sub": "3",
        "email": "prof1@ejemplo.com",
        "tenant_id": 1,
        "rol": "Profesional",
        "profesional_id": 1,
    })

    resp = cliente.get(
        "/api/v1/turnos?profesional_id=2",
        headers={"Authorization": f"Bearer {token_prof1}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCESO_DENEGADO"


def test_profesional_sin_recurso_asociado_devuelve_403(cliente: TestClient) -> None:
    """Task 3.2: un usuario con rol Profesional pero sin profesional_id devuelve 403 ACCESO_DENEGADO."""
    token_prof_huerfano = crear_token_acceso({
        "sub": "4",
        "email": "huerfano@ejemplo.com",
        "tenant_id": 1,
        "rol": "Profesional",
        "profesional_id": None,
    })

    resp = cliente.get(
        "/api/v1/turnos",
        headers={"Authorization": f"Bearer {token_prof_huerfano}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCESO_DENEGADO"


