"""Pruebas de integración para administración CRUD de recursos clínicos (C-09b, F-10).

Verifica todos los escenarios de specs/administrar-recursos/spec.md:
- Altas exitosas de profesional y sillón (201).
- Modificaciones exitosas de profesional y sillón (200).
- Disponibilidad inmediata de recursos creados para agendar turnos (POST /turnos) y reprogramar (PATCH /reprogramar).
- Rechazo por nombre duplicado en el mismo tenant (409 NOMBRE_PROFESIONAL_DUPLICADO / NOMBRE_SILLON_DUPLICADO).
- Rechazo por recurso inexistente o perteneciente a otro tenant (404).
- Control de acceso RBAC estricto: permitido para Administrador, denegado para Recepcionista y Profesional (403).
- Denegación ante peticiones anónimas (401).
- Validación de campos requeridos y texto no vacío (422).
- Bitácora inmutable de auditoría para cada operación exitosa.
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
    rol: str = "Administrador",
    usuario_id: int = 1,
) -> dict[str, str]:
    claims = {
        "sub": str(usuario_id),
        "email": f"test_{usuario_id}@{tenant_id}.com",
        "tenant_id": tenant_id,
        "rol": rol,
    }
    token = crear_token_acceso(claims)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cliente_y_contexto(tmp_path: Path):
    ruta = tmp_path / "api_admin_recursos.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    cliente = TestClient(app)
    return cliente, tenant_id, ruta


# ---------------------------------------------------------------------------
# Profesionales: Alta y Modificación (Camino Feliz)
# ---------------------------------------------------------------------------


def test_alta_profesional_exitosa_201(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.post(
        "/api/v1/profesionales",
        json={
            "nombre": "Dra. Nueva",
            "matricula": "MN-9988",
            "especialidad": "Ortodoncia",
            "activo": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    datos = resp.json()
    assert datos["id"] is not None
    assert datos["nombre"] == "Dra. Nueva"
    assert datos["matricula"] == "MN-9988"
    assert datos["especialidad"] == "Ortodoncia"
    assert datos["activo"] is True


def test_profesional_creado_queda_disponible_para_turnos(cliente_y_contexto):
    """Verifica task 3.2: profesional creado se puede usar de inmediato para agendar y reprogramar."""
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    # 1. Crear profesional como Administrador
    resp_p = cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dr. Recien Creado", "matricula": "MP-1111"},
        headers=h_admin,
    )
    assert resp_p.status_code == 201
    prof_id = resp_p.json()["id"]

    # 2. Agendar turno con el nuevo profesional
    resp_turno = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Nuevo",
            "profesional": "Dr. Recien Creado",
            "sillon": "Sillón 1",
            "fecha": "2026-11-15",
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
        },
        headers=h_recep,
    )
    assert resp_turno.status_code == 201
    turno_id = resp_turno.json()["id"]

    # 3. Crear segundo profesional para reprogramar
    resp_p2 = cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dra. Reemplazo", "matricula": "MP-2222"},
        headers=h_admin,
    )
    assert resp_p2.status_code == 201
    p2_id = resp_p2.json()["id"]

    # 4. Reprogramar turno hacia el segundo profesional por ID
    resp_reprog = cliente.patch(
        f"/api/v1/turnos/{turno_id}/reprogramar",
        json={
            "fecha": "2026-11-15",
            "hora_inicio": "11:00",
            "hora_fin": "11:30",
            "profesional_id": p2_id,
        },
        headers=h_recep,
    )
    assert resp_reprog.status_code == 200
    assert resp_reprog.json()["profesional"] == "Dra. Reemplazo"


def test_modificacion_profesional_exitosa_200(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    resp_crear = cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dr. Para Editar", "matricula": "MP-01"},
        headers=headers,
    )
    prof_id = resp_crear.json()["id"]

    resp_mod = cliente.put(
        f"/api/v1/profesionales/{prof_id}",
        json={
            "nombre": "Dr. Pérez Modificado",
            "matricula": "MN-1234",
            "especialidad": "Endodoncia",
            "activo": False,
        },
        headers=headers,
    )
    assert resp_mod.status_code == 200
    datos = resp_mod.json()
    assert datos["id"] == prof_id
    assert datos["nombre"] == "Dr. Pérez Modificado"
    assert datos["matricula"] == "MN-1234"
    assert datos["especialidad"] == "Endodoncia"
    assert datos["activo"] is False


# ---------------------------------------------------------------------------
# Sillones: Alta y Modificación (Camino Feliz)
# ---------------------------------------------------------------------------


def test_alta_sillon_exitosa_201(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.post(
        "/api/v1/sillones",
        json={
            "nombre": "Sillón Quirúrgico 4",
            "equipamiento": "Turbina LED y Cavitador",
            "activo": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    datos = resp.json()
    assert datos["id"] is not None
    assert datos["nombre"] == "Sillón Quirúrgico 4"
    assert datos["equipamiento"] == "Turbina LED y Cavitador"
    assert datos["activo"] is True


def test_sillon_creado_queda_disponible_para_turnos(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    h_admin = _headers(tenant_id, rol="Administrador")
    h_recep = _headers(tenant_id, rol="Recepcionista")

    # 1. Crear sillón
    resp_s = cliente.post(
        "/api/v1/sillones",
        json={"nombre": "Sillón Nuevo Box", "equipamiento": "Completo"},
        headers=h_admin,
    )
    assert resp_s.status_code == 201
    sil_id = resp_s.json()["id"]

    # 2. Agendar turno usando el nuevo sillón
    resp_turno = cliente.post(
        "/api/v1/turnos",
        json={
            "paciente": "Paciente Box",
            "profesional": "Dr. Ejemplo",
            "sillon": "Sillón Nuevo Box",
            "fecha": "2026-11-16",
            "hora_inicio": "10:00",
            "hora_fin": "10:30",
        },
        headers=h_recep,
    )
    assert resp_turno.status_code == 201
    turno_id = resp_turno.json()["id"]

    # 3. Reprogramar turno especificando el sillón por ID
    resp_reprog = cliente.patch(
        f"/api/v1/turnos/{turno_id}/reprogramar",
        json={
            "fecha": "2026-11-16",
            "hora_inicio": "14:00",
            "hora_fin": "14:30",
            "sillon_id": sil_id,
        },
        headers=h_recep,
    )
    assert resp_reprog.status_code == 200
    assert resp_reprog.json()["sillon"] == "Sillón Nuevo Box"


def test_modificacion_sillon_exitosa_200(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    resp_crear = cliente.post(
        "/api/v1/sillones",
        json={"nombre": "Sillón Edición", "equipamiento": "Original"},
        headers=headers,
    )
    sil_id = resp_crear.json()["id"]

    resp_mod = cliente.put(
        f"/api/v1/sillones/{sil_id}",
        json={
            "nombre": "Sillón 1 Renovado",
            "equipamiento": "Lámpara blanqueamiento",
            "activo": True,
        },
        headers=headers,
    )
    assert resp_mod.status_code == 200
    datos = resp_mod.json()
    assert datos["id"] == sil_id
    assert datos["nombre"] == "Sillón 1 Renovado"
    assert datos["equipamiento"] == "Lámpara blanqueamiento"
    assert datos["activo"] is True


# ---------------------------------------------------------------------------
# Duplicados (409)
# ---------------------------------------------------------------------------


def test_rechazo_profesional_nombre_duplicado(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dr. Existente", "matricula": "MN-1"},
        headers=headers,
    )

    # Intento de crear duplicado
    resp_dupl = cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dr. Existente", "matricula": "MN-2"},
        headers=headers,
    )
    assert resp_dupl.status_code == 409
    assert resp_dupl.json()["error"]["code"] == "NOMBRE_PROFESIONAL_DUPLICADO"


def test_rechazo_profesional_colision_al_editar(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    cliente.post("/api/v1/profesionales", json={"nombre": "Dr. Uno"}, headers=headers)
    p2 = cliente.post("/api/v1/profesionales", json={"nombre": "Dr. Dos"}, headers=headers).json()

    # Intentar renombrar p2 a Dr. Uno
    resp_col = cliente.put(
        f"/api/v1/profesionales/{p2['id']}",
        json={"nombre": "Dr. Uno", "activo": True},
        headers=headers,
    )
    assert resp_col.status_code == 409
    assert resp_col.json()["error"]["code"] == "NOMBRE_PROFESIONAL_DUPLICADO"


def test_rechazo_sillon_nombre_duplicado(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    cliente.post(
        "/api/v1/sillones",
        json={"nombre": "Sillón Principal"},
        headers=headers,
    )

    resp_dupl = cliente.post(
        "/api/v1/sillones",
        json={"nombre": "Sillón Principal"},
        headers=headers,
    )
    assert resp_dupl.status_code == 409
    assert resp_dupl.json()["error"]["code"] == "NOMBRE_SILLON_DUPLICADO"


def test_rechazo_sillon_colision_al_editar(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    cliente.post("/api/v1/sillones", json={"nombre": "Sillón A"}, headers=headers)
    s2 = cliente.post("/api/v1/sillones", json={"nombre": "Sillón B"}, headers=headers).json()

    resp_col = cliente.put(
        f"/api/v1/sillones/{s2['id']}",
        json={"nombre": "Sillón A", "activo": True},
        headers=headers,
    )
    assert resp_col.status_code == 409
    assert resp_col.json()["error"]["code"] == "NOMBRE_SILLON_DUPLICADO"


# ---------------------------------------------------------------------------
# Recursos Inexistentes o Ajenos (404)
# ---------------------------------------------------------------------------


def test_profesional_inexistente_o_ajeno_devuelve_404(cliente_y_contexto):
    cliente, tenant_id, ruta = cliente_y_contexto
    h_admin_t1 = _headers(tenant_id, rol="Administrador")

    # Inexistente
    resp_inex = cliente.put(
        "/api/v1/profesionales/9999",
        json={"nombre": "Dr. No Existe", "activo": True},
        headers=h_admin_t1,
    )
    assert resp_inex.status_code == 404
    assert resp_inex.json()["error"]["code"] == "PROFESIONAL_NO_ENCONTRADO"

    # Tenant 2
    conn = abrir_conexion(ruta)
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Ajena')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Ajena'").fetchone()[0]
    conn.commit()
    conn.close()

    h_admin_t2 = _headers(t2_id, rol="Administrador")
    p_t2 = cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dr. Ajeno"},
        headers=h_admin_t2,
    ).json()

    # Tenant 1 intenta modificar recurso de Tenant 2
    resp_ajeno = cliente.put(
        f"/api/v1/profesionales/{p_t2['id']}",
        json={"nombre": "Dr. Modificado Ajeno", "activo": True},
        headers=h_admin_t1,
    )
    assert resp_ajeno.status_code == 404
    assert resp_ajeno.json()["error"]["code"] == "PROFESIONAL_NO_ENCONTRADO"


def test_sillon_inexistente_o_ajeno_devuelve_404(cliente_y_contexto):
    cliente, tenant_id, ruta = cliente_y_contexto
    h_admin_t1 = _headers(tenant_id, rol="Administrador")

    resp_inex = cliente.put(
        "/api/v1/sillones/9999",
        json={"nombre": "Sillón No Existe", "activo": True},
        headers=h_admin_t1,
    )
    assert resp_inex.status_code == 404
    assert resp_inex.json()["error"]["code"] == "SILLON_NO_ENCONTRADO"

    conn = abrir_conexion(ruta)
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica B')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica B'").fetchone()[0]
    conn.commit()
    conn.close()

    h_admin_t2 = _headers(t2_id, rol="Administrador")
    s_t2 = cliente.post("/api/v1/sillones", json={"nombre": "Sillón B"}, headers=h_admin_t2).json()

    resp_ajeno = cliente.put(
        f"/api/v1/sillones/{s_t2['id']}",
        json={"nombre": "Sillón Modificado", "activo": True},
        headers=h_admin_t1,
    )
    assert resp_ajeno.status_code == 404
    assert resp_ajeno.json()["error"]["code"] == "SILLON_NO_ENCONTRADO"


# ---------------------------------------------------------------------------
# Seguridad y RBAC (401 / 403)
# ---------------------------------------------------------------------------


def test_seguridad_sin_token_devuelve_401(cliente_y_contexto):
    cliente, _, _ = cliente_y_contexto

    for ruta in ("/api/v1/profesionales", "/api/v1/sillones"):
        assert cliente.post(ruta, json={"nombre": "Recurso"}).status_code == 401
        assert cliente.put(f"{ruta}/1", json={"nombre": "Recurso", "activo": True}).status_code == 401


def test_rbac_roles_no_autorizados_devuelve_403(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto

    for rol in ("Recepcionista", "Profesional"):
        headers = _headers(tenant_id, rol=rol)
        # Profesionales
        resp_post_p = cliente.post("/api/v1/profesionales", json={"nombre": "Dr. X"}, headers=headers)
        assert resp_post_p.status_code == 403
        assert resp_post_p.json()["error"]["code"] == "ACCESO_DENEGADO"

        resp_put_p = cliente.put("/api/v1/profesionales/1", json={"nombre": "Dr. X", "activo": True}, headers=headers)
        assert resp_put_p.status_code == 403
        assert resp_put_p.json()["error"]["code"] == "ACCESO_DENEGADO"

        # Sillones
        resp_post_s = cliente.post("/api/v1/sillones", json={"nombre": "Sillón X"}, headers=headers)
        assert resp_post_s.status_code == 403
        assert resp_post_s.json()["error"]["code"] == "ACCESO_DENEGADO"

        resp_put_s = cliente.put("/api/v1/sillones/1", json={"nombre": "Sillón X", "activo": True}, headers=headers)
        assert resp_put_s.status_code == 403
        assert resp_put_s.json()["error"]["code"] == "ACCESO_DENEGADO"


# ---------------------------------------------------------------------------
# Validación (422)
# ---------------------------------------------------------------------------


def test_validacion_nombre_vacio_devuelve_422(cliente_y_contexto):
    cliente, tenant_id, _ = cliente_y_contexto
    headers = _headers(tenant_id, rol="Administrador")

    # Nombre vacío
    resp1 = cliente.post("/api/v1/profesionales", json={"nombre": ""}, headers=headers)
    assert resp1.status_code == 422
    assert resp1.json()["error"]["code"] == "VALIDACION"

    # Nombre con solo espacios
    resp2 = cliente.post("/api/v1/sillones", json={"nombre": "    "}, headers=headers)
    assert resp2.status_code == 422
    assert resp2.json()["error"]["code"] == "VALIDACION"


# ---------------------------------------------------------------------------
# Auditoría (C-09)
# ---------------------------------------------------------------------------


def test_auditoria_de_operaciones_crud_recursos(cliente_y_contexto):
    cliente, tenant_id, ruta = cliente_y_contexto
    conn = abrir_conexion(ruta)
    admin_id = conn.execute(
        "SELECT id FROM usuario WHERE tenant_id = ? AND rol = 'Administrador'",
        (tenant_id,),
    ).fetchone()[0]
    conn.close()
    headers = _headers(tenant_id, rol="Administrador", usuario_id=admin_id)

    # 1. Crear profesional
    p = cliente.post(
        "/api/v1/profesionales",
        json={"nombre": "Dr. Auditado", "especialidad": "Periodoncia"},
        headers=headers,
    ).json()

    # 2. Modificar profesional
    cliente.put(
        f"/api/v1/profesionales/{p['id']}",
        json={"nombre": "Dr. Auditado Modificado", "activo": False},
        headers=headers,
    )

    # 3. Crear sillón
    s = cliente.post(
        "/api/v1/sillones",
        json={"nombre": "Sillón Auditado", "equipamiento": "Laser"},
        headers=headers,
    ).json()

    # 4. Modificar sillón
    cliente.put(
        f"/api/v1/sillones/{s['id']}",
        json={"nombre": "Sillón Auditado Modificado", "activo": True},
        headers=headers,
    )

    # Consultar auditoría
    resp_aud = cliente.get("/api/v1/auditoria", headers=headers)
    assert resp_aud.status_code == 200
    acciones = [ev["accion"] for ev in resp_aud.json()]

    assert "CREAR_PROFESIONAL" in acciones
    assert "MODIFICAR_PROFESIONAL" in acciones
    assert "CREAR_SILLON" in acciones
    assert "MODIFICAR_SILLON" in acciones

    ev_crear_p = next(ev for ev in resp_aud.json() if ev["accion"] == "CREAR_PROFESIONAL")
    assert ev_crear_p["entidad"] == "profesional"
    assert ev_crear_p["entidad_id"] == p["id"]
    assert ev_crear_p["usuario_id"] == admin_id
    assert "Periodoncia" in ev_crear_p["detalle"]
