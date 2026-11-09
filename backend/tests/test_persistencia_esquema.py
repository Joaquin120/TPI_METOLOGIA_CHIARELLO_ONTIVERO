"""Pruebas del esquema de persistencia (task 1.2, design D4).

Base SQLite REAL en archivo temporal por test: nunca se mockea la base
(regla dura 5 / D-04). Datos siempre sintéticos (regla dura 3 / RN-06).
"""

import sqlite3

import pytest

from src.infrastructure.database import abrir_conexion, migrar


def test_esquema_crea_las_tablas_esperadas(tmp_path) -> None:
    """Las migraciones 001 a 004 crean las tablas e índices, y son idempotentes."""
    ruta = tmp_path / "esquema.db"
    conexion = abrir_conexion(str(ruta))
    try:
        assert migrar(conexion) == ["001_init.sql", "002_auth.sql", "003_recursos.sql", "004_pacientes.sql"]
        # Segunda corrida: las migraciones ya registradas no se vuelven a aplicar.
        assert migrar(conexion) == []

        tablas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"tenant", "profesional", "sillon", "paciente", "turno", "usuario"} <= tablas
        assert "schema_migrations" in tablas

        aplicadas = conexion.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()
        assert [fila[0] for fila in aplicadas] == ["001_init.sql", "002_auth.sql", "003_recursos.sql", "004_pacientes.sql"]

        # Índice de solapamiento (tenant_id, fecha_hora_inicio) — design D4.
        columnas_indice = [
            fila[2]
            for fila in conexion.execute(
                "PRAGMA index_info(idx_turno_tenant_inicio)"
            )
        ]
        assert columnas_indice == ["tenant_id", "fecha_hora_inicio"]

        # Índice de usuario (tenant_id, email) — C-04.
        columnas_indice_usuario = [
            fila[2]
            for fila in conexion.execute(
                "PRAGMA index_info(idx_usuario_tenant_email)"
            )
        ]
        assert columnas_indice_usuario == ["tenant_id", "email"]

        # Índice de paciente (tenant_id, dni) — C-07.
        columnas_indice_paciente = [
            fila[2]
            for fila in conexion.execute(
                "PRAGMA index_info(idx_paciente_tenant_dni)"
            )
        ]
        assert columnas_indice_paciente == ["tenant_id", "dni"]
    finally:
        conexion.close()


def test_esquema_002_usuario_restricciones(tmp_path) -> None:
    """La tabla usuario valida CHECK de rol, UNIQUE(tenant_id, email) y FKs."""
    ruta = tmp_path / "usuario_integridad.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Test')")
        id_tenant = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Test'").fetchone()[0]

        # Inserción válida
        conexion.execute(
            "INSERT INTO usuario (tenant_id, email, password_hash, rol) VALUES (?, ?, ?, ?)",
            (id_tenant, "admin@test.com", "hash123", "Administrador"),
        )
        conexion.commit()

        # UNIQUE (tenant_id, email)
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO usuario (tenant_id, email, password_hash, rol) VALUES (?, ?, ?, ?)",
                (id_tenant, "admin@test.com", "otrohash", "Recepcionista"),
            )

        # CHECK (rol IN ('Administrador', 'Recepcionista', 'Profesional'))
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO usuario (tenant_id, email, password_hash, rol) VALUES (?, ?, ?, ?)",
                (id_tenant, "otro@test.com", "hash", "SuperAdmin"),
            )

        # FK tenant_id inexistente
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO usuario (tenant_id, email, password_hash, rol) VALUES (9999, ?, ?, ?)",
                ("nadie@test.com", "hash", "Recepcionista"),
            )
    finally:
        conexion.close()


