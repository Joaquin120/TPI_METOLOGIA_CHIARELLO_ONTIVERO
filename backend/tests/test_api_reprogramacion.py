"""Pruebas de integración del endpoint PATCH /api/v1/turnos/{id}/reprogramar (C-08b).

Cubre exhaustivamente todos los requisitos de specs/reprogramar-turno/spec.md:
- Reprogramación exitosa in-place (200) y liberación inmediata del horario anterior.
- Doble validación simultánea e independiente con precedencia RN-09 (409).
- Desplazamiento parcial en la misma franja horaria sin auto-solapamiento (200).
- Restricción por estado: rechazo de turnos CANCELADO y COMPLETADO (409 TRANSICION_INVALIDA).
- RBAC: permitido para Recepcionista y Administrador; denegado para Profesional (403).
- Autenticación: 401 NO_AUTENTICADO si falta token.
- Tenancy: 404 TURNO_NO_ENCONTRADO si el turno no existe o es de otro tenant.
- Validación: 422 VALIDACION si hora_inicio >= hora_fin o formato erróneo.
- Trazabilidad: Registro en la bitácora de auditoría con accion="REPROGRAMAR_TURNO".
"""

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
    profesional_id: int | None = None,
) -> dict[str, str]:
    claims = {
        "sub": str(usuario_id),
        "email": f"test_{usuario_id}@{tenant_id}.com",
        "tenant_id": tenant_id,
        "rol": rol,
    }
    if profesional_id is not None:
        claims["profesional_id"] = profesional_id
    token = crear_token_acceso(claims)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cliente_y_contexto(tmp_path: Path):
    ruta = tmp_path / "api_reprogramacion.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    cliente = TestClient(app)
    return cliente, tenant_id, ruta


