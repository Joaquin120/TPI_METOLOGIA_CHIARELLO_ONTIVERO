"""Tests del repositorio de usuarios SQLite (C-04, task 1.3).

Verifica la persistencia y consulta de usuarios en SQLite real.
"""

import sqlite3
import pytest

from src.infrastructure.database import abrir_conexion, migrar
from src.repositories.usuarios_sqlite import RepositorioUsuariosSqlite, Usuario


@pytest.fixture
def conexion(tmp_path) -> sqlite3.Connection:
    ruta = tmp_path / "test_usuarios.db"
    con = abrir_conexion(str(ruta))
    migrar(con)
    con.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Dental A')")
    con.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Dental B')")
    con.commit()
    try:
        yield con
    finally:
        con.close()


def test_crear_y_buscar_por_email(conexion: sqlite3.Connection) -> None:
    repo = RepositorioUsuariosSqlite(conexion)
    usuario = repo.crear(
        tenant_id=1,
        email="recepcion@dental-a.com",
        password_hash="hash_secreto_123",
        rol="Recepcionista",
    )

    assert usuario.id is not None
    assert usuario.email == "recepcion@dental-a.com"
    assert usuario.rol == "Recepcionista"
    assert usuario.tenant_id == 1
    assert usuario.activo is True
    assert usuario.profesional_id is None

    encontrado = repo.buscar_por_email("recepcion@dental-a.com", tenant_id=1)
    assert encontrado is not None
    assert encontrado.id == usuario.id
    assert encontrado.email == "recepcion@dental-a.com"
    assert encontrado.password_hash == "hash_secreto_123"


def test_buscar_por_email_aislamiento_entre_tenants(conexion: sqlite3.Connection) -> None:
    repo = RepositorioUsuariosSqlite(conexion)
    repo.crear(
        tenant_id=1,
        email="usuario@comun.com",
        password_hash="hash_tenant_1",
        rol="Administrador",
    )
    repo.crear(
        tenant_id=2,
        email="usuario@comun.com",
        password_hash="hash_tenant_2",
        rol="Recepcionista",
    )

    u1 = repo.buscar_por_email("usuario@comun.com", tenant_id=1)
    assert u1 is not None
    assert u1.tenant_id == 1
    assert u1.password_hash == "hash_tenant_1"

    u2 = repo.buscar_por_email("usuario@comun.com", tenant_id=2)
    assert u2 is not None
    assert u2.tenant_id == 2
    assert u2.password_hash == "hash_tenant_2"


def test_buscar_por_id(conexion: sqlite3.Connection) -> None:
    repo = RepositorioUsuariosSqlite(conexion)
    creado = repo.crear(
        tenant_id=1,
        email="admin@dental-a.com",
        password_hash="hash_admin",
        rol="Administrador",
    )

    encontrado = repo.buscar_por_id(creado.id)
    assert encontrado is not None
    assert encontrado.id == creado.id
    assert encontrado.email == "admin@dental-a.com"
    assert encontrado.rol == "Administrador"

    assert repo.buscar_por_id(99999) is None