def test_esquema_001_aplica_check_unicos_y_fk(tmp_path) -> None:
    """CHECK de estado, únicos (tenant_id, nombre) y claves foráneas quedan activos."""
    ruta = tmp_path / "integridad.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Ejemplo')")
        id_tenant = conexion.execute("SELECT id FROM tenant").fetchone()[0]

        # Único provisorio (tenant_id, nombre) en profesional (design D4).
        conexion.execute(
            "INSERT INTO profesional (tenant_id, nombre) VALUES (?, 'Dr. Ejemplo')",
            (id_tenant,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO profesional (tenant_id, nombre) VALUES (?, 'Dr. Ejemplo')",
                (id_tenant,),
            )

        conexion.execute(
            "INSERT INTO sillon (tenant_id, nombre) VALUES (?, 'Sillón 1')",
            (id_tenant,),
        )
        conexion.execute(
            "INSERT INTO paciente (tenant_id, nombre) VALUES (?, 'Paciente Ficticio')",
            (id_tenant,),
        )
        id_profesional = conexion.execute(
            "SELECT id FROM profesional WHERE nombre = 'Dr. Ejemplo'"
        ).fetchone()[0]
        id_sillon = conexion.execute(
            "SELECT id FROM sillon WHERE nombre = 'Sillón 1'"
        ).fetchone()[0]
        id_paciente = conexion.execute(
            "SELECT id FROM paciente WHERE nombre = 'Paciente Ficticio'"
        ).fetchone()[0]
        conexion.commit()

        # CHECK (estado IN (...)): un estado fuera del enum se rechaza.
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO turno (tenant_id, paciente_id, profesional_id, sillon_id,"
                " fecha_hora_inicio, fecha_hora_fin, estado)"
                " VALUES (?, ?, ?, ?, '2026-11-01 10:00', '2026-11-01 10:30', 'VOLANDO')",
                (id_tenant, id_paciente, id_profesional, id_sillon),
            )

        # Integridad referencial: un profesional inexistente rompe el alta.
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO turno (tenant_id, paciente_id, profesional_id, sillon_id,"
                " fecha_hora_inicio, fecha_hora_fin, estado)"
                " VALUES (?, ?, 999999, ?, '2026-11-01 10:00', '2026-11-01 10:30',"
                " 'CONFIRMADO')",
                (id_tenant, id_paciente, id_sillon),
            )
    finally:
        conexion.close()


def test_esquema_003_recursos_columnas_y_defaults(tmp_path) -> None:
    """La migración 003 añade columnas a profesional y sillon con defaults correctos."""
    ruta = tmp_path / "recursos_esquema.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        # Columnas de profesional
        info_prof = {
            fila[1]: fila[4]  # name: dflt_value
            for fila in conexion.execute("PRAGMA table_info(profesional)")
        }
        assert "matricula" in info_prof
        assert "especialidad" in info_prof
        assert "activo" in info_prof
        assert str(info_prof["activo"]) == "1"

        # Columnas de sillon
        info_sillon = {
            fila[1]: fila[4]
            for fila in conexion.execute("PRAGMA table_info(sillon)")
        }
        assert "equipamiento" in info_sillon
        assert "activo" in info_sillon
        assert str(info_sillon["activo"]) == "1"

        # Inserción sin columnas nuevas adopta defaults
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Recursos')")
        id_tenant = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Recursos'").fetchone()[0]
        conexion.execute(
            "INSERT INTO profesional (tenant_id, nombre) VALUES (?, 'Dr. Default')",
            (id_tenant,),
        )
        conexion.execute(
            "INSERT INTO sillon (tenant_id, nombre) VALUES (?, 'Sillón Default')",
            (id_tenant,),
        )
        conexion.commit()

        fila_p = conexion.execute("SELECT matricula, especialidad, activo FROM profesional WHERE nombre = 'Dr. Default'").fetchone()
        assert fila_p[0] is None
        assert fila_p[1] is None
        assert fila_p[2] == 1

        fila_s = conexion.execute("SELECT equipamiento, activo FROM sillon WHERE nombre = 'Sillón Default'").fetchone()
        assert fila_s[0] is None
        assert fila_s[1] == 1
    finally:
        conexion.close()


def test_esquema_004_paciente_restricciones(tmp_path) -> None:
    """La migración 004 añade telefono y UNIQUE(tenant_id, dni) a la tabla paciente."""
    ruta = tmp_path / "paciente_integridad.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Pacientes')")
        id_tenant = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Pacientes'").fetchone()[0]

        # Inserción con columna telefono
        conexion.execute(
            "INSERT INTO paciente (tenant_id, nombre, dni, telefono) VALUES (?, 'Paciente 1', '10000001', '+54 11 4000-0001')",
            (id_tenant,),
        )
        conexion.commit()

        # UNIQUE(tenant_id, dni) rechaza duplicado en el mismo tenant
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute(
                "INSERT INTO paciente (tenant_id, nombre, dni, telefono) VALUES (?, 'Paciente 2', '10000001', '+54 11 4000-0002')",
                (id_tenant,),
            )

        # Mismo DNI en otro tenant es admitido
        conexion.execute("INSERT INTO tenant (nombre) VALUES ('Clínica Otra')")
        id_tenant2 = conexion.execute("SELECT id FROM tenant WHERE nombre = 'Clínica Otra'").fetchone()[0]
        conexion.execute(
            "INSERT INTO paciente (tenant_id, nombre, dni, telefono) VALUES (?, 'Paciente 1', '10000001', '+54 11 4000-0001')",
            (id_tenant2,),
        )
        conexion.commit()
    finally:
        conexion.close()


