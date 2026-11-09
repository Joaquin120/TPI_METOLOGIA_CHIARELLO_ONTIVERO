"""Pruebas de integración de la gestión de pacientes (C-07, RN-05, RN-06).

Garantiza aislamiento horizontal multi-tenant, unicidad por tenant, validación
estricta con envelope unificado y 100% datos sintéticos sin PII real.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.errores import ErrorPacienteDuplicado
from src.api.esquemas import PacienteRespuesta
from src.api.seguridad import crear_token_acceso
from src.domain.models import Paciente
from src.infrastructure.database import abrir_conexion
from src.infrastructure.seed import TENANT_DEFECTO
from src.repositories.pacientes_sqlite import RepositorioPacientesSqlite


# Fixtures sintéticos canónicos (RN-06)
FIXTURE_PACIENTE_A = {
    "dni": "10000001",
    "nombre": "Paciente Ficticio Uno",
    "telefono": "+54 11 4000-0001",
}

FIXTURE_PACIENTE_B = {
    "dni": "10000002",
    "nombre": "Paciente Ficticio Dos",
    "telefono": "+54 11 4000-0002",
}

FIXTURE_PACIENTE_COMPARTIDO = {
    "dni": "20000001",
    "nombre": "Paciente Sintético Compartido",
    "telefono": "+54 11 5000-0001",
}


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


@pytest.fixture()
def cliente_y_tenant(tmp_path: Path) -> tuple[TestClient, int, Path]:
    ruta = tmp_path / "api_pacientes.db"
    app = create_app(ruta_db=ruta, sembrar=False)
    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT OR IGNORE INTO tenant (nombre) VALUES (?)", (TENANT_DEFECTO,))
        conexion.commit()
    finally:
        conexion.close()
    tenant_id = _id_tenant(ruta)
    return TestClient(app), tenant_id, ruta


# ---------------------------------------------------------------------------
# Requirement: Alta de pacientes en el tenant
# ---------------------------------------------------------------------------


def test_crear_paciente_exitoso_camino_feliz(cliente_y_tenant) -> None:
    """Escenario: Alta exitosa de paciente con datos sintéticos válidos y código 201."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    respuesta = cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A, headers=headers)
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert isinstance(datos["id"], int)
    assert datos["tenant_id"] == tenant_id
    assert datos["dni"] == FIXTURE_PACIENTE_A["dni"]
    assert datos["nombre"] == FIXTURE_PACIENTE_A["nombre"]
    assert datos["telefono"] == FIXTURE_PACIENTE_A["telefono"]


def test_crear_paciente_dni_duplicado_mismo_tenant_rechazado(cliente_y_tenant) -> None:
    """Escenario: Rechazo 409 con envelope PACIENTE_DUPLICADO ante mismo DNI en el centro."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    resp1 = cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A, headers=headers)
    assert resp1.status_code == 201

    payload_duplicado = {
        "dni": FIXTURE_PACIENTE_A["dni"],
        "nombre": "Paciente Colisión Sintético",
        "telefono": "+54 11 4000-9999",
    }
    resp2 = cliente.post("/api/v1/pacientes", json=payload_duplicado, headers=headers)
    assert resp2.status_code == 409
    cuerpo = resp2.json()
    assert "error" in cuerpo
    assert cuerpo["error"]["code"] == "PACIENTE_DUPLICADO"
    assert "DNI" in cuerpo["error"]["message"]


def test_crear_paciente_mismo_dni_distinto_tenant_permitido(cliente_y_tenant) -> None:
    """Escenario: Admisión del mismo DNI en tenants independientes con 201 en ambos."""
    cliente, t1_id, ruta = cliente_y_tenant

    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Centro Médico Secundario')")
        t2_id = conexion.execute(
            "SELECT id FROM tenant WHERE nombre = 'Centro Médico Secundario'"
        ).fetchone()[0]
        conexion.commit()
    finally:
        conexion.close()

    headers_t1 = _headers(t1_id, rol="Recepcionista")
    headers_t2 = _headers(t2_id, rol="Recepcionista")

    resp_t1 = cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_COMPARTIDO, headers=headers_t1)
    assert resp_t1.status_code == 201
    assert resp_t1.json()["tenant_id"] == t1_id

    resp_t2 = cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_COMPARTIDO, headers=headers_t2)
    assert resp_t2.status_code == 201
    assert resp_t2.json()["tenant_id"] == t2_id
    assert resp_t2.json()["id"] != resp_t1.json()["id"]


@pytest.mark.parametrize(
    "payload, campo_afectado",
    [
        ({"dni": "1000000A", "nombre": "Ana Sintética", "telefono": "+54 11 4000-0001"}, "dni"),
        ({"dni": "123", "nombre": "Ana Sintética", "telefono": "+54 11 4000-0001"}, "dni"),
        ({"dni": "123456789", "nombre": "Ana Sintética", "telefono": "+54 11 4000-0001"}, "dni"),
        ({"dni": "10000001", "nombre": "", "telefono": "+54 11 4000-0001"}, "nombre"),
        ({"dni": "10000001", "nombre": "   ", "telefono": "+54 11 4000-0001"}, "nombre"),
        ({"dni": "10000001", "nombre": "Ana Sintética", "telefono": "invalido"}, "telefono"),
        ({"dni": "10000001", "nombre": "Ana Sintética", "telefono": "+54 11 4000-0001", "tenant_id": 99}, "extra"),
        ({"dni": "10000001", "nombre": "Ana Sintética", "telefono": "+54 11 4000-0001", "id": 10}, "extra"),
    ],
)
def test_crear_paciente_validacion_fallida_envelope(cliente_y_tenant, payload, campo_afectado) -> None:
    """Escenario: Rechazo 422 con envelope VALIDACION ante datos mal formateados o campos extra."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    respuesta = cliente.post("/api/v1/pacientes", json=payload, headers=headers)
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert "error" in cuerpo
    assert cuerpo["error"]["code"] == "VALIDACION"
    assert isinstance(cuerpo["error"]["message"], str)


