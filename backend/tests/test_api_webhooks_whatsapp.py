"""Tests para el endpoint de webhook de WhatsApp (TDD tasks 3.1, 3.2, 3.3)."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.seguridad import crear_token_acceso
from src.infrastructure.database import abrir_conexion


@pytest.fixture
def client_app(tmp_path: Path):
    """Crea una app con base de datos sembrada para pruebas del webhook."""
    ruta_db = tmp_path / "test_webhook.db"
    app = create_app(ruta_db=ruta_db, sembrar=True)
    with TestClient(app) as client:
        yield client, ruta_db


def _crear_turno_test(client: TestClient) -> int:
    """Helper que crea un turno a través de la API autenticada y retorna su id."""
    token = crear_token_acceso(
        claims={
            "sub": "2",
            "email": "recepcion@ejemplo.com",
            "rol": "Recepcionista",
            "tenant_id": 1,
        }
    )
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "paciente": "Paciente Ficticio Uno",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-20",
        "hora_inicio": "10:00",
        "hora_fin": "11:00",
        "telefono": "+54 11 4000-0001",
    }
    resp = client.post("/api/v1/turnos", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_webhook_rechaza_peticion_sin_secreto(client_app) -> None:
    """Task 3.1: Rechazo con HTTP 401 si no se envía la cabecera X-Webhook-Secret."""
    client, _ = client_app
    turno_id = _crear_turno_test(client)
    payload = {
        "accion": "CONFIRMAR",
        "turno_id": turno_id,
    }
    resp = client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert resp.status_code == 401
    assert "secreto" in resp.text.lower() or "firma" in resp.text.lower() or "unauthorized" in resp.text.lower()


def test_webhook_rechaza_peticion_con_secreto_invalido(client_app) -> None:
    """Task 3.1: Rechazo con HTTP 401 ante secreto erróneo."""
    client, _ = client_app
    turno_id = _crear_turno_test(client)
    payload = {
        "accion": "CONFIRMAR",
        "turno_id": turno_id,
    }
    headers = {"X-Webhook-Secret": "clave-falsa-invalida"}
    resp = client.post("/api/v1/webhooks/whatsapp", json=payload, headers=headers)
    assert resp.status_code == 401


def test_webhook_confirma_asistencia_y_registra_auditoria(client_app) -> None:
    """Task 3.2: Confirmación exitosa de turno y persistencia de evento en auditoría."""
    client, ruta_db = client_app
    turno_id = _crear_turno_test(client)
    headers = {"X-Webhook-Secret": "secreto-webhook-default"}

    payload = {
        "accion": "CONFIRMAR",
        "turno_id": turno_id,
    }
    resp = client.post("/api/v1/webhooks/whatsapp", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["turno_id"] == turno_id
    assert data["accion_procesada"] == "CONFIRMAR"

    # Verificamos registro en auditoría
    con = abrir_conexion(ruta_db)
    fila_auditoria = con.execute(
        "SELECT accion, entidad, detalle FROM auditoria WHERE entidad_id = ? AND accion = 'WHATSAPP_CONFIRMACION'",
        (turno_id,),
    ).fetchone()
    con.close()
    assert fila_auditoria is not None
    assert fila_auditoria[0] == "WHATSAPP_CONFIRMACION"


def test_webhook_cancela_turno_liberando_recursos_rn04(client_app) -> None:
    """Task 3.3: Cancelación remota vía WhatsApp cambia el estado a CANCELADO y libera el horario."""
    client, ruta_db = client_app
    turno_id = _crear_turno_test(client)
    headers = {"X-Webhook-Secret": "secreto-webhook-default"}

    payload = {
        "accion": "CANCELAR",
        "turno_id": turno_id,
    }
    resp = client.post("/api/v1/webhooks/whatsapp", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["turno_id"] == turno_id
    assert data["accion_procesada"] == "CANCELAR"
    assert data["estado_actual"] == "CANCELADO"

    # Verificamos en DB que el turno está CANCELADO
    con = abrir_conexion(ruta_db)
    fila = con.execute("SELECT estado FROM turno WHERE id = ?", (turno_id,)).fetchone()
    fila_auditoria = con.execute(
        "SELECT accion FROM auditoria WHERE entidad_id = ? AND accion = 'WHATSAPP_CANCELACION'",
        (turno_id,),
    ).fetchone()
    con.close()

    assert fila[0] == "CANCELADO"
    assert fila_auditoria is not None


def test_webhook_turno_no_encontrado(client_app) -> None:
    """Task 3.1: Retorna 404 si el turno_id no existe."""
    client, _ = client_app
    headers = {"X-Webhook-Secret": "secreto-webhook-default"}
    payload = {
        "accion": "CONFIRMAR",
        "turno_id": 999999,
    }
    resp = client.post("/api/v1/webhooks/whatsapp", json=payload, headers=headers)
    assert resp.status_code == 404


def test_webhook_cancelacion_libera_recursos_para_nueva_reserva_rn04(client_app) -> None:
    """Triangulación: tras cancelar por webhook, el mismo horario puede ser reservado por otro turno."""
    client, _ = client_app
    turno_id = _crear_turno_test(client)
    headers_webhook = {"X-Webhook-Secret": "secreto-webhook-default"}

    # Cancelamos el turno vía webhook
    resp_canc = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"accion": "CANCELAR", "turno_id": turno_id},
        headers=headers_webhook,
    )
    assert resp_canc.status_code == 200

    # Intentamos crear un nuevo turno en exactamente el mismo horario y recursos
    token = crear_token_acceso(
        claims={
            "sub": "2",
            "email": "recepcion@ejemplo.com",
            "rol": "Recepcionista",
            "tenant_id": 1,
        }
    )
    headers_api = {"Authorization": f"Bearer {token}"}
    payload_nuevo = {
        "paciente": "Paciente Ficticio Dos",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-20",
        "hora_inicio": "10:00",
        "hora_fin": "11:00",
    }
    resp_nuevo = client.post("/api/v1/turnos", json=payload_nuevo, headers=headers_api)
    assert resp_nuevo.status_code == 201
    assert resp_nuevo.json()["id"] != turno_id


def test_webhook_intento_cancelar_turno_completado_rechazado(client_app) -> None:
    """Triangulación: un turno ya COMPLETADO no puede ser cancelado vía webhook."""
    client, ruta_db = client_app
    turno_id = _crear_turno_test(client)
    headers_webhook = {"X-Webhook-Secret": "secreto-webhook-default"}

    # Marcamos el turno como COMPLETADO en la base
    con = abrir_conexion(ruta_db)
    con.execute("UPDATE turno SET estado = 'COMPLETADO' WHERE id = ?", (turno_id,))
    con.commit()
    con.close()

    resp = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"accion": "CANCELAR", "turno_id": turno_id},
        headers=headers_webhook,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "completado" in data["mensaje"].lower()
    assert data["estado_actual"] == "COMPLETADO"

