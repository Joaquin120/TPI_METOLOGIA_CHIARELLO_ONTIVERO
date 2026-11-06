"""Semilla sintética de datos iniciales (task 1.4, design D6, RN-06)."""

import sqlite3

from src.api.seguridad import hashear_password

TENANT_DEFECTO = "Clínica Ejemplo"
PROFESIONALES_DEFECTO = ("Dr. Ejemplo", "Dra. Ejemplo")
SILLONES_DEFECTO = ("Sillón 1", "Sillón 2")
PASSWORD_DEFECTO = "secreto123"

USUARIOS_DEFECTO = (
    ("admin@ejemplo.com", "Administrador", None),
    ("recepcion@ejemplo.com", "Recepcionista", None),
    ("dr.ejemplo@ejemplo.com", "Profesional", "Dr. Ejemplo"),
)


def sembrar_datos_iniciales(conexion: sqlite3.Connection) -> None:
    """Siembra 1 tenant, 2 profesionales, 2 sillones y 3 usuarios de forma idempotente.

    Regla dura 3 / RN-06: utiliza únicamente datos sintéticos.
    """
    conexion.execute(
        "INSERT OR IGNORE INTO tenant (nombre) VALUES (?)",
        (TENANT_DEFECTO,),
    )
    fila_tenant = conexion.execute(
        "SELECT id FROM tenant WHERE nombre = ?",
        (TENANT_DEFECTO,),
    ).fetchone()
    tenant_id = fila_tenant[0] if isinstance(fila_tenant, (tuple, list)) else fila_tenant["id"]

    for prof in PROFESIONALES_DEFECTO:
        conexion.execute(
            "INSERT OR IGNORE INTO profesional (tenant_id, nombre) VALUES (?, ?)",
            (tenant_id, prof),
        )

    for sil in SILLONES_DEFECTO:
        conexion.execute(
            "INSERT OR IGNORE INTO sillon (tenant_id, nombre) VALUES (?, ?)",
            (tenant_id, sil),
        )

    hash_password = hashear_password(PASSWORD_DEFECTO)
    for email, rol, nombre_prof in USUARIOS_DEFECTO:
        prof_id = None
        if nombre_prof is not None:
            fila_prof = conexion.execute(
                "SELECT id FROM profesional WHERE tenant_id = ? AND nombre = ?",
                (tenant_id, nombre_prof),
            ).fetchone()
            if fila_prof is not None:
                prof_id = fila_prof[0] if isinstance(fila_prof, (tuple, list)) else fila_prof["id"]

        conexion.execute(
            """
            INSERT OR IGNORE INTO usuario (tenant_id, email, password_hash, rol, profesional_id, activo)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (tenant_id, email, hash_password, rol, prof_id),
        )

    conexion.commit()