# ---------------------------------------------------------------------------
# Requirement: Consulta y filtrado de pacientes por tenant
# ---------------------------------------------------------------------------


def test_listar_pacientes_exitoso(cliente_y_tenant) -> None:
    """Escenario: Listado exitoso 200 de los pacientes registrados en el tenant."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A, headers=headers)
    cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_B, headers=headers)

    respuesta = cliente.get("/api/v1/pacientes", headers=headers)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert isinstance(datos, list)
    assert len(datos) == 2
    dnis = [p["dni"] for p in datos]
    assert FIXTURE_PACIENTE_A["dni"] in dnis
    assert FIXTURE_PACIENTE_B["dni"] in dnis


def test_listar_pacientes_aislamiento_horizontal_estricto(cliente_y_tenant) -> None:
    """Escenario: Aislamiento horizontal estricto entre tenants distintos."""
    cliente, t1_id, ruta = cliente_y_tenant

    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Centro Tercero')")
        t2_id = conexion.execute(
            "SELECT id FROM tenant WHERE nombre = 'Centro Tercero'"
        ).fetchone()[0]
        conexion.commit()
    finally:
        conexion.close()

    headers_t1 = _headers(t1_id, rol="Recepcionista")
    headers_t2 = _headers(t2_id, rol="Recepcionista")

    cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A, headers=headers_t1)
    cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_B, headers=headers_t2)

    # Tenant 1 consulta
    resp_t1 = cliente.get("/api/v1/pacientes", headers=headers_t1)
    assert resp_t1.status_code == 200
    items_t1 = resp_t1.json()
    assert len(items_t1) == 1
    assert items_t1[0]["dni"] == FIXTURE_PACIENTE_A["dni"]

    # Tenant 2 consulta
    resp_t2 = cliente.get("/api/v1/pacientes", headers=headers_t2)
    assert resp_t2.status_code == 200
    items_t2 = resp_t2.json()
    assert len(items_t2) == 1
    assert items_t2[0]["dni"] == FIXTURE_PACIENTE_B["dni"]


def test_filtrar_pacientes_por_dni_y_nombre(cliente_y_tenant) -> None:
    """Escenario: Filtrado por DNI exacto y por nombre parcial dentro del tenant."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A, headers=headers)
    cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_B, headers=headers)

    # Filtrar por DNI
    resp_dni = cliente.get(f"/api/v1/pacientes?dni={FIXTURE_PACIENTE_A['dni']}", headers=headers)
    assert resp_dni.status_code == 200
    assert len(resp_dni.json()) == 1
    assert resp_dni.json()[0]["dni"] == FIXTURE_PACIENTE_A["dni"]

    # Filtrar por nombre parcial
    resp_nom = cliente.get("/api/v1/pacientes?nombre=Dos", headers=headers)
    assert resp_nom.status_code == 200
    assert len(resp_nom.json()) == 1
    assert resp_nom.json()[0]["nombre"] == FIXTURE_PACIENTE_B["nombre"]

    # Filtrar sin coincidencias
    resp_vacio = cliente.get("/api/v1/pacientes?dni=99999999", headers=headers)
    assert resp_vacio.status_code == 200
    assert resp_vacio.json() == []


