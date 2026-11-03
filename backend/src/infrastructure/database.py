"""Conexión a la base y runner de migraciones idempotente (design D4, D-04)."""

import sqlite3
from pathlib import Path

from src.infrastructure.config import ruta_base_de_datos

# Carpeta de scripts .sql; cada archivo se aplica una sola vez y queda
# registrado en `schema_migrations` (runner mínimo, design D4).
MIGRACIONES_DIR = Path(__file__).resolve().parent / "migrations"


def abrir_conexion(ruta: str | Path | None = None) -> sqlite3.Connection:
    """Abre la base en `ruta` con claves foráneas habilitadas.

    Sin `ruta` resuelve el archivo desde `TURNO_DB_PATH` (design D7, D-05).
    Las reposiciones leen columnas por nombre (`sqlite3.Row`): crear siempre
    las conexiones con esta función. `PRAGMA foreign_keys` es por conexión y
    debe ejecutarse fuera de una transacción (se ejecuta justo al abrir).
    """
    destino = ruta_base_de_datos() if ruta is None else ruta
    conexion = sqlite3.connect(str(destino))
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def migrar(conexion: sqlite3.Connection) -> list[str]:
    """Aplica los scripts `.sql` pendientes de `MIGRACIONES_DIR`.

    Idempotente: una versión ya registrada en `schema_migrations` no se vuelve
    a ejecutar (design D4). Devuelve las migraciones aplicadas en esta corrida,
    en orden alfabético.
    """
    conexion.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)"
    )
    aplicadas = {
        fila[0]
        for fila in conexion.execute("SELECT version FROM schema_migrations")
    }
    aplicadas_ahora: list[str] = []
    for archivo in sorted(MIGRACIONES_DIR.glob("*.sql")):
        if archivo.name in aplicadas:
            continue
        conexion.executescript(archivo.read_text(encoding="utf-8"))
        conexion.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (archivo.name,),
        )
        aplicadas_ahora.append(archivo.name)
    conexion.commit()
    return aplicadas_ahora
