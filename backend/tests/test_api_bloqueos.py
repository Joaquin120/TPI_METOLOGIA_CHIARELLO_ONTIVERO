"""Pruebas de integración para la API de bloqueos de sillones (C-10, F-12, RN-07, RP-07)."""

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
    rol: str = "Administrador",
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
    ruta = tmp_path / "api_bloqueos.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    cliente = TestClient(app)
    return cliente, tenant_id, ruta


# ---------------------------------------------------------------------------
# Scenarios: Registro de Bloqueo (Camino Feliz y Errores)
# ---------------------------------------------------------------------------


def test_api_crear_bloqueo_exitoso_201(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
            "motivo": "Mantenimiento preventivo anual de turbina",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    datos = resp.json()
    assert datos["id"] is not None
    assert datos["sillon_id"] == 1
    assert datos["fecha_hora_inicio"] == "2026-11-20 08:00"
    assert datos["fecha_hora_fin"] == "2026-11-20 12:00"
    assert datos["motivo"] == "Mantenimiento preventivo anual de turbina"


def test_api_bloqueos_contiguos_permitidos(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "08:00",
            "hora_fin": "10:00",
            "motivo": "Bloqueo A",
        },
        headers=headers,
    )

    resp2 = cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "10:00",
            "hora_fin": "12:00",
            "motivo": "Bloqueo B",
        },
        headers=headers,
    )
    assert resp2.status_code == 201


def test_api_crear_bloqueo_solapado_rechazado_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
            "motivo": "Primer Bloqueo",
        },
        headers=headers,
    )

    resp = cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "11:00",
            "hora_fin": "13:00",
            "motivo": "Superposición",
        },
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "BLOQUEO_SOLAPADO"


def test_api_crear_bloqueo_con_turno_activo_rechazado_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    # Crear turno activo en sillón 1
    resp_t = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Cita",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-20",
            "hora_inicio": "09:00",
            "hora_fin": "10:00",
        },
        headers=h_recep,
    )
    assert resp_t.status_code == 201

    # Intento de bloqueo en el intervalo del turno
    resp_b = cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
            "motivo": "Mantenimiento conflicto",
        },
        headers=h_admin,
    )
    assert resp_b.status_code == 409
    assert resp_b.json()["error"]["code"] == "CONFLICTO_TURNOS_EXISTENTES"


def test_api_crear_bloqueo_con_turno_cancelado_permitido(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    resp_t = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Cancelar",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-20",
            "hora_inicio": "09:00",
            "hora_fin": "10:00",
        },
        headers=h_recep,
    )
    t_id = resp_t.json()["id"]

    # Cancelar turno
    cliente.patch(f"/api/v1/turnos/{t_id}/estado", json={"accion": "cancelar"}, headers=h_recep)

    # Ahora crear bloqueo debe ser exitoso
    resp_b = cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
            "motivo": "Mantenimiento libre",
        },
        headers=h_admin,
    )
    assert resp_b.status_code == 201


# ---------------------------------------------------------------------------
# Scenarios: Impacto en Turnos (agendar y reprogramar)
# ---------------------------------------------------------------------------


def test_api_alta_turno_en_sillon_bloqueado_rechazada_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
            "motivo": "Bloqueo Sillón 1",
        },
        headers=h_admin,
    )

    # Intentar agendar en Sillón 1 durante el bloqueo
    resp = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente X",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-20",
            "hora_inicio": "09:00",
            "hora_fin": "09:30",
        },
        headers=h_recep,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SILLON_BLOQUEADO"

    # Turno en horario contiguo: permitido
    resp_ok = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Ok",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-20",
            "hora_inicio": "12:00",
            "hora_fin": "12:30",
        },
        headers=h_recep,
    )
    assert resp_ok.status_code == 201


def test_api_reprogramar_turno_en_sillon_bloqueado_rechazado_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    # Turno el día 19
    t = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Mover",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-19",
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
        },
        headers=h_recep,
    ).json()

    # Bloqueo en sillón 1 el día 20 de 14:00 a 18:00
    cliente.post(
        "/api/v1/bloqueos",
        json={
            "sillon_id": 1,
            "fecha": "2026-11-20",
            "hora_inicio": "14:00",
            "hora_fin": "18:00",
            "motivo": "Mantenimiento tarde",
        },
        headers=h_admin,
    )

    # Reprogramar hacia 15:00-16:00 del día 20: 409 SILLON_BLOQUEADO
    resp_rep = cliente.patch(
        f"/api/v1/turnos/{t['id']}/reprogramar",
        json={
            "fecha": "2026-11-20",
            "hora_inicio": "15:00",
            "hora_fin": "16:00",
        },
        headers=h_recep,
    )
    assert resp_rep.status_code == 409
    assert resp_rep.json()["error"]["code"] == "SILLON_BLOQUEADO"

    # Reprogramar contiguo 18:00-18:30: permitido
    resp_ok = cliente.patch(
        f"/api/v1/turnos/{t['id']}/reprogramar",
        json={
            "fecha": "2026-11-20",
            "hora_inicio": "18:00",
            "hora_fin": "18:30",
        },
        headers=h_recep,
    )
    assert resp_ok.status_code == 200


# ---------------------------------------------------------------------------
# Scenarios: Consulta, Filtrado y Aislamiento Multi-Tenant
# ---------------------------------------------------------------------------


