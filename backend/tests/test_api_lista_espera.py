"""Pruebas de integración para la API de Lista de Espera (C-15, F-08, PA-14, RN-01, RN-08)."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.seguridad import crear_token_acceso
from src.infrastructure.database import abrir_conexion
from src.infrastructure.seed import TENANT_DEFECTO


def _id_tenant(ruta: Path, nombre: str = TENANT_DEFECTO) -> int:
    conexion = abrir_conexion(ruta)
    try:
        return conexion.execute(
            "SELECT id FROM tenant WHERE nombre = ?", (nombre,)
        ).fetchone()[0]
    finally:
        conexion.close()


def _headers(
    tenant_id: int,
    rol: str = "Recepcionista",
    usuario_id: int = 1,
) -> dict[str, str]:
    claims = {
        "sub": str(usuario_id),
        "email": f"usuario_{usuario_id}@{tenant_id}.com",
        "tenant_id": tenant_id,
        "rol": rol,
    }
    token = crear_token_acceso(claims)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cliente_y_contexto(tmp_path: Path):
    ruta = tmp_path / "api_lista_espera.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    cliente = TestClient(app)
    return cliente, tenant_id, ruta


def test_api_crear_entrada_lista_espera_201(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    resp = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Carlos Gardel",
            "paciente_telefono": "+5491112345678",
            "fecha_deseada": "2026-11-25",
            "motivo": "Urgencia conducto",
            "profesional_nombre": "Dra. Gomez",
            "franja_horaria": "MAÑANA",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    datos = resp.json()
    assert datos["id"] is not None
    assert datos["paciente_nombre"] == "Carlos Gardel"
    assert datos["estado"] == "PENDIENTE"


def test_api_crear_entrada_validacion_error_422(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    # Nombre vacío
    resp = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "",
            "paciente_telefono": "+5491112345678",
            "fecha_deseada": "2026-11-25",
            "motivo": "Control",
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_api_listar_con_filtros(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    r1 = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "P1",
            "paciente_telefono": "+5491111112222",
            "fecha_deseada": "2026-11-25",
            "motivo": "M1",
        },
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "P2",
            "paciente_telefono": "+5491122223333",
            "fecha_deseada": "2026-11-26",
            "motivo": "M2",
        },
        headers=headers,
    )
    assert r2.status_code == 201

    resp = cliente.get("/api/v1/lista-espera?fecha=2026-11-25", headers=headers)
    assert resp.status_code == 200
    entradas = resp.json()
    assert len(entradas) == 1
    assert entradas[0]["paciente_nombre"] == "P1"


def test_api_cancelar_entrada_lista_espera(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    creado = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "A Cancelar",
            "paciente_telefono": "+5491199990000",
            "fecha_deseada": "2026-11-25",
            "motivo": "Consulta",
        },
        headers=headers,
    ).json()

    entrada_id = creado["id"]
    resp = cliente.patch(f"/api/v1/lista-espera/{entrada_id}/cancelar", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["estado"] == "CANCELADO"


def test_api_consultar_candidatos_orden_fifo(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    c1 = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Primero",
            "paciente_telefono": "+5491111112222",
            "fecha_deseada": "2026-11-25",
            "motivo": "M1",
            "profesional_nombre": "Dr. Pérez",
        },
        headers=headers,
    ).json()
    c2 = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Segundo",
            "paciente_telefono": "+5491122223333",
            "fecha_deseada": "2026-11-25",
            "motivo": "M2",
            "profesional_nombre": "Dr. Pérez",
        },
        headers=headers,
    ).json()

    resp = cliente.get(
        "/api/v1/lista-espera/candidatos?fecha=2026-11-25&profesional_nombre=Dr.%20P%C3%A9rez",
        headers=headers,
    )
    assert resp.status_code == 200
    candidatos = resp.json()
    assert len(candidatos) == 2
    assert candidatos[0]["id"] == c1["id"]
    assert candidatos[1]["id"] == c2["id"]


def test_api_asignar_turno_desde_lista_espera_exitoso(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    # 1. Registrar paciente en espera
    entrada = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Paciente Reasignado",
            "paciente_telefono": "+5491188889999",
            "fecha_deseada": "2026-11-25",
            "motivo": "Dolor de muela",
        },
        headers=headers,
    ).json()

    # 2. Asignar turno
    resp = cliente.post(
        f"/api/v1/lista-espera/{entrada['id']}/asignar",
        json={
            "profesional_id": 1,
            "sillon_id": 1,
            "fecha": "2026-11-25",
            "hora_inicio": "14:00",
            "hora_fin": "15:00",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    datos_turno = resp.json()
    assert datos_turno["paciente"] == "Paciente Reasignado"

    # 3. Comprobar que la entrada en lista de espera pasó a estado ASIGNADO
    get_resp = cliente.get(f"/api/v1/lista-espera", headers=headers)
    entradas = [e for e in get_resp.json() if e["id"] == entrada["id"]]
    assert len(entradas) == 1
    assert entradas[0]["estado"] == "ASIGNADO"


def test_api_asignar_turno_conflicto_solapamiento_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    # Agendar un turno previo que ocupe el sillón 1
    r_pre = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Preexistente",
            "fecha": "2026-11-25",
            "hora_inicio": "14:00",
            "hora_fin": "15:00",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
        },
        headers=headers,
    )
    assert r_pre.status_code == 201

    # Entrada en lista de espera
    entrada = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Paciente Conflicto",
            "paciente_telefono": "+5491100001111",
            "fecha_deseada": "2026-11-25",
            "motivo": "Consulta",
        },
        headers=headers,
    ).json()

    # Intentar asignar al mismo horario y sillón debe dar 409 Conflict
    resp = cliente.post(
        f"/api/v1/lista-espera/{entrada['id']}/asignar",
        json={
            "profesional_id": 2,
            "sillon_id": 1,
            "fecha": "2026-11-25",
            "hora_inicio": "14:00",
            "hora_fin": "15:00",
        },
        headers=headers,
    )
    assert resp.status_code == 409


def test_api_rbac_odontologo_denegado_403(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers_odontologo = _headers(tenant_id, rol="Odontólogo")

    resp = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Prueba RBAC",
            "paciente_telefono": "+5491111112222",
            "fecha_deseada": "2026-11-25",
            "motivo": "Consulta",
        },
        headers=headers_odontologo,
    )
    assert resp.status_code == 403


def test_api_errores_404_recursos_inexistentes(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    # Cancelar entrada inexistente
    r_cancel = cliente.patch("/api/v1/lista-espera/9999/cancelar", headers=headers)
    assert r_cancel.status_code == 404

    # Asignar entrada inexistente
    r_asig = cliente.post(
        "/api/v1/lista-espera/9999/asignar",
        json={
            "profesional_id": 1,
            "sillon_id": 1,
            "fecha": "2026-11-25",
            "hora_inicio": "14:00",
            "hora_fin": "15:00",
        },
        headers=headers,
    )
    assert r_asig.status_code == 404

    # Entrada real pero profesional inexistente
    entrada = cliente.post(
        "/api/v1/lista-espera",
        json={
            "paciente_nombre": "Test 404",
            "paciente_telefono": "+5491111112222",
            "fecha_deseada": "2026-11-25",
            "motivo": "Consulta",
        },
        headers=headers,
    ).json()

    r_prof_inexistente = cliente.post(
        f"/api/v1/lista-espera/{entrada['id']}/asignar",
        json={
            "profesional_id": 9999,
            "sillon_id": 1,
            "fecha": "2026-11-25",
            "hora_inicio": "14:00",
            "hora_fin": "15:00",
        },
        headers=headers,
    )
    assert r_prof_inexistente.status_code == 404
