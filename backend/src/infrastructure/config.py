"""Configuración de la aplicación por variables de entorno (design D7, D-05).

Regla dura 6: sin secretos ni rutas sensibles en el repo. La única fuente es
`TURNO_DB_PATH`; no se leen archivos `.env` (auto-carga opcional futura, ver
Open Questions del design).
"""

import os

# Default documentado para desarrollo: base relativa al directorio de trabajo
# (se descarta del repo vía `.gitignore`, task 1.5). Nunca una ruta absoluta.
RUTA_BASE_DEFECTO = "turnos.db"


def ruta_base_de_datos() -> str:
    """Ruta de la base: `TURNO_DB_PATH` del entorno o `RUTA_BASE_DEFECTO`.

    Se lee en cada llamada para que las pruebas puedan apuntar la variable a
    un archivo temporal de `tmp_path` (design D7 / D8).
    """
    return os.environ.get("TURNO_DB_PATH", RUTA_BASE_DEFECTO)