def test_api_listar_bloqueos_con_filtros(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    cliente.post("/api/v1/bloqueos", json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "B1"}, headers=h_admin)
    cliente.post("/api/v1/bloqueos", json={"sillon_id": 2, "fecha": "2026-11-21", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "B2"}, headers=h_admin)

    # Recepcionista puede listar
    resp = cliente.get("/api/v1/bloqueos?sillon_id=1", headers=h_recep)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["sillon_id"] == 1


def test_api_bloqueos_aislamiento_multitenant(cliente_y_contexto):
    cliente, t1_id, ruta = cliente_y_contexto
    h_t1 = _headers(t1_id, rol="Administrador")

    conn = abrir_conexion(ruta)
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Dos')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Dos'").fetchone()[0]
    conn.execute("INSERT INTO sillon (tenant_id, nombre) VALUES (?, 'Sillón T2')", (t2_id,))
    s_t2 = conn.execute("SELECT id FROM sillon WHERE tenant_id = ? AND nombre = 'Sillón T2'", (t2_id,)).fetchone()[0]
    conn.commit()
    conn.close()

    h_t2 = _headers(t2_id, rol="Administrador")

    cliente.post("/api/v1/bloqueos", json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "T1"}, headers=h_t1)
    cliente.post("/api/v1/bloqueos", json={"sillon_id": s_t2, "fecha": "2026-11-20", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "T2"}, headers=h_t2)

    resp_t1 = cliente.get("/api/v1/bloqueos", headers=h_t1)
    assert len(resp_t1.json()) == 1
    assert resp_t1.json()[0]["motivo"] == "T1"

    resp_t2 = cliente.get("/api/v1/bloqueos", headers=h_t2)
    assert len(resp_t2.json()) == 1
    assert resp_t2.json()[0]["motivo"] == "T2"


# ---------------------------------------------------------------------------
# Scenarios: Eliminación de Bloqueo
# ---------------------------------------------------------------------------


def test_api_eliminar_bloqueo_exitoso_y_liberacion(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    b = cliente.post(
        "/api/v1/bloqueos",
        json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "A borrar"},
        headers=h_admin,
    ).json()

    # Eliminar bloqueo
    resp_del = cliente.delete(f"/api/v1/bloqueos/{b['id']}", headers=h_admin)
    assert resp_del.status_code == 200

    # Ahora el sillón 1 puede recibir turnos en ese horario
    resp_t = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Liberado",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-20",
            "hora_inicio": "09:00",
            "hora_fin": "09:30",
        },
        headers=h_recep,
    )
    assert resp_t.status_code == 201


def test_api_eliminar_bloqueo_inexistente_devuelve_404(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")

    resp = cliente.delete("/api/v1/bloqueos/9999", headers=h_admin)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "BLOQUEO_NO_ENCONTRADO"


# ---------------------------------------------------------------------------
# Scenarios: Seguridad, RBAC, Validación y Auditoría
# ---------------------------------------------------------------------------


def test_api_bloqueos_rbac_denegado_403(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto

    for rol in ("Recepcionista", "Profesional"):
        h = _headers(tenant_id, rol=rol)
        # POST
        resp_post = cliente.post(
            "/api/v1/bloqueos",
            json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "M"},
            headers=h,
        )
        assert resp_post.status_code == 403
        assert resp_post.json()["error"]["code"] == "ACCESO_DENEGADO"

        # DELETE
        resp_del = cliente.delete("/api/v1/bloqueos/1", headers=h)
        assert resp_del.status_code == 403
        assert resp_del.json()["error"]["code"] == "ACCESO_DENEGADO"

    # GET denegado solo para Profesional (Recepcionista puede listar)
    h_prof = _headers(tenant_id, rol="Profesional")
    resp_get = cliente.get("/api/v1/bloqueos", headers=h_prof)
    assert resp_get.status_code == 403


def test_api_bloqueos_sin_token_401(cliente_y_contexto):
    cliente, _, _ = cliente_y_contexto
    assert cliente.post("/api/v1/bloqueos", json={}).status_code == 401
    assert cliente.get("/api/v1/bloqueos").status_code == 401
    assert cliente.delete("/api/v1/bloqueos/1").status_code == 401


def test_api_bloqueos_validacion_422(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")

    # hora_inicio >= hora_fin
    resp1 = cliente.post(
        "/api/v1/bloqueos",
        json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "12:00", "hora_fin": "10:00", "motivo": "Invertido"},
        headers=h_admin,
    )
    assert resp1.status_code == 422
    assert resp1.json()["error"]["code"] == "VALIDACION"

    # motivo vacío
    resp2 = cliente.post(
        "/api/v1/bloqueos",
        json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "10:00", "hora_fin": "12:00", "motivo": "   "},
        headers=h_admin,
    )
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "VALIDACION"


def test_api_bloqueos_auditoria_inmutable(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")

    b = cliente.post(
        "/api/v1/bloqueos",
        json={"sillon_id": 1, "fecha": "2026-11-20", "hora_inicio": "08:00", "hora_fin": "12:00", "motivo": "Auditoria Test"},
        headers=h_admin,
    ).json()

    cliente.delete(f"/api/v1/bloqueos/{b['id']}", headers=h_admin)

    # Consultar bitácora de auditoría
    resp_aud = cliente.get("/api/v1/auditoria", headers=h_admin)
    assert resp_aud.status_code == 200
    acciones = [ev["accion"] for ev in resp_aud.json()]
    assert "CREAR_BLOQUEO_SILLON" in acciones
    assert "ELIMINAR_BLOQUEO_SILLON" in acciones
