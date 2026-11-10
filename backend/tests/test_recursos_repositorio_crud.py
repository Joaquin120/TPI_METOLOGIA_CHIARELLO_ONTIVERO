"""Pruebas unitarias de persistencia para operaciones CRUD de profesionales y sillones (C-09b, task 1.4).

Verifica creación, modificación, control de duplicados y aislamiento inter-tenant estricto sobre SQLite real.
"""

from pathlib import Path
import pytest

from src.domain.exceptions import RecursoDuplicadoError
from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import TENANT_DEFECTO, sembrar_datos_iniciales
from src.repositories.recursos import RepositorioProfesionales, RepositorioSillones


@pytest.fixture
def conexion_y_tenants(tmp_path: Path):
    ruta = tmp_path / "test_recursos_crud.db"
    conn = abrir_conexion(ruta)
    migrar(conn)
    sembrar_datos_iniciales(conn)
    t1_id = conn.execute("SELECT id FROM tenant WHERE nombre = ?", (TENANT_DEFECTO,)).fetchone()[0]
    conn.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Secundaria')")
    t2_id = conn.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Secundaria'").fetchone()[0]
    conn.commit()
    yield conn, t1_id, t2_id, ruta
    conn.close()


def test_profesional_crear_exitoso(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioProfesionales(conn, t1_id)

    prof = repo.crear(
        nombre="Dra. Gómez",
        matricula="MP-5555",
        especialidad="Endodoncia",
        activo=True,
    )

    assert prof.id is not None
    assert prof.nombre == "Dra. Gómez"
    assert prof.matricula == "MP-5555"
    assert prof.especialidad == "Endodoncia"
    assert prof.activo is True

    recuperado = repo.obtener_por_id(prof.id)
    assert recuperado == prof


def test_profesional_crear_duplicado_mismo_tenant_lanza_recurso_duplicado(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioProfesionales(conn, t1_id)

    repo.crear(nombre="Dr. Unico", matricula="MP-1")
    with pytest.raises(RecursoDuplicadoError, match="Dr. Unico"):
        repo.crear(nombre="Dr. Unico", matricula="MP-2")


def test_profesional_mismo_nombre_distinto_tenant_permitido(conexion_y_tenants):
    conn, t1_id, t2_id, _ = conexion_y_tenants
    repo1 = RepositorioProfesionales(conn, t1_id)
    repo2 = RepositorioProfesionales(conn, t2_id)

    p1 = repo1.crear(nombre="Dr. Compartido", matricula="MP-10")
    p2 = repo2.crear(nombre="Dr. Compartido", matricula="MP-20")

    assert p1.id != p2.id
    assert p1.nombre == p2.nombre


def test_profesional_actualizar_exitoso(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioProfesionales(conn, t1_id)

    creado = repo.crear(nombre="Dr. Original", matricula="MP-100", especialidad="General", activo=True)
    actualizado = repo.actualizar(
        id_=creado.id,
        nombre="Dr. Editado",
        matricula="MP-200",
        especialidad="Ortodoncia",
        activo=False,
    )

    assert actualizado is not None
    assert actualizado.nombre == "Dr. Editado"
    assert actualizado.matricula == "MP-200"
    assert actualizado.especialidad == "Ortodoncia"
    assert actualizado.activo is False


def test_profesional_actualizar_inexistente_o_ajeno_devuelve_none(conexion_y_tenants):
    conn, t1_id, t2_id, _ = conexion_y_tenants
    repo1 = RepositorioProfesionales(conn, t1_id)
    repo2 = RepositorioProfesionales(conn, t2_id)

    creado_t1 = repo1.crear(nombre="Dr. T1")
    assert repo1.actualizar(id_=9999, nombre="Dr. Fantasma") is None
    assert repo2.actualizar(id_=creado_t1.id, nombre="Dr. IntentoHack") is None


def test_profesional_actualizar_colision_nombre_lanza_recurso_duplicado(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioProfesionales(conn, t1_id)

    p1 = repo.crear(nombre="Dr. Primero")
    p2 = repo.crear(nombre="Dr. Segundo")

    with pytest.raises(RecursoDuplicadoError, match="Dr. Primero"):
        repo.actualizar(id_=p2.id, nombre="Dr. Primero")


def test_profesional_actualizar_mismo_nombre_no_colisiona(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioProfesionales(conn, t1_id)

    p = repo.crear(nombre="Dr. Estable", matricula="MP-1")
    actualizado = repo.actualizar(id_=p.id, nombre="Dr. Estable", matricula="MP-2")
    assert actualizado is not None
    assert actualizado.matricula == "MP-2"


# ---------------------------------------------------------------------------
# RepositorioSillones Tests
# ---------------------------------------------------------------------------


def test_sillon_crear_exitoso(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioSillones(conn, t1_id)

    sillon = repo.crear(
        nombre="Sillón Cirugía",
        equipamiento="Lámpara cialítica + Turbina",
        activo=True,
    )

    assert sillon.id is not None
    assert sillon.nombre == "Sillón Cirugía"
    assert sillon.equipamiento == "Lámpara cialítica + Turbina"
    assert sillon.activo is True

    recuperado = repo.obtener_por_id(sillon.id)
    assert recuperado == sillon


def test_sillon_crear_duplicado_mismo_tenant_lanza_recurso_duplicado(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioSillones(conn, t1_id)

    repo.crear(nombre="Sillón Alpha")
    with pytest.raises(RecursoDuplicadoError, match="Sillón Alpha"):
        repo.crear(nombre="Sillón Alpha")


def test_sillon_mismo_nombre_distinto_tenant_permitido(conexion_y_tenants):
    conn, t1_id, t2_id, _ = conexion_y_tenants
    repo1 = RepositorioSillones(conn, t1_id)
    repo2 = RepositorioSillones(conn, t2_id)

    s1 = repo1.crear(nombre="Sillón Común")
    s2 = repo2.crear(nombre="Sillón Común")

    assert s1.id != s2.id
    assert s1.nombre == s2.nombre


def test_sillon_actualizar_exitoso(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioSillones(conn, t1_id)

    s = repo.crear(nombre="Sillón Beta", equipamiento="Básico", activo=True)
    actualizado = repo.actualizar(
        id_=s.id,
        nombre="Sillón Beta Renovado",
        equipamiento="Turbina LED",
        activo=False,
    )

    assert actualizado is not None
    assert actualizado.nombre == "Sillón Beta Renovado"
    assert actualizado.equipamiento == "Turbina LED"
    assert actualizado.activo is False


def test_sillon_actualizar_inexistente_o_ajeno_devuelve_none(conexion_y_tenants):
    conn, t1_id, t2_id, _ = conexion_y_tenants
    repo1 = RepositorioSillones(conn, t1_id)
    repo2 = RepositorioSillones(conn, t2_id)

    s1 = repo1.crear(nombre="Sillón T1")
    assert repo1.actualizar(id_=9999, nombre="Sillón Fantasma") is None
    assert repo2.actualizar(id_=s1.id, nombre="Sillón Hack") is None


def test_sillon_actualizar_colision_nombre_lanza_recurso_duplicado(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioSillones(conn, t1_id)

    s1 = repo.crear(nombre="Sillón Uno")
    s2 = repo.crear(nombre="Sillón Dos")

    with pytest.raises(RecursoDuplicadoError, match="Sillón Uno"):
        repo.actualizar(id_=s2.id, nombre="Sillón Uno")


def test_sillon_actualizar_mismo_nombre_no_colisiona(conexion_y_tenants):
    conn, t1_id, _, _ = conexion_y_tenants
    repo = RepositorioSillones(conn, t1_id)

    s = repo.crear(nombre="Sillón Fijo", equipamiento="A")
    actualizado = repo.actualizar(id_=s.id, nombre="Sillón Fijo", equipamiento="B")
    assert actualizado is not None
    assert actualizado.equipamiento == "B"
