"""Pruebas de configuración de la ruta de la base (task 1.3, design D7, D-05).

La ruta sale exclusivamente del entorno: sin secretos ni rutas sensibles
fijas en el código (regla dura 6). Base SQLite real, nunca mockeada.
"""

import sqlite3
from pathlib import Path

from src.infrastructure.config import RUTA_BASE_DEFECTO, ruta_base_de_datos
from src.infrastructure.database import abrir_conexion, migrar


def test_ruta_de_la_base_sale_del_entorno(tmp_path, monkeypatch) -> None:
    """TURNO_DB_PATH decide la base: ese archivo es el que se usa y persiste."""
    ruta = tmp_path / "entorno.db"
    monkeypatch.setenv("TURNO_DB_PATH", str(ruta))

    conexion = abrir_conexion()  # sin ruta explícita: resuelve desde el entorno
    try:
        migrar(conexion)
    finally:
        conexion.close()

    assert ruta.exists()
    with sqlite3.connect(str(ruta)) as cruda:
        tablas = {
            fila[0]
            for fila in cruda.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "turno" in tablas


def test_ruta_por_defecto_es_relativa_y_documentada(monkeypatch) -> None:
    """Sin TURNO_DB_PATH se usa el default documentado: relativo, sin secretos (D-05)."""
    monkeypatch.delenv("TURNO_DB_PATH", raising=False)

    assert ruta_base_de_datos() == RUTA_BASE_DEFECTO
    assert RUTA_BASE_DEFECTO == "turnos.db"
    assert not Path(RUTA_BASE_DEFECTO).is_absolute()  # ningún literal de ruta sensible
