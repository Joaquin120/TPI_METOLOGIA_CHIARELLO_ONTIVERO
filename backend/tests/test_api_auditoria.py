"""Pruebas de integración del módulo de auditoría y trazabilidad (C-09, RN-05, RN-06).

Valida consultas a la bitácora sobre SQLite real, ordenamiento cronológico inverso,
aislamiento multi-tenant estricto, control de acceso RBAC exclusivo para Administrador
y envelope unificado de errores.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.esquemas import RegistroAuditoriaRespuesta
from src.api.seguridad import crear_token_acceso
from src.domain.models import RegistroAuditoria
from src.infrastructure.database import abrir_conexion
from src.infrastructure.seed import TENANT_DEFECTO
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite


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


@pytest.fixture()
def cliente_y_tenant(tmp_path: Path) -> tuple[TestClient, int, Path]:
    ruta = tmp_path / "api_auditoria.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    return TestClient(app), tenant_id, ruta


def _crear_evento_auditoria(
    ruta: Path,
    tenant_id: int,
    usuario_id: int,
    accion: str,
    entidad: str,
    fecha_hora: str,
    entidad_id: int | None = None,
    detalle: str | None = None,
) -> int:
    conexion = abrir_conexion(ruta)
    try:
        repo = RepositorioAuditoriaSqlite(conexion)
        reg = repo.registrar(
            RegistroAuditoria(
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                accion=accion,
                entidad=entidad,
                entidad_id=entidad_id,
                detalle=detalle,
                fecha_hora=fecha_hora,
            )
        )
        assert reg.id is not None
        return reg.id
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Requirement: Consulta y filtrado de eventos de auditoría
# ---------------------------------------------------------------------------


def test_listar_auditoria_exitoso(cliente_y_tenant) -> None:
    """Escenario: Consulta exitosa de eventos de auditoría del tenant con código 200."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador", usuario_id=1)

    _crear_evento_auditoria(
        ruta, tenant_id, 1, "CREAR", "Turno", "2026-11-09 10:00", 101, "Alta de turno"
    )
    _crear_evento_auditoria(
        ruta, tenant_id, 1, "CANCELAR", "Turno", "2026-11-09 11:00", 101, "Cancelación de turno"
    )

    resp = cliente.get("/api/v1/auditoria", headers=headers)
    assert resp.status_code == 200
    datos = resp.json()
    assert isinstance(datos, list)
    assert len(datos) == 2
    # Ordenamiento cronológico inverso: el de las 11:00 primero
    assert datos[0]["accion"] == "CANCELAR"
    assert datos[1]["accion"] == "CREAR"
    assert datos[0]["tenant_id"] == tenant_id
    assert datos[0]["usuario_id"] == 1
    assert datos[0]["entidad"] == "Turno"
    assert datos[0]["entidad_id"] == 101
    assert datos[0]["detalle"] == "Cancelación de turno"


def test_listar_auditoria_filtrado_por_fechas(cliente_y_tenant) -> None:
    """Escenario: Filtrado de auditoría por rango fecha_desde y fecha_hasta."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    _crear_evento_auditoria(ruta, tenant_id, 1, "CREAR", "Turno", "2026-10-15 10:00")
    _crear_evento_auditoria(ruta, tenant_id, 1, "CREAR", "Turno", "2026-11-05 10:00")
    _crear_evento_auditoria(ruta, tenant_id, 1, "CREAR", "Turno", "2026-12-01 10:00")

    resp = cliente.get(
        "/api/v1/auditoria?fecha_desde=2026-11-01&fecha_hasta=2026-11-30",
        headers=headers,
    )
    assert resp.status_code == 200
    datos = resp.json()
    assert len(datos) == 1
    assert datos[0]["fecha_hora"] == "2026-11-05 10:00"


def test_listar_auditoria_fechas_invertidas_devuelve_422(cliente_y_tenant) -> None:
    """Escenario: Rechazo 422 con envelope RANGO_FECHAS_INVALIDO si fecha_desde > fecha_hasta."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.get(
        "/api/v1/auditoria?fecha_desde=2026-11-15&fecha_hasta=2026-11-01",
        headers=headers,
    )
    assert resp.status_code == 422
    cuerpo = resp.json()
    assert "error" in cuerpo
    assert cuerpo["error"]["code"] == "RANGO_FECHAS_INVALIDO"


