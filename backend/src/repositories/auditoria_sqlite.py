"""Adaptador de persistencia de eventos de auditoría en SQLite con aislamiento por tenant (C-09, RN-05)."""

from dataclasses import replace
import sqlite3

from src.domain.models import RegistroAuditoria


class RepositorioAuditoriaSqlite:
    """Acceso a datos de la bitácora de auditoría en SQLite acotada al tenant."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion

    def _fila_a_registro(self, fila: sqlite3.Row | tuple) -> RegistroAuditoria:
        r_id = fila["id"] if isinstance(fila, sqlite3.Row) else fila[0]
        t_id = fila["tenant_id"] if isinstance(fila, sqlite3.Row) else fila[1]
        u_id = fila["usuario_id"] if isinstance(fila, sqlite3.Row) else fila[2]
        accion = fila["accion"] if isinstance(fila, sqlite3.Row) else fila[3]
        entidad = fila["entidad"] if isinstance(fila, sqlite3.Row) else fila[4]
        entidad_id = fila["entidad_id"] if isinstance(fila, sqlite3.Row) else fila[5]
        detalle = fila["detalle"] if isinstance(fila, sqlite3.Row) else fila[6]
        fecha_hora = fila["fecha_hora"] if isinstance(fila, sqlite3.Row) else fila[7]
        return RegistroAuditoria(
            id=r_id,
            tenant_id=t_id,
            usuario_id=u_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=detalle,
            fecha_hora=fecha_hora,
        )

    def registrar(self, registro: RegistroAuditoria) -> RegistroAuditoria:
        """Persiste un registro de auditoría en el tenant y devuelve el modelo con id asignado."""
        cursor = self._conexion.execute(
            """
            INSERT INTO auditoria (
                tenant_id, usuario_id, accion, entidad, entidad_id, detalle, fecha_hora
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registro.tenant_id,
                registro.usuario_id,
                registro.accion,
                registro.entidad,
                registro.entidad_id,
                registro.detalle,
                registro.fecha_hora,
            ),
        )
        self._conexion.commit()
        return replace(registro, id=cursor.lastrowid)

    def listar(
        self,
        tenant_id: int,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        usuario_id: int | None = None,
        accion: str | None = None,
        entidad: str | None = None,
    ) -> list[RegistroAuditoria]:
        """Consulta los eventos de auditoría acotados al tenant con filtros opcionales."""
        clausulas = ["tenant_id = ?"]
        parametros: list[object] = [tenant_id]

        if fecha_desde is not None:
            clausulas.append("fecha_hora >= ?")
            parametros.append(f"{fecha_desde} 00:00")

        if fecha_hasta is not None:
            clausulas.append("fecha_hora <= ?")
            parametros.append(f"{fecha_hasta} 23:59")

        if usuario_id is not None:
            clausulas.append("usuario_id = ?")
            parametros.append(usuario_id)

        if accion is not None:
            clausulas.append("accion = ?")
            parametros.append(accion)

        if entidad is not None:
            clausulas.append("entidad = ?")
            parametros.append(entidad)

        where_sql = " AND ".join(clausulas)
        sql = f"""
            SELECT id, tenant_id, usuario_id, accion, entidad, entidad_id, detalle, fecha_hora
              FROM auditoria
             WHERE {where_sql}
             ORDER BY fecha_hora DESC, id DESC
        """
        filas = self._conexion.execute(sql, tuple(parametros)).fetchall()
        return [self._fila_a_registro(fila) for fila in filas]