def _crear_turno_fixture(cliente: TestClient, headers: dict[str, str], **kwargs) -> dict:
    payload = {
        "paciente": "Paciente Sintético",
        "profesional": "Dr. Ejemplo",
        "sillon": "Sillón 1",
        "fecha": "2026-11-01",
        "hora_inicio": "10:00",
        "hora_fin": "10:30",
    }
    payload.update(kwargs)
    resp = cliente.post("/api/v1/turnos", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Scenarios: Camino Feliz
# ---------------------------------------------------------------------------


def test_reprogramacion_exitosa_camino_feliz(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    turno = _crear_turno_fixture(cliente, headers)
    turno_id = turno["id"]

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/reprogramar",
        json={
            "fecha": "2026-11-01",
            "hora_inicio": "14:00",
            "hora_fin": "14:30",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["id"] == turno_id
    assert datos["fecha"] == "2026-11-01"
    assert datos["hora_inicio"] == "14:00"
    assert datos["hora_fin"] == "14:30"
    assert datos["estado"] == "CONFIRMADO"
    assert datos["profesional"] == "Dr. Ejemplo"
    assert datos["sillon"] == "Sillón 1"


def test_liberacion_inmediata_intervalo_previo(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    turno = _crear_turno_fixture(
        cliente, headers, fecha="2026-11-01", hora_inicio="10:00", hora_fin="10:30"
    )
    turno_id = turno["id"]

    # Reprogramar a las 14:00
    resp_reprog = cliente.patch(
        f"/api/v1/turnos/{turno_id}/reprogramar",
        json={"fecha": "2026-11-01", "hora_inicio": "14:00", "hora_fin": "14:30"},
        headers=headers,
    )
    assert resp_reprog.status_code == 200

    # Ahora crear otro turno en 10:00-10:30 debe ser 201 CREATED
    resp_nuevo = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Otro Paciente",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón 1",
            "fecha": "2026-11-01",
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
        },
        headers=headers,
    )
    assert resp_nuevo.status_code == 201


def test_reprogramacion_con_cambio_opcional_de_recursos(cliente_y_contexto):
    cliente, tenant_id, ruta = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    # Obtener IDs de profesional y sillón
    conn = abrir_conexion(ruta)
    p2_id = conn.execute(
        "INSERT INTO profesional (tenant_id, nombre) VALUES (?, 'Dra. Colega') RETURNING id",
        (tenant_id,),
    ).fetchone()[0]
    s2_id = conn.execute(
        "SELECT id FROM sillon WHERE tenant_id = ? AND nombre = 'Sillón 2'",
        (tenant_id,),
    ).fetchone()[0]
    conn.commit()
    conn.close()

    turno = _crear_turno_fixture(cliente, headers)
    turno_id = turno["id"]

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/reprogramar",
        json={
            "fecha": "2026-11-02",
            "hora_inicio": "11:00",
            "hora_fin": "11:30",
            "profesional_id": p2_id,
            "sillon_id": s2_id,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["profesional"] == "Dra. Colega"
    assert datos["sillon"] == "Sillón 2"
    assert datos["fecha"] == "2026-11-02"


# ---------------------------------------------------------------------------
# Scenarios: Conflictos de Recursos (409)
# ---------------------------------------------------------------------------


def test_conflicto_profesional_ocupado_devuelve_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    _crear_turno_fixture(
        cliente, headers, fecha="2026-11-01", hora_inicio="14:00", hora_fin="15:00"
    )
    turno_2 = _crear_turno_fixture(
        cliente, headers, fecha="2026-11-01", hora_inicio="09:00", hora_fin="10:00"
    )

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_2['id']}/reprogramar",
        json={"fecha": "2026-11-01", "hora_inicio": "14:30", "hora_fin": "15:30"},
        headers=headers,
    )
    assert resp.status_code == 409
    cuerpo = resp.json()
    assert cuerpo["error"]["code"] == "SOLAPAMIENTO_PROFESIONAL"


def test_conflicto_sillon_ocupado_devuelve_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    # Dra. Colega en Sillon 1 de 14:00 a 15:00
    _crear_turno_fixture(
        cliente,
        headers,
        profesional="Dra. Colega",
        sillon="Sillón 1",
        fecha="2026-11-01",
        hora_inicio="14:00",
        hora_fin="15:00",
    )

    # Dr. Ejemplo en Sillon 2 de 09:00 a 10:00
    turno_2 = _crear_turno_fixture(
        cliente,
        headers,
        profesional="Dr. Ejemplo",
        sillon="Sillón 2",
        fecha="2026-11-01",
        hora_inicio="09:00",
        hora_fin="10:00",
    )

    # Reprogramar turno_2 al Sillón 1 en 14:30-15:30
    resp = cliente.patch(
        f"/api/v1/turnos/{turno_2['id']}/reprogramar",
        json={
            "fecha": "2026-11-01",
            "hora_inicio": "14:30",
            "hora_fin": "15:30",
            # mantener Dr. Ejemplo pero pasar a Sillon 1
            "profesional_id": None,
        },
        headers=headers,
    )
    # Dr. Ejemplo no colisiona, pero Sillon 1 sí colisiona con Dra. Colega
    # Necesitamos pasar el sillon_id de Sillon 1
    # Consultamos ID de Sillon 1
    conn = abrir_conexion(cliente_y_contexto[2])
    sil1_id = conn.execute(
        "SELECT id FROM sillon WHERE nombre = 'Sillón 1' AND tenant_id = ?",
        (tenant_id,),
    ).fetchone()[0]
    conn.close()

    resp_con_sillon = cliente.patch(
        f"/api/v1/turnos/{turno_2['id']}/reprogramar",
        json={
            "fecha": "2026-11-01",
            "hora_inicio": "14:30",
            "hora_fin": "15:30",
            "sillon_id": sil1_id,
        },
        headers=headers,
    )
    assert resp_con_sillon.status_code == 409
    assert resp_con_sillon.json()["error"]["code"] == "SOLAPAMIENTO_SILLON"


def test_conflicto_simultaneo_aplica_precedencia_rn09(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    _crear_turno_fixture(
        cliente,
        headers,
        profesional="Dr. Ejemplo",
        sillon="Sillón 1",
        fecha="2026-11-01",
        hora_inicio="14:00",
        hora_fin="15:00",
    )
    turno_2 = _crear_turno_fixture(
        cliente,
        headers,
        profesional="Dr. Ejemplo",
        sillon="Sillón 1",
        fecha="2026-11-01",
        hora_inicio="09:00",
        hora_fin="10:00",
    )

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_2['id']}/reprogramar",
        json={"fecha": "2026-11-01", "hora_inicio": "14:15", "hora_fin": "14:45"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SOLAPAMIENTO_PROFESIONAL"


def test_turnos_contiguos_permitidos(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    _crear_turno_fixture(
        cliente, headers, fecha="2026-11-01", hora_inicio="10:00", hora_fin="10:30"
    )
    turno_2 = _crear_turno_fixture(
        cliente, headers, fecha="2026-11-01", hora_inicio="12:00", hora_fin="12:30"
    )

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_2['id']}/reprogramar",
        json={"fecha": "2026-11-01", "hora_inicio": "10:30", "hora_fin": "11:00"},
        headers=headers,
    )
    assert resp.status_code == 200


def test_desplazamiento_parcial_propio_turno_sin_auto_solapamiento(
    cliente_y_contexto,
):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    turno = _crear_turno_fixture(
        cliente, headers, fecha="2026-11-01", hora_inicio="10:00", hora_fin="11:00"
    )

    resp = cliente.patch(
        f"/api/v1/turnos/{turno['id']}/reprogramar",
        json={"fecha": "2026-11-01", "hora_inicio": "10:30", "hora_fin": "11:30"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["hora_inicio"] == "10:30"
    assert resp.json()["hora_fin"] == "11:30"


# ---------------------------------------------------------------------------
# Scenarios: Restricción por Estado Terminal (409 TRANSICION_INVALIDA)
# ---------------------------------------------------------------------------


def test_reprogramar_turno_cancelado_devuelve_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    turno = _crear_turno_fixture(cliente, headers)
    # Cancelar turno
    cliente.patch(
        f"/api/v1/turnos/{turno['id']}/estado",
        json={"accion": "cancelar"},
        headers=headers,
    )

    resp = cliente.patch(
        f"/api/v1/turnos/{turno['id']}/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TRANSICION_INVALIDA"


def test_reprogramar_turno_completado_devuelve_409(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    turno = _crear_turno_fixture(cliente, headers)
    # Completar turno
    cliente.patch(
        f"/api/v1/turnos/{turno['id']}/estado",
        json={"accion": "completar"},
        headers=headers,
    )

    resp = cliente.patch(
        f"/api/v1/turnos/{turno['id']}/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "TRANSICION_INVALIDA"


# ---------------------------------------------------------------------------
# Scenarios: Seguridad, RBAC y Tenancy
# ---------------------------------------------------------------------------


def test_reprogramar_rol_administrador_permitido(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_recep = _headers(tenant_id, rol="Recepcionista")
    h_admin = _headers(tenant_id, rol="Administrador")

    turno = _crear_turno_fixture(cliente, h_recep)

    resp = cliente.patch(
        f"/api/v1/turnos/{turno['id']}/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
        headers=h_admin,
    )
    assert resp.status_code == 200


def test_reprogramar_rol_profesional_denegado_403(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_recep = _headers(tenant_id, rol="Recepcionista")
    h_prof = _headers(tenant_id, rol="Profesional", profesional_id=1)

    turno = _crear_turno_fixture(cliente, h_recep)

    resp = cliente.patch(
        f"/api/v1/turnos/{turno['id']}/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
        headers=h_prof,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "ACCESO_DENEGADO"


def test_reprogramar_sin_token_devuelve_401(cliente_y_contexto):
    cliente, _, _ = cliente_y_contexto

    resp = cliente.patch(
        "/api/v1/turnos/1/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NO_AUTENTICADO"


def test_reprogramar_turno_inexistente_o_ajeno_devuelve_404(cliente_y_contexto):
    cliente, tenant_id, ruta = cliente_y_contexto
    headers_t1 = _headers(tenant_id, rol="Recepcionista")

    # Inexistente
    resp = cliente.patch(
        "/api/v1/turnos/9999/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
        headers=headers_t1,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TURNO_NO_ENCONTRADO"

    # Turno en Tenant 2
    conn = abrir_conexion(ruta)
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Ajena')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Ajena'").fetchone()[0]
    conn.commit()
    conn.close()

    headers_t2 = _headers(t2_id, rol="Recepcionista")
    turno_t2 = _crear_turno_fixture(cliente, headers_t2)

    # Tenant 1 intenta reprogramar el turno del Tenant 2
    resp_ajeno = cliente.patch(
        f"/api/v1/turnos/{turno_t2['id']}/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00", "hora_fin": "10:30"},
        headers=headers_t1,
    )
    assert resp_ajeno.status_code == 404
    assert resp_ajeno.json()["error"]["code"] == "TURNO_NO_ENCONTRADO"


# ---------------------------------------------------------------------------
# Scenarios: Validación Temporal y Envelope de Errores (422)
# ---------------------------------------------------------------------------


def test_reprogramar_hora_inicio_mayor_o_igual_a_fin_devuelve_422(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    resp = cliente.patch(
        "/api/v1/turnos/1/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "11:00", "hora_fin": "10:30"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDACION"


def test_reprogramar_formato_hora_invalido_devuelve_422(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Recepcionista")

    resp = cliente.patch(
        "/api/v1/turnos/1/reprogramar",
        json={"fecha": "2026-11-02", "hora_inicio": "10:00:00", "hora_fin": "11:00"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDACION"


# ---------------------------------------------------------------------------
# Scenario: Trazabilidad y Auditoría (C-09)
# ---------------------------------------------------------------------------


def test_reprogramar_registra_evento_de_auditoria(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers_recep = _headers(tenant_id, rol="Recepcionista", usuario_id=2)
    headers_admin = _headers(tenant_id, rol="Administrador", usuario_id=1)

    turno = _crear_turno_fixture(cliente, headers_recep)
    turno_id = turno["id"]

    resp = cliente.patch(
        f"/api/v1/turnos/{turno_id}/reprogramar",
        json={
            "fecha": "2026-11-03",
            "hora_inicio": "15:00",
            "hora_fin": "15:30",
            "motivo": "Cambio solicitado por el paciente",
        },
        headers=headers_recep,
    )
    assert resp.status_code == 200

    # Consultar auditoría como Administrador
    resp_aud = cliente.get("/api/v1/auditoria?accion=REPROGRAMAR_TURNO", headers=headers_admin)
    assert resp_aud.status_code == 200
    eventos = resp_aud.json()
    assert len(eventos) >= 1
    evento = eventos[0]
    assert evento["accion"] == "REPROGRAMAR_TURNO"
    assert evento["entidad"] == "turno"
    assert evento["entidad_id"] == turno_id
    assert evento["usuario_id"] == 2
    assert "anterior" in evento["detalle"]
    assert "nuevo" in evento["detalle"]
    assert "Cambio solicitado por el paciente" in evento["detalle"]
