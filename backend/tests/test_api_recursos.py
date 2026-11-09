"""Pruebas de integración de los endpoints de recursos (C-06, F-04, F-05, RN-05, PA-01).

Valida los contratos de `GET /api/v1/profesionales` y `GET /api/v1/sillones` contra SQLite real
con datos puramente sintéticos (RN-06), formato completo, aislamiento multi-tenant y control de acceso.
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


def _headers(tenant_id: int, rol: str = "Recepcionista", usuario_id: int = 1, prof_id: int | None = None) -> dict[str, str]:
    claims = {
        "sub": str(usuario_id),
        "email": f"usuario@{tenant_id}.com",
        "tenant_id": tenant_id,
        "rol": rol,
    }
    if prof_id is not None:
        claims["profesional_id"] = prof_id
    token = crear_token_acceso(claims)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def cliente_y_tenant(tmp_path: Path) -> tuple[TestClient, int, Path]:
    ruta = tmp_path / "api_recursos.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    return TestClient(app), tenant_id, ruta


# ---------------------------------------------------------------------------
# Requirement: Listado de profesionales por tenant
# ---------------------------------------------------------------------------


def test_listar_profesionales_exitoso_y_formato_completo(cliente_y_tenant) -> None:
    """Escenario: Listado exitoso de profesionales con todos sus campos y código 200."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    respuesta = cliente.get("/api/v1/profesionales", headers=headers)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert isinstance(datos, list)
    # Por defecto solo_activos=True: debe incluir Dr. Ejemplo y Dra. Ejemplo, pero no Dr. Inactivo
    nombres = [p["nombre"] for p in datos]
    assert "Dr. Ejemplo" in nombres
    assert "Dra. Ejemplo" in nombres
    assert "Dr. Inactivo" not in nombres

    # Verificar contrato del primer profesional
    prof = next(p for p in datos if p["nombre"] == "Dr. Ejemplo")
    assert isinstance(prof["id"], int)
    assert prof["matricula"] == "MP-1001"
    assert prof["especialidad"] == "Odontología General"
    assert prof["activo"] is True
    assert "tenant_id" not in prof


def test_listar_profesionales_filtrado_solo_activos(cliente_y_tenant) -> None:
    """Escenario: Filtrado opcional por profesionales activos (resolución PA-01)."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    # solo_activos=true (explícito)
    resp_activos = cliente.get("/api/v1/profesionales?solo_activos=true", headers=headers)
    assert resp_activos.status_code == 200
    nombres_activos = [p["nombre"] for p in resp_activos.json()]
    assert "Dr. Inactivo" not in nombres_activos

    # solo_activos=false: incluye tanto activos como inactivos
    resp_todos = cliente.get("/api/v1/profesionales?solo_activos=false", headers=headers)
    assert resp_todos.status_code == 200
    datos_todos = resp_todos.json()
    nombres_todos = [p["nombre"] for p in datos_todos]
    assert "Dr. Ejemplo" in nombres_todos
    assert "Dra. Ejemplo" in nombres_todos
    assert "Dr. Inactivo" in nombres_todos

    prof_inactivo = next(p for p in datos_todos if p["nombre"] == "Dr. Inactivo")
    assert prof_inactivo["matricula"] == "MP-1003"
    assert prof_inactivo["especialidad"] == "Cirugía Maxilofacial"
    assert prof_inactivo["activo"] is False


def test_listar_profesionales_aislamiento_multitenant(cliente_y_tenant) -> None:
    """Escenario: Aislamiento estricto de profesionales entre tenants."""
    cliente, t1_id, ruta = cliente_y_tenant

    # Crear tenant 2 con un profesional propio
    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Foránea')")
        t2_id = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Foránea'").fetchone()[0]
        conexion.execute(
            """
            INSERT INTO profesional (tenant_id, nombre, matricula, especialidad, activo)
            VALUES (?, 'Dra. Foránea', 'MP-7777', 'Odontopediatría', 1)
            """,
            (t2_id,),
        )
        conexion.commit()
    finally:
        conexion.close()

    # Usuario de Tenant 1 consulta
    resp_t1 = cliente.get("/api/v1/profesionales?solo_activos=false", headers=_headers(t1_id))
    assert resp_t1.status_code == 200
    nombres_t1 = [p["nombre"] for p in resp_t1.json()]
    assert "Dra. Foránea" not in nombres_t1

    # Usuario de Tenant 2 consulta
    resp_t2 = cliente.get("/api/v1/profesionales", headers=_headers(t2_id))
    assert resp_t2.status_code == 200
    datos_t2 = resp_t2.json()
    assert len(datos_t2) == 1
    assert datos_t2[0]["nombre"] == "Dra. Foránea"
    assert datos_t2[0]["matricula"] == "MP-7777"


def test_listar_profesionales_requiere_autenticacion(cliente_y_tenant) -> None:
    """Escenario: Rechazo con 401 si la petición no incluye Authorization o token es inválido."""
    cliente, _, _ = cliente_y_tenant

    # Sin header
    resp_sin_auth = cliente.get("/api/v1/profesionales")
    assert resp_sin_auth.status_code == 401
    assert "error" in resp_sin_auth.json()
    assert resp_sin_auth.json()["error"]["code"] == "NO_AUTENTICADO"

    # Token inválido
    resp_invalido = cliente.get("/api/v1/profesionales", headers={"Authorization": "Bearer token.corrupto.xyz"})
    assert resp_invalido.status_code == 401
    assert resp_invalido.json()["error"]["code"] == "TOKEN_INVALIDO"


# ---------------------------------------------------------------------------
# Requirement: Listado de sillones odontológicos por tenant
# ---------------------------------------------------------------------------


def test_listar_sillones_exitoso_y_formato_completo(cliente_y_tenant) -> None:
    """Escenario: Listado exitoso de sillones con todos sus campos y código 200."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    respuesta = cliente.get("/api/v1/sillones", headers=headers)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert isinstance(datos, list)
    nombres = [s["nombre"] for s in datos]
    assert "Sillón 1" in nombres
    assert "Sillón 2" in nombres
    assert "Sillón 3" not in nombres  # Sillón 3 está inactivo por defecto

    sillon = next(s for s in datos if s["nombre"] == "Sillón 1")
    assert isinstance(sillon["id"], int)
    assert sillon["equipamiento"] == "Sillón Odontológico Básico"
    assert sillon["activo"] is True
    assert "tenant_id" not in sillon


