"""Adaptador SQLite para la persistencia de usuarios (C-04, task 1.3)."""

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class Usuario:
    """Entidad de persistencia que representa un usuario del sistema."""

    id: int
    tenant_id: int
    email: str
    password_hash: str
    rol: str
    profesional_id: int | None = None
    activo: bool = True


class RepositorioUsuariosSqlite:
    """Acceso a datos de la tabla usuario en SQLite."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._con = conexion

    def crear(
        self,
        tenant_id: int,
        email: str,
        password_hash: str,
        rol: str,
        profesional_id: int | None = None,
        activo: bool = True,
    ) -> Usuario:
        cursor = self._con.execute(
            """
            INSERT INTO usuario (tenant_id, email, password_hash, rol, profesional_id, activo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (tenant_id, email, password_hash, rol, profesional_id, 1 if activo else 0),
        )
        self._con.commit()
        return Usuario(
            id=cursor.lastrowid,
            tenant_id=tenant_id,
            email=email,
            password_hash=password_hash,
            rol=rol,
            profesional_id=profesional_id,
            activo=activo,
        )

    def buscar_por_email(
        self, email: str, tenant_id: int | None = None
    ) -> Usuario | None:
        if tenant_id is not None:
            fila = self._con.execute(
                """
                SELECT id, tenant_id, email, password_hash, rol, profesional_id, activo
                FROM usuario
                WHERE email = ? AND tenant_id = ?
                """,
                (email, tenant_id),
            ).fetchone()
        else:
            fila = self._con.execute(
                """
                SELECT id, tenant_id, email, password_hash, rol, profesional_id, activo
                FROM usuario
                WHERE email = ?
                """,
                (email,),
            ).fetchone()

        if fila is None:
            return None

        return Usuario(
            id=fila["id"],
            tenant_id=fila["tenant_id"],
            email=fila["email"],
            password_hash=fila["password_hash"],
            rol=fila["rol"],
            profesional_id=fila["profesional_id"],
            activo=bool(fila["activo"]),
        )

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        fila = self._con.execute(
            """
            SELECT id, tenant_id, email, password_hash, rol, profesional_id, activo
            FROM usuario
            WHERE id = ?
            """,
            (usuario_id,),
        ).fetchone()

        if fila is None:
            return None

        return Usuario(
            id=fila["id"],
            tenant_id=fila["tenant_id"],
            email=fila["email"],
            password_hash=fila["password_hash"],
            rol=fila["rol"],
            profesional_id=fila["profesional_id"],
            activo=bool(fila["activo"]),
        )