def test_listar_auditoria_filtrado_por_entidad_y_accion(cliente_y_tenant) -> None:
    """Escenario: Filtrado de eventos por entidad, acción y usuario_id."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    _crear_evento_auditoria(ruta, tenant_id, 1, "CREAR", "Turno", "2026-11-09 10:00")
    _crear_evento_auditoria(ruta, tenant_id, 1, "CREAR", "Paciente", "2026-11-09 10:10")
    _crear_evento_auditoria(ruta, tenant_id, 2, "MODIFICAR", "Turno", "2026-11-09 10:20")

    # Filtrar por entidad
    resp_ent = cliente.get("/api/v1/auditoria?entidad=Paciente", headers=headers)
    assert resp_ent.status_code == 200
    assert len(resp_ent.json()) == 1
    assert resp_ent.json()[0]["entidad"] == "Paciente"

    # Filtrar por acción
    resp_acc = cliente.get("/api/v1/auditoria?accion=MODIFICAR", headers=headers)
    assert resp_acc.status_code == 200
    assert len(resp_acc.json()) == 1
    assert resp_acc.json()[0]["accion"] == "MODIFICAR"

    # Filtrar por usuario_id
    resp_usr = cliente.get("/api/v1/auditoria?usuario_id=2", headers=headers)
    assert resp_usr.status_code == 200
    assert len(resp_usr.json()) == 1
    assert resp_usr.json()[0]["usuario_id"] == 2


def test_listar_auditoria_aislamiento_multitenant(cliente_y_tenant) -> None:
    """Escenario: Aislamiento estricto de auditoría entre clínicas distintas."""
    cliente, t1_id, ruta = cliente_y_tenant

    # Crear Tenant 2
    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Secundaria')")
        t2_id = conexion.execute(
            "SELECT id FROM tenant WHERE nombre = 'Clínica Secundaria'"
        ).fetchone()[0]
        conexion.execute(
            "INSERT INTO usuario (tenant_id, email, password_hash, rol) VALUES (?, 'admin2@secundaria.com', 'h', 'Administrador')",
            (t2_id,),
        )
        u2_id = conexion.execute("SELECT id FROM usuario WHERE email = 'admin2@secundaria.com'").fetchone()[0]
        conexion.commit()
    finally:
        conexion.close()

    _crear_evento_auditoria(ruta, t1_id, 1, "CREAR", "Turno", "2026-11-09 10:00", detalle="Tenant 1 Evento")
    _crear_evento_auditoria(ruta, t2_id, u2_id, "CREAR", "Turno", "2026-11-09 10:05", detalle="Tenant 2 Evento")

    # Consulta Tenant 1
    resp_t1 = cliente.get("/api/v1/auditoria", headers=_headers(t1_id, rol="Administrador"))
    assert resp_t1.status_code == 200
    assert len(resp_t1.json()) == 1
    assert resp_t1.json()[0]["detalle"] == "Tenant 1 Evento"

    # Consulta Tenant 2
    resp_t2 = cliente.get("/api/v1/auditoria", headers=_headers(t2_id, rol="Administrador", usuario_id=u2_id))
    assert resp_t2.status_code == 200
    assert len(resp_t2.json()) == 1
    assert resp_t2.json()[0]["detalle"] == "Tenant 2 Evento"


# ---------------------------------------------------------------------------
# Requirement: Control de acceso RBAC y autenticación
# ---------------------------------------------------------------------------


def test_seguridad_auditoria_sin_autenticacion(cliente_y_tenant) -> None:
    """Escenario: 401 NO_AUTENTICADO si no hay cabecera Authorization."""
    cliente, _, _ = cliente_y_tenant

    resp = cliente.get("/api/v1/auditoria")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "NO_AUTENTICADO"


def test_seguridad_auditoria_roles_no_autorizados(cliente_y_tenant) -> None:
    """Escenario: 403 ACCESO_DENEGADO para roles Recepcionista y Profesional."""
    cliente, tenant_id, _ = cliente_y_tenant

    for rol in ("Recepcionista", "Profesional"):
        headers = _headers(tenant_id, rol=rol)
        resp = cliente.get("/api/v1/auditoria", headers=headers)
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ACCESO_DENEGADO"


def test_seguridad_auditoria_rol_administrador_permitido(cliente_y_tenant) -> None:
    """Escenario: 200 OK exclusivo para rol Administrador."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.get("/api/v1/auditoria", headers=headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Pruebas unitarias de cobertura del repositorio y esquemas
# ---------------------------------------------------------------------------


def test_repositorio_auditoria_unitario(tmp_path: Path) -> None:
    """Verifica registrar y listar directamente con base SQLite real."""
    ruta = tmp_path / "repo_auditoria.db"
    create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)

    conexion = abrir_conexion(ruta)
    try:
        repo = RepositorioAuditoriaSqlite(conexion)
        reg = RegistroAuditoria(
            tenant_id=tenant_id,
            usuario_id=1,
            accion="ELIMINAR",
            entidad="Turno",
            fecha_hora="2026-11-09 12:00",
        )
        guardado = repo.registrar(reg)
        assert guardado.id is not None

        items = repo.listar(tenant_id=tenant_id, accion="ELIMINAR")
        assert len(items) == 1
        assert items[0].accion == "ELIMINAR"

        # desde_dominio con id None lanza ValueError
        reg_sin_id = RegistroAuditoria(
            tenant_id=1,
            usuario_id=1,
            accion="TEST",
            entidad="Test",
            fecha_hora="2026-11-09 10:00",
            id=None,
        )
        with pytest.raises(ValueError, match="El registro de auditoría debe tener un id asignado"):
            RegistroAuditoriaRespuesta.desde_dominio(reg_sin_id)
    finally:
        conexion.close()
