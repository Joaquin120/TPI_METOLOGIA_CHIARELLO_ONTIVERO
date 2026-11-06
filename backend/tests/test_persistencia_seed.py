"""Pruebas de la semilla inicial de datos (task 1.4, design D6, RN-06).

Base SQLite REAL en archivo temporal por test: nunca se mockea la base
(regla dura 5 / D-04). Datos siempre sintéticos (regla dura 3 / RN-06).
"""

from src.infrastructure.database import abrir_conexion, migrar
from src.infrastructure.seed import (
    PROFESIONALES_DEFECTO,
    SILLONES_DEFECTO,
    TENANT_DEFECTO,
    USUARIOS_DEFECTO,
    sembrar_datos_iniciales,
)


def test_seed_carga_un_tenant_dos_profesionales_y_dos_sillones(tmp_path) -> None:
    """La semilla crea exactamente 1 tenant, 2 profesionales, 2 sillones y 3 usuarios sintéticos."""
    ruta = tmp_path / "seed_inicial.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        sembrar_datos_iniciales(conexion)

        tenants = conexion.execute("SELECT nombre FROM tenant").fetchall()
        assert len(tenants) == 1
        assert tenants[0][0] == TENANT_DEFECTO

        profesionales = [
            fila[0]
            for fila in conexion.execute(
                "SELECT nombre FROM profesional ORDER BY id"
            ).fetchall()
        ]
        assert tuple(profesionales) == PROFESIONALES_DEFECTO

        sillones = [
            fila[0]
            for fila in conexion.execute(
                "SELECT nombre FROM sillon ORDER BY id"
            ).fetchall()
        ]
        assert tuple(sillones) == SILLONES_DEFECTO

        usuarios = conexion.execute(
            "SELECT email, rol, activo FROM usuario ORDER BY email"
        ).fetchall()
        assert len(usuarios) == 3
        emails = [u[0] for u in usuarios]
        assert "admin@ejemplo.com" in emails
        assert "recepcion@ejemplo.com" in emails
        assert "dr.ejemplo@ejemplo.com" in emails
    finally:
        conexion.close()


def test_seed_es_idempotente(tmp_path) -> None:
    """Ejecutar la semilla múltiples veces no duplica registros ni genera errores."""
    ruta = tmp_path / "seed_idempotente.db"
    conexion = abrir_conexion(str(ruta))
    try:
        migrar(conexion)
        sembrar_datos_iniciales(conexion)
        sembrar_datos_iniciales(conexion)
        sembrar_datos_iniciales(conexion)

        cantidad_tenants = conexion.execute("SELECT count(*) FROM tenant").fetchone()[0]
        cantidad_prof = conexion.execute("SELECT count(*) FROM profesional").fetchone()[0]
        cantidad_sillones = conexion.execute("SELECT count(*) FROM sillon").fetchone()[0]
        cantidad_usuarios = conexion.execute("SELECT count(*) FROM usuario").fetchone()[0]

        assert cantidad_tenants == 1
        assert cantidad_prof == 2
        assert cantidad_sillones == 2
        assert cantidad_usuarios == 3
    finally:
        conexion.close()