# ---------------------------------------------------------------------------
# Requirement: Control de acceso RBAC y autenticación
# ---------------------------------------------------------------------------


def test_seguridad_pacientes_sin_autenticacion(cliente_y_tenant) -> None:
    """Escenario: Peticiones sin token devuelven 401 NO_AUTENTICADO; con token malo TOKEN_INVALIDO."""
    cliente, _, _ = cliente_y_tenant

    resp_post = cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A)
    assert resp_post.status_code == 401
    assert resp_post.json()["error"]["code"] == "NO_AUTENTICADO"

    resp_get = cliente.get("/api/v1/pacientes")
    assert resp_get.status_code == 401
    assert resp_get.json()["error"]["code"] == "NO_AUTENTICADO"

    resp_corrupto = cliente.get("/api/v1/pacientes", headers={"Authorization": "Bearer corrupto"})
    assert resp_corrupto.status_code == 401
    assert resp_corrupto.json()["error"]["code"] == "TOKEN_INVALIDO"


def test_seguridad_pacientes_rol_no_autorizado_rechaza_creacion(cliente_y_tenant) -> None:
    """Escenario: Profesional no puede registrar pacientes (403 ACCESO_DENEGADO)."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers_prof = _headers(tenant_id, rol="Profesional")

    respuesta = cliente.post("/api/v1/pacientes", json=FIXTURE_PACIENTE_A, headers=headers_prof)
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "ACCESO_DENEGADO"


def test_roles_autorizados_creacion_y_consulta(cliente_y_tenant) -> None:
    """Escenario: Admin y Recepcionista pueden crear; Profesional puede consultar."""
    cliente, tenant_id, _ = cliente_y_tenant

    headers_admin = _headers(tenant_id, rol="Administrador")
    resp_adm = cliente.post(
        "/api/v1/pacientes",
        json={"dni": "30000001", "nombre": "Paciente de Admin", "telefono": "+54 11 4000-1111"},
        headers=headers_admin,
    )
    assert resp_adm.status_code == 201

    headers_prof = _headers(tenant_id, rol="Profesional")
    resp_prof_get = cliente.get("/api/v1/pacientes", headers=headers_prof)
    assert resp_prof_get.status_code == 200
    assert any(p["dni"] == "30000001" for p in resp_prof_get.json())


# ---------------------------------------------------------------------------
# Pruebas unitarias de cobertura del repositorio y esquemas
# ---------------------------------------------------------------------------


def test_repositorio_pacientes_metodos_unitarios(tmp_path: Path) -> None:
    """Verifica crear, buscar_por_id, buscar_por_dni y manejo de duplicados directo."""
    ruta = tmp_path / "repo_pacientes.db"
    app = create_app(ruta_db=ruta, sembrar=False)
    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT OR IGNORE INTO tenant (nombre) VALUES (?)", (TENANT_DEFECTO,))
        conexion.commit()
    finally:
        conexion.close()
    tenant_id = _id_tenant(ruta)

    conexion = abrir_conexion(ruta)
    try:
        repo = RepositorioPacientesSqlite(conexion)
        paciente = Paciente(
            dni="40000001",
            nombre="Paciente Repo Test",
            telefono="+54 11 4000-4444",
            tenant_id=tenant_id,
        )
        creado = repo.crear(paciente)
        assert creado.id is not None

        # Duplicado directo
        with pytest.raises(ErrorPacienteDuplicado):
            repo.crear(paciente)

        # buscar_por_id
        encontrado_id = repo.buscar_por_id(creado.id, tenant_id)
        assert encontrado_id is not None
        assert encontrado_id.dni == "40000001"
        assert repo.buscar_por_id(99999, tenant_id) is None

        # buscar_por_dni
        encontrado_dni = repo.buscar_por_dni("40000001", tenant_id)
        assert encontrado_dni is not None
        assert encontrado_dni.nombre == "Paciente Repo Test"
        assert repo.buscar_por_dni("99999999", tenant_id) is None

        # desde_dominio con id None lanza ValueError
        paciente_sin_id = Paciente(dni="11111111", nombre="X", telefono="12345678", tenant_id=1, id=None)
        with pytest.raises(ValueError, match="El paciente debe tener un id asignado"):
            PacienteRespuesta.desde_dominio(paciente_sin_id)
    finally:
        conexion.close()
