"""Pruebas de integración de endpoints de métricas y reportes (C-08, RN-05, RN-06).

Valida consultas analíticas sobre SQLite real, cálculo exacto de tasa de cancelación,
aislamiento estricto multi-tenant, RBAC y envelope unificado de errores.
"""

from pathlib import Path
import sqlite3
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


@pytest.fixture()
def cliente_y_tenant(tmp_path: Path) -> tuple[TestClient, int, Path]:
    ruta = tmp_path / "api_metricas.db"
    app = create_app(ruta_db=ruta, sembrar=True)
    tenant_id = _id_tenant(ruta)
    return TestClient(app), tenant_id, ruta


def _crear_turno_manual(
    ruta: Path,
    tenant_id: int,
    profesional_nombre: str,
    sillon_nombre: str,
    paciente_nombre: str,
    fecha_inicio: str,
    fecha_fin: str,
    estado: str = "CONFIRMADO",
) -> None:
    conexion = abrir_conexion(ruta)
    try:
        prof_id = conexion.execute(
            "SELECT id FROM profesional WHERE tenant_id = ? AND nombre = ?",
            (tenant_id, profesional_nombre),
        ).fetchone()[0]
        sil_id = conexion.execute(
            "SELECT id FROM sillon WHERE tenant_id = ? AND nombre = ?",
            (tenant_id, sillon_nombre),
        ).fetchone()[0]
        dni_sintetico = f"{abs(hash((tenant_id, paciente_nombre))) % 90000000 + 10000000:08d}"
        conexion.execute(
            "INSERT OR IGNORE INTO paciente (tenant_id, nombre, dni, telefono) VALUES (?, ?, ?, '11111111')",
            (tenant_id, paciente_nombre, dni_sintetico),
        )
        pac_id = conexion.execute(
            "SELECT id FROM paciente WHERE tenant_id = ? AND nombre = ?",
            (tenant_id, paciente_nombre),
        ).fetchone()[0]

        conexion.execute(
            """
            INSERT INTO turno (
                tenant_id, paciente_id, profesional_id, sillon_id,
                fecha_hora_inicio, fecha_hora_fin, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, pac_id, prof_id, sil_id, fecha_inicio, fecha_fin, estado),
        )
        conexion.commit()
    finally:
        conexion.close()


# ---------------------------------------------------------------------------
# Requirement: Consulta de métricas agregadas de turnos
# ---------------------------------------------------------------------------


def test_metricas_turnos_tenant_vacio_retorna_ceros(cliente_y_tenant) -> None:
    """Escenario: Consulta exitosa de métricas en tenant sin turnos con tasa 0.0%."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.get("/api/v1/metricas/turnos", headers=headers)
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["total"] == 0
    assert datos["tasa_cancelacion"] == 0.0
    assert datos["por_estado"]["PENDIENTE"] == 0
    assert datos["por_estado"]["CONFIRMADO"] == 0
    assert datos["por_estado"]["CANCELADO"] == 0
    assert datos["por_estado"]["COMPLETADO"] == 0


def test_metricas_turnos_calculo_tasa_cancelacion(cliente_y_tenant) -> None:
    """Escenario: Cálculo de tasa de cancelación con 10 turnos totales y 2 cancelados (20.0%)."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    # 6 confirmados
    for i in range(6):
        _crear_turno_manual(
            ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", f"Paciente Conf {i}",
            f"2026-11-0{i+1} 10:00", f"2026-11-0{i+1} 10:30", "CONFIRMADO"
        )
    # 2 cancelados
    for i in range(2):
        _crear_turno_manual(
            ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", f"Paciente Canc {i}",
            f"2026-11-0{i+7} 10:00", f"2026-11-0{i+7} 10:30", "CANCELADO"
        )
    # 2 completados
    for i in range(2):
        _crear_turno_manual(
            ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", f"Paciente Comp {i}",
            f"2026-11-0{i+9} 10:00", f"2026-11-0{i+9} 10:30", "COMPLETADO"
        )

    resp = cliente.get("/api/v1/metricas/turnos", headers=headers)
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["total"] == 10
    assert datos["por_estado"]["CONFIRMADO"] == 6
    assert datos["por_estado"]["CANCELADO"] == 2
    assert datos["por_estado"]["COMPLETADO"] == 2
    assert datos["tasa_cancelacion"] == 20.0


def test_metricas_turnos_filtrado_por_rango_fechas(cliente_y_tenant) -> None:
    """Escenario: Filtrado de métricas acotadas a fecha_desde y fecha_hasta."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Recepcionista")

    # Octubre
    _crear_turno_manual(
        ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", "Paciente Oct",
        "2026-10-15 10:00", "2026-10-15 10:30", "CONFIRMADO"
    )
    # Noviembre
    _crear_turno_manual(
        ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", "Paciente Nov",
        "2026-11-05 10:00", "2026-11-05 10:30", "CONFIRMADO"
    )

    resp = cliente.get(
        "/api/v1/metricas/turnos?fecha_desde=2026-11-01&fecha_hasta=2026-11-30",
        headers=headers,
    )
    assert resp.status_code == 200
    datos = resp.json()
    assert datos["total"] == 1
    assert datos["fecha_desde"] == "2026-11-01"
    assert datos["fecha_hasta"] == "2026-11-30"