def test_listar_sillones_filtrado_solo_activos(cliente_y_tenant) -> None:
    """Escenario: Filtrado opcional por sillones activos."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    # solo_activos=true
    resp_activos = cliente.get("/api/v1/sillones?solo_activos=true", headers=headers)
    assert resp_activos.status_code == 200
    nombres_activos = [s["nombre"] for s in resp_activos.json()]
    assert "Sillón 3" not in nombres_activos

    # solo_activos=false: incluye activos e inactivos
    resp_todos = cliente.get("/api/v1/sillones?solo_activos=false", headers=headers)
    assert resp_todos.status_code == 200
    datos_todos = resp_todos.json()
    nombres_todos = [s["nombre"] for s in datos_todos]
    assert "Sillón 1" in nombres_todos
    assert "Sillón 2" in nombres_todos
    assert "Sillón 3" in nombres_todos

    sillon_inactivo = next(s for s in datos_todos if s["nombre"] == "Sillón 3")
    assert sillon_inactivo["equipamiento"] == "En mantenimiento técnico"
    assert sillon_inactivo["activo"] is False


def test_listar_sillones_aislamiento_multitenant(cliente_y_tenant) -> None:
    """Escenario: Aislamiento estricto de sillones entre tenants."""
    cliente, t1_id, ruta = cliente_y_tenant

    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Otra')")
        t2_id = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Otra'").fetchone()[0]
        conexion.execute(
            """
            INSERT INTO sillon (tenant_id, nombre, equipamiento, activo)
            VALUES (?, 'Sillón Exclusivo Clínica Otra', 'Lámpara Blanqueamiento', 1)
            """,
            (t2_id,),
        )
        conexion.commit()
    finally:
        conexion.close()

    resp_t1 = cliente.get("/api/v1/sillones?solo_activos=false", headers=_headers(t1_id))
    assert resp_t1.status_code == 200
    nombres_t1 = [s["nombre"] for s in resp_t1.json()]
    assert "Sillón Exclusivo Clínica Otra" not in nombres_t1

    resp_t2 = cliente.get("/api/v1/sillones", headers=_headers(t2_id))
    assert resp_t2.status_code == 200
    datos_t2 = resp_t2.json()
    assert len(datos_t2) == 1
    assert datos_t2[0]["nombre"] == "Sillón Exclusivo Clínica Otra"


def test_listar_sillones_requiere_autenticacion(cliente_y_tenant) -> None:
    """Escenario: Rechazo con 401 si no hay token o es inválido en sillones."""
    cliente, _, _ = cliente_y_tenant

    resp_sin_auth = cliente.get("/api/v1/sillones")
    assert resp_sin_auth.status_code == 401
    assert resp_sin_auth.json()["error"]["code"] == "NO_AUTENTICADO"

    resp_invalido = cliente.get("/api/v1/sillones", headers={"Authorization": "Bearer invalido"})
    assert resp_invalido.status_code == 401
    assert resp_invalido.json()["error"]["code"] == "TOKEN_INVALIDO"


# ---------------------------------------------------------------------------
# Requirement: Control de acceso a recursos por roles del tenant
# ---------------------------------------------------------------------------


def test_recursos_permite_acceso_a_cualquier_rol_del_tenant(cliente_y_tenant) -> None:
    """Escenario: Administrador, Recepcionista y Profesional tienen lectura de recursos."""
    cliente, tenant_id, _ = cliente_y_tenant

    for rol in ("Administrador", "Recepcionista", "Profesional"):
        headers = _headers(tenant_id, rol=rol)
        res_prof = cliente.get("/api/v1/profesionales", headers=headers)
        assert res_prof.status_code == 200, f"Rol {rol} no pudo consultar profesionales"

        res_sil = cliente.get("/api/v1/sillones", headers=headers)
        assert res_sil.status_code == 200, f"Rol {rol} no pudo consultar sillones"

