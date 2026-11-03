"""Semilla sintética de datos iniciales (task 1.4, design D6, RN-06)."""

import sqlite3

TENANT_DEFECTO = "Clínica Ejemplo"
PROFESIONALES_DEFECTO = ("Dr. Ejemplo", "Dra. Ejemplo")
SILLONES_DEFECTO = ("Sillón 1", "Sillón 2")


def sembrar_datos_iniciales(conexion: sqlite3.Connection) -> None:
    """Siembra 1 tenant, 2 profesionales y 2 sillones de forma idempotente.

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

    conexion.commit()