def test_metricas_turnos_rango_fechas_invertidas_devuelve_422(cliente_y_tenant) -> None:
    """Escenario: Error 422 con envelope RANGO_FECHAS_INVALIDO si fecha_desde > fecha_hasta."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.get(
        "/api/v1/metricas/turnos?fecha_desde=2026-11-15&fecha_hasta=2026-11-01",
        headers=headers,
    )
    assert resp.status_code == 422
    cuerpo = resp.json()
    assert "error" in cuerpo
    assert cuerpo["error"]["code"] == "RANGO_FECHAS_INVALIDO"


def test_metricas_turnos_formato_fecha_invalido_devuelve_422(cliente_y_tenant) -> None:
    """Escenario: Error 422 si el formato de fecha no cumple YYYY-MM-DD."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    resp = cliente.get(
        "/api/v1/metricas/turnos?fecha_desde=fecha-invalida",
        headers=headers,
    )
    assert resp.status_code == 422
    cuerpo = resp.json()
    assert "error" in cuerpo
    assert cuerpo["error"]["code"] == "VALIDACION"


def test_metricas_turnos_aislamiento_multitenant(cliente_y_tenant) -> None:
    """Escenario: Los turnos de un tenant B no afectan las métricas de tenant A."""
    cliente, t1_id, ruta = cliente_y_tenant

    # Crear Tenant 2
    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Centro Secundario')")
        t2_id = conexion.execute(
            "SELECT id FROM tenant WHERE nombre = 'Centro Secundario'"
        ).fetchone()[0]
        conexion.execute(
            "INSERT INTO profesional (tenant_id, nombre) VALUES (?, 'Dr. Secundario')",
            (t2_id,),
        )
        conexion.execute(
            "INSERT INTO sillon (tenant_id, nombre) VALUES (?, 'Sillón Secundario')",
            (t2_id,),
        )
        conexion.commit()
    finally:
        conexion.close()

    # 1 turno en Tenant 1
    _crear_turno_manual(
        ruta, t1_id, "Dr. Ejemplo", "Sillón 1", "Paciente T1",
        "2026-11-01 10:00", "2026-11-01 10:30", "CONFIRMADO"
    )
    # 5 turnos en Tenant 2
    for i in range(5):
        _crear_turno_manual(
            ruta, t2_id, "Dr. Secundario", "Sillón Secundario", f"Paciente T2_{i}",
            f"2026-11-0{i+1} 10:00", f"2026-11-0{i+1} 10:30", "CANCELADO"
        )

    # Consulta Tenant 1
    resp_t1 = cliente.get("/api/v1/metricas/turnos", headers=_headers(t1_id))
    assert resp_t1.status_code == 200
    assert resp_t1.json()["total"] == 1
    assert resp_t1.json()["tasa_cancelacion"] == 0.0

    # Consulta Tenant 2
    resp_t2 = cliente.get("/api/v1/metricas/turnos", headers=_headers(t2_id))
    assert resp_t2.status_code == 200
    assert resp_t2.json()["total"] == 5
    assert resp_t2.json()["tasa_cancelacion"] == 100.0


# ---------------------------------------------------------------------------
# Requirement: Consulta de métricas de recursos clínicos
# ---------------------------------------------------------------------------


