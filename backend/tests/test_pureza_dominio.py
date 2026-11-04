"""Guard de pureza del dominio (task 2.1, design D7, `architecture.md` §1/§3).

Verifica de forma automática que `backend/src/domain/` no importa frameworks
HTTP, librerías de validación de presentación, drivers de base de datos ni
módulos de repositorios/infraestructura. El dominio solo puede depender de la
biblioteca estándar y de sí mismo.

Regla dura 1 (spec first) / regla dura 2 (la doble validación vive en el dominio):
la capa API no debe arrastrar dependencias hacia adentro; este test es la red de
seguridad permanente de esa separación.
"""

import ast
from pathlib import Path

# Prefijos prohibidos dentro de `src/domain/` (design D7 / spec "Guard de pureza").
PREFIJOS_PROHIBIDOS: tuple[str, ...] = (
    "fastapi",
    "pydantic",
    "starlette",
    "httpx",
    "sqlite3",
    "sqlalchemy",
    "alembic",
    "src.repositories",
    "src.infrastructure",
    "src.api",
)

DIRECTORIO_DOMINIO = Path(__file__).resolve().parents[1] / "src" / "domain"


def _modulos_importados(fuente: str) -> list[str]:
    """Devuelve los módulos importados por `fuente` usando `ast`.

    Cubre `import x`, `import x as y`, `from x import y` y `from x import y as z`.
    No intenta resolver imports dinámicos (`__import__`, `importlib`): el dominio
    no los usa y el guard es una verificación estática de código fuente.
    """
    arbol = ast.parse(fuente)
    modulos: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.extend(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level:
                # Import relativo: no puede resolver a un prefijo absoluto prohibido.
                continue
            if nodo.module:
                modulos.append(nodo.module)
    return modulos


def _imports_prohibidos(fuente: str) -> list[str]:
    """Devuelve los módulos de `fuente` que coinciden con un prefijo prohibido."""
    hallazgos: list[str] = []
    for modulo in _modulos_importados(fuente):
        for prefijo in PREFIJOS_PROHIBIDOS:
            if modulo == prefijo or modulo.startswith(prefijo + "."):
                hallazgos.append(modulo)
                break
    return hallazgos


# ---------------------------------------------------------------------------
# Triangulación del helper (task 2.1 GREEN/TRIANGULATE)
# ---------------------------------------------------------------------------


def test_helper_no_reporta_una_fuente_limpia() -> None:
    """Una fuente que solo importa dominio/estándar no produce hallazgos."""
    fuente = (
        "import ast\n"
        "from dataclasses import dataclass\n"
        "from src.domain.models import Turno\n"
    )
    assert _imports_prohibidos(fuente) == []


def test_helper_detecta_import_sqlite3() -> None:
    """`import sqlite3` se detecta como violación de pureza."""
    assert _imports_prohibidos("import sqlite3\n") == ["sqlite3"]


def test_helper_detecta_from_import_prohibido_y_submodulo() -> None:
    """Detecta `from src.repositories...` y módulos anidados de un prefijo prohibido."""
    fuente = "from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria\n"
    assert _imports_prohibidos(fuente) == ["src.repositories.turnos_memoria"]
    assert _imports_prohibidos("import fastapi.security\n") == ["fastapi.security"]


# ---------------------------------------------------------------------------
# Guard sobre el código real del dominio
# ---------------------------------------------------------------------------


def test_dominio_real_sin_imports_prohibidos() -> None:
    """Ningún archivo de `src/domain/` importa HTTP, Pydantic, DB, repos o infra."""
    archivos = sorted(DIRECTORIO_DOMINIO.glob("*.py"))
    assert archivos, f"No se encontraron archivos de dominio en {DIRECTORIO_DOMINIO}"

    violaciones: dict[str, list[str]] = {}
    for archivo in archivos:
        hallazgos = _imports_prohibidos(archivo.read_text(encoding="utf-8"))
        if hallazgos:
            violaciones[archivo.name] = hallazgos

    assert violaciones == {}, f"Dominio contaminado: {violaciones}"


def test_services_no_importa_repositorio_en_memoria() -> None:
    """`ServicioTurnos` no conoce `src.repositories.turnos_memoria` (design D2)."""
    fuente = (DIRECTORIO_DOMINIO / "services.py").read_text(encoding="utf-8")
    modulos = _modulos_importados(fuente)
    assert "src.repositories.turnos_memoria" not in modulos
    assert all(not m.startswith("src.repositories") for m in modulos)
