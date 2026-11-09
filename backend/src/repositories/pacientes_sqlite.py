"""Adaptador de persistencia de pacientes en SQLite con aislamiento por tenant (C-07, design D2/D4)."""

from dataclasses import replace
import sqlite3

from src.api.errores import ErrorPacienteDuplicado
from src.domain.models import Paciente


class RepositorioPacientesSqlite:
    """Acceso a datos de la tabla paciente en SQLite acotado al tenant (RN-05)."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion

    def _fila_a_paciente(self, fila: sqlite3.Row | tuple) -> Paciente:
        p_id = fila["id"] if isinstance(fila, sqlite3.Row) else fila[0]
        t_id = fila["tenant_id"] if isinstance(fila, sqlite3.Row) else fila[1]
        dni = fila["dni"] if isinstance(fila, sqlite3.Row) else fila[2]
        nombre = fila["nombre"] if isinstance(fila, sqlite3.Row) else fila[3]
        telefono = fila["telefono"] if isinstance(fila, sqlite3.Row) else fila[4]
        return Paciente(
            id=p_id,
            tenant_id=t_id,
            dni=dni,
            nombre=nombre,
            telefono=telefono or "",
        )

    def crear(self, paciente: Paciente) -> Paciente:
        """Persiste un paciente nuevo dentro del tenant.

        Si ya existe un registro con el mismo (tenant_id, dni), lanza ErrorPacienteDuplicado.
        """
        try:
            cursor = self._conexion.execute(
                """
                INSERT INTO paciente (tenant_id, nombre, dni, telefono)
                VALUES (?, ?, ?, ?)
                """,
                (paciente.tenant_id, paciente.nombre, paciente.dni, paciente.telefono),
            )
            self._conexion.commit()
            nuevo_id = cursor.lastrowid
            return replace(paciente, id=nuevo_id)
        except sqlite3.IntegrityError as exc:
            self._conexion.rollback()
            raise ErrorPacienteDuplicado(
                "Ya existe un paciente con el DNI indicado en este centro"
            ) from exc

    def buscar_por_id(self, id: int, tenant_id: int) -> Paciente | None:
        """Recupera un paciente por su id dentro del tenant o None si no existe."""
        fila = self._conexion.execute(
            """
            SELECT id, tenant_id, dni, nombre, telefono
              FROM paciente
             WHERE id = ? AND tenant_id = ?
            """,
            (id, tenant_id),
        ).fetchone()
        if fila is None:
            return None
        return self._fila_a_paciente(fila)

    def buscar_por_dni(self, dni: str, tenant_id: int) -> Paciente | None:
        """Recupera un paciente por su dni dentro del tenant o None si no existe."""
        fila = self._conexion.execute(
            """
            SELECT id, tenant_id, dni, nombre, telefono
              FROM paciente
             WHERE dni = ? AND tenant_id = ?
            """,
            (dni, tenant_id),
        ).fetchone()
        if fila is None:
            return None
        return self._fila_a_paciente(fila)

    def listar(
        self,
        tenant_id: int,
        filtro_nombre: str | None = None,
        filtro_dni: str | None = None,
    ) -> list[Paciente]:
        """Recupera los pacientes del tenant con filtros opcionales ordenados por id."""
        clausulas = ["tenant_id = ?"]
        parametros: list[object] = [tenant_id]

        if filtro_dni is not None:
            clausulas.append("dni = ?")
            parametros.append(filtro_dni)

        if filtro_nombre is not None:
            clausulas.append("nombre LIKE ?")
            parametros.append(f"%{filtro_nombre}%")

        where_sql = " AND ".join(clausulas)
        sql = f"""
            SELECT id, tenant_id, dni, nombre, telefono
              FROM paciente
             WHERE {where_sql}
             ORDER BY id
        """
        filas = self._conexion.execute(sql, tuple(parametros)).fetchall()
        return [self._fila_a_paciente(fila) for fila in filas]
