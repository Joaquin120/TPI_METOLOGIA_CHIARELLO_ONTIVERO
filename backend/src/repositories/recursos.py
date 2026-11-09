"""Repositorios de recursos auxiliares con aislamiento por tenant (design D6, RN-05)."""

import sqlite3

from src.domain.models import Profesional, Sillon


class RepositorioProfesionales:
    """Acceso a datos de profesionales dentro de un tenant."""

    def __init__(self, conexion: sqlite3.Connection, tenant_id: int) -> None:
        self._conexion = conexion
        self._tenant_id = tenant_id

    def resolver_id(self, nombre: str) -> int:
        """Resuelve el id de un profesional por nombre dentro del tenant (crea si no existe)."""
        self._conexion.execute(
            "INSERT OR IGNORE INTO profesional (tenant_id, nombre) VALUES (?, ?)",
            (self._tenant_id, nombre),
        )
        fila = self._conexion.execute(
            "SELECT id FROM profesional WHERE tenant_id = ? AND nombre = ?",
            (self._tenant_id, nombre),
        ).fetchone()
        return fila[0] if isinstance(fila, (tuple, list)) else fila["id"]

    def obtener_por_id(self, id_: int) -> Profesional | None:
        """Obtiene el modelo Profesional por su id dentro del tenant."""
        fila = self._conexion.execute(
            "SELECT id, nombre, matricula, especialidad, activo FROM profesional WHERE tenant_id = ? AND id = ?",
            (self._tenant_id, id_),
        ).fetchone()
        if fila is None:
            return None
        return Profesional(
            id=fila[0] if isinstance(fila, (tuple, list)) else fila["id"],
            nombre=fila[1] if isinstance(fila, (tuple, list)) else fila["nombre"],
            matricula=fila[2] if isinstance(fila, (tuple, list)) else fila["matricula"],
            especialidad=fila[3] if isinstance(fila, (tuple, list)) else fila["especialidad"],
            activo=bool(fila[4] if isinstance(fila, (tuple, list)) else fila["activo"]),
        )

    def listar(self, solo_activos: bool = True) -> list[Profesional]:
        """Lista los profesionales del tenant, con filtro opcional por activo."""
        consulta = (
            "SELECT id, nombre, matricula, especialidad, activo FROM profesional WHERE tenant_id = ? AND activo = 1 ORDER BY id"
            if solo_activos
            else "SELECT id, nombre, matricula, especialidad, activo FROM profesional WHERE tenant_id = ? ORDER BY id"
        )
        filas = self._conexion.execute(consulta, (self._tenant_id,)).fetchall()
        return [
            Profesional(
                id=fila[0] if isinstance(fila, (tuple, list)) else fila["id"],
                nombre=fila[1] if isinstance(fila, (tuple, list)) else fila["nombre"],
                matricula=fila[2] if isinstance(fila, (tuple, list)) else fila["matricula"],
                especialidad=fila[3] if isinstance(fila, (tuple, list)) else fila["especialidad"],
                activo=bool(fila[4] if isinstance(fila, (tuple, list)) else fila["activo"]),
            )
            for fila in filas
        ]


class RepositorioSillones:
    """Acceso a datos de sillones dentro de un tenant."""

    def __init__(self, conexion: sqlite3.Connection, tenant_id: int) -> None:
        self._conexion = conexion
        self._tenant_id = tenant_id

    def resolver_id(self, nombre: str) -> int:
        """Resuelve el id de un sillón por nombre dentro del tenant (crea si no existe)."""
        self._conexion.execute(
            "INSERT OR IGNORE INTO sillon (tenant_id, nombre) VALUES (?, ?)",
            (self._tenant_id, nombre),
        )
        fila = self._conexion.execute(
            "SELECT id FROM sillon WHERE tenant_id = ? AND nombre = ?",
            (self._tenant_id, nombre),
        ).fetchone()
        return fila[0] if isinstance(fila, (tuple, list)) else fila["id"]

    def obtener_por_id(self, id_: int) -> Sillon | None:
        """Obtiene el modelo Sillon por su id dentro del tenant."""
        fila = self._conexion.execute(
            "SELECT id, nombre, equipamiento, activo FROM sillon WHERE tenant_id = ? AND id = ?",
            (self._tenant_id, id_),
        ).fetchone()
        if fila is None:
            return None
        return Sillon(
            id=fila[0] if isinstance(fila, (tuple, list)) else fila["id"],
            nombre=fila[1] if isinstance(fila, (tuple, list)) else fila["nombre"],
            equipamiento=fila[2] if isinstance(fila, (tuple, list)) else fila["equipamiento"],
            activo=bool(fila[3] if isinstance(fila, (tuple, list)) else fila["activo"]),
        )

    def listar(self, solo_activos: bool = True) -> list[Sillon]:
        """Lista los sillones del tenant, con filtro opcional por activo."""
        consulta = (
            "SELECT id, nombre, equipamiento, activo FROM sillon WHERE tenant_id = ? AND activo = 1 ORDER BY id"
            if solo_activos
            else "SELECT id, nombre, equipamiento, activo FROM sillon WHERE tenant_id = ? ORDER BY id"
        )
        filas = self._conexion.execute(consulta, (self._tenant_id,)).fetchall()
        return [
            Sillon(
                id=fila[0] if isinstance(fila, (tuple, list)) else fila["id"],
                nombre=fila[1] if isinstance(fila, (tuple, list)) else fila["nombre"],
                equipamiento=fila[2] if isinstance(fila, (tuple, list)) else fila["equipamiento"],
                activo=bool(fila[3] if isinstance(fila, (tuple, list)) else fila["activo"]),
            )
            for fila in filas
        ]


class RepositorioPacientes:
    """Acceso a datos y upsert de pacientes dentro de un tenant."""

    def __init__(self, conexion: sqlite3.Connection, tenant_id: int) -> None:
        self._conexion = conexion
        self._tenant_id = tenant_id

    def resolver_id(self, nombre: str, dni: str | None = None) -> int:
        """Upsert de paciente por nombre dentro del tenant y devuelve su id."""
        self._conexion.execute(
            "INSERT OR IGNORE INTO paciente (tenant_id, nombre, dni) VALUES (?, ?, ?)",
            (self._tenant_id, nombre, dni),
        )
        fila = self._conexion.execute(
            "SELECT id FROM paciente WHERE tenant_id = ? AND nombre = ?",
            (self._tenant_id, nombre),
        ).fetchone()
        return fila[0] if isinstance(fila, (tuple, list)) else fila["id"]

    def obtener_nombre_por_id(self, id_: int) -> str | None:
        """Obtiene el nombre del paciente por id dentro del tenant."""
        fila = self._conexion.execute(
            "SELECT nombre FROM paciente WHERE tenant_id = ? AND id = ?",
            (self._tenant_id, id_),
        ).fetchone()
        if fila is None:
            return None
        return fila[0] if isinstance(fila, (tuple, list)) else fila["nombre"]