def test_metricas_recursos_exitoso_con_left_join(cliente_y_tenant) -> None:
    """Escenario: Recursos sin turnos aparecen con total_turnos = 0 gracias a LEFT JOIN."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    # Asignar 2 turnos a Dr. Ejemplo en Sillón 1
    _crear_turno_manual(
        ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", "Paciente Rec 1",
        "2026-11-01 09:00", "2026-11-01 09:30"
    )
    _crear_turno_manual(
        ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", "Paciente Rec 2",
        "2026-11-01 10:00", "2026-11-01 10:30"
    )

    resp = cliente.get("/api/v1/metricas/recursos", headers=headers)
    assert resp.status_code == 200
    datos = resp.json()

    # Profesionales
    profs = {p["nombre"]: p["total_turnos"] for p in datos["profesionales"]}
    assert profs["Dr. Ejemplo"] == 2
    assert profs["Dra. Ejemplo"] == 0
    assert profs["Dr. Inactivo"] == 0

    # Sillones
    sills = {s["nombre"]: s["total_turnos"] for s in datos["sillones"]}
    assert sills["Sillón 1"] == 2
    assert sills["Sillón 2"] == 0
    assert sills["Sillón 3"] == 0


def test_metricas_recursos_con_filtro_fechas(cliente_y_tenant) -> None:
    """Escenario: Métricas de recursos filtradas por rango temporal."""
    cliente, tenant_id, ruta = cliente_y_tenant
    headers = _headers(tenant_id, rol="Administrador")

    # Octubre
    _crear_turno_manual(
        ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", "Paciente Rec Oct",
        "2026-10-15 09:00", "2026-10-15 09:30"
    )
    # Noviembre
    _crear_turno_manual(
        ruta, tenant_id, "Dr. Ejemplo", "Sillón 1", "Paciente Rec Nov",
        "2026-11-05 09:00", "2026-11-05 09:30"
    )

    resp = cliente.get(
        "/api/v1/metricas/recursos?fecha_desde=2026-11-01&fecha_hasta=2026-11-30",
        headers=headers,
    )
    assert resp.status_code == 200
    datos = resp.json()
    profs = {p["nombre"]: p["total_turnos"] for p in datos["profesionales"]}
    assert profs["Dr. Ejemplo"] == 1
    assert datos["fecha_desde"] == "2026-11-01"
    assert datos["fecha_hasta"] == "2026-11-30"


def test_metricas_recursos_aislamiento_multitenant(cliente_y_tenant) -> None:
    """Escenario: Recursos de Tenant 1 no incluyen profesionales ni sillones de Tenant 2."""
    cliente, t1_id, ruta = cliente_y_tenant

    conexion = abrir_conexion(ruta)
    try:
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Tercera')")
        t2_id = conexion.execute(
            "SELECT id FROM tenant WHERE nombre = 'Clínica Tercera'"
        ).fetchone()[0]
        conexion.execute(
            "INSERT INTO profesional (tenant_id, nombre) VALUES (?, 'Dr. Exclusivo T2')",
            (t2_id,),
        )
        conexion.commit()
    finally:
        conexion.close()

    resp = cliente.get("/api/v1/metricas/recursos", headers=_headers(t1_id))
    assert resp.status_code == 200
    nombres_t1 = [p["nombre"] for p in resp.json()["profesionales"]]
    assert "Dr. Exclusivo T2" not in nombres_t1


# ---------------------------------------------------------------------------
# Requirement: Control de acceso RBAC y autenticación
# ---------------------------------------------------------------------------


def test_metricas_seguridad_sin_autenticacion(cliente_y_tenant) -> None:
    """Escenario: 401 NO_AUTENTICADO si no hay token."""
    cliente, _, _ = cliente_y_tenant

    resp_turnos = cliente.get("/api/v1/metricas/turnos")
    assert resp_turnos.status_code == 401
    assert resp_turnos.json()["error"]["code"] == "NO_AUTENTICADO"

    resp_recursos = cliente.get("/api/v1/metricas/recursos")
    assert resp_recursos.status_code == 401
    assert resp_recursos.json()["error"]["code"] == "NO_AUTENTICADO"


def test_metricas_seguridad_rol_profesional_denegado(cliente_y_tenant) -> None:
    """Escenario: 403 ACCESO_DENEGADO para rol Profesional."""
    cliente, tenant_id, _ = cliente_y_tenant
    headers_prof = _headers(tenant_id, rol="Profesional")

    resp_turnos = cliente.get("/api/v1/metricas/turnos", headers=headers_prof)
    assert resp_turnos.status_code == 403
    assert resp_turnos.json()["error"]["code"] == "ACCESO_DENEGADO"

    resp_recursos = cliente.get("/api/v1/metricas/recursos", headers=headers_prof)
    assert resp_recursos.status_code == 403
    assert resp_recursos.json()["error"]["code"] == "ACCESO_DENEGADO"


def test_metricas_roles_autorizados_admin_y_recepcion(cliente_y_tenant) -> None:
    """Escenario: 200 OK para Administrador y Recepcionista."""
    cliente, tenant_id, _ = cliente_y_tenant

    for rol in ("Administrador", "Recepcionista"):
        headers = _headers(tenant_id, rol=rol)
        assert cliente.get("/api/v1/metricas/turnos", headers=headers).status_code == 200
        assert cliente.get("/api/v1/metricas/recursos", headers=headers).status_code == 200
