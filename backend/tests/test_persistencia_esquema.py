"""Pruebas del esquema de persistencia (task 1.2, design D4).

Base SQLite REAL en archivo temporal por test: nunca se mockea la base
(regla dura 5 / D-04). Datos siempre sintéticos (regla dura 3 / RN-06).
"""

import sqlite3

import pytest

from src.infrastructure.database import abrir_conexion, migrar


def test_esquema_001_crea_las_cinco_tablas(tmp_path) -> None:
    """La migración 001 crea las cinco tablas y sus índices, y es idempotente."""
    ruta = tmp_path / "esquema.db"
    conexion = abrir_conexion(str(ruta))
    try:
        assert migrar(conexion) == ["001_init.sql"]
        # Segunda corrida: la migración ya registrada no se vuelve a aplicar.
        assert migrar(conexion) == []

        tablas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"tenant", "profesional", "sillon", "paciente", "turno"} <= tablas
        assert "schema_migrations" in tablas

        aplicadas = conexion.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()
        assert [fila[0] for fila in aplicadas] == ["001_init.sql"]

        # Índice de solapamiento (tenant_id, fecha_hora_inicio) — design D4.
        columnas_indice = [
            fila[2]
            for fila in conexion.execute(
                "PRAGMA index_info(idx_turno_tenant_inicio)"
            )
        ]
        assert columnas_indice == ["tenant_id", "fecha_hora_inicio"]
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
