"""Adaptador de persistencia de bloqueos de sillones en SQLite con aislamiento por tenant (C-10, F-12, RN-07)."""

from dataclasses import replace
import sqlite3

from src.domain.models import BloqueoSillon


class RepositorioBloqueosSqlite:
    """Implementa `PuertoBloqueos` contra SQLite real garantizando aislamiento por tenant."""

    def __init__(self, conexion: sqlite3.Connection, tenant_id: int) -> None:
        self._conexion = conexion
        self._tenant_id = tenant_id

    def _fila_a_bloqueo(self, fila: sqlite3.Row | tuple) -> BloqueoSillon:
        b_id = fila["id"] if isinstance(fila, sqlite3.Row) else fila[0]
        t_id = fila["tenant_id"] if isinstance(fila, sqlite3.Row) else fila[1]
        s_id = fila["sillon_id"] if isinstance(fila, sqlite3.Row) else fila[2]
        f_inicio = fila["fecha_hora_inicio"] if isinstance(fila, sqlite3.Row) else fila[3]
        f_fin = fila["fecha_hora_fin"] if isinstance(fila, sqlite3.Row) else fila[4]
        motivo = fila["motivo"] if isinstance(fila, sqlite3.Row) else fila[5]
        creado_por = fila["creado_por"] if isinstance(fila, sqlite3.Row) else fila[6]
        creado_en = fila["creado_en"] if isinstance(fila, sqlite3.Row) else fila[7]

        return BloqueoSillon(
            id=b_id,
            tenant_id=t_id,
            sillon_id=s_id,
            fecha_hora_inicio=f_inicio,
            fecha_hora_fin=f_fin,
            motivo=motivo,
            creado_por=creado_por,
            creado_en=creado_en,
        )

    def guardar(self, bloqueo: BloqueoSillon) -> BloqueoSillon:
        """Persiste un nuevo bloqueo en la tabla `bloqueo_sillon` dentro del tenant."""
        cursor = self._conexion.execute(
            """
            INSERT INTO bloqueo_sillon (
                tenant_id, sillon_id, fecha_hora_inicio, fecha_hora_fin, motivo, creado_por
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                self._tenant_id,
                bloqueo.sillon_id,
                bloqueo.fecha_hora_inicio,
                bloqueo.fecha_hora_fin,
                bloqueo.motivo,
                bloqueo.creado_por,
            ),
        )
        self._conexion.commit()
        nuevo_id = cursor.lastrowid
        fila = self._conexion.execute(
            "SELECT creado_en FROM bloqueo_sillon WHERE id = ?", (nuevo_id,)
        ).fetchone()
        creado_en = fila[0] if fila is not None else None
        return replace(
            bloqueo,
            id=nuevo_id,
            tenant_id=self._tenant_id,
            creado_en=creado_en,
        )

    def buscar_bloqueos_solapados(
        self,
        sillon_id: int,
        fecha_hora_inicio: str,
        fecha_hora_fin: str,
        excluir_bloqueo_id: int | None = None,
    ) -> list[BloqueoSillon]:
        """Consulta bloqueos solapados en intervalos semiabiertos [inicio, fin) (A_inicio < B_fin AND A_fin > B_inicio)."""
        sql = """
            SELECT id, tenant_id, sillon_id, fecha_hora_inicio, fecha_hora_fin, motivo, creado_por, creado_en
              FROM bloqueo_sillon
             WHERE tenant_id = ?
               AND sillon_id = ?
               AND fecha_hora_inicio < ?
               AND fecha_hora_fin > ?
               AND (? IS NULL OR id != ?)
             ORDER BY fecha_hora_inicio, id
        """
        parametros = (
            self._tenant_id,
            sillon_id,
            fecha_hora_fin,
            fecha_hora_inicio,
            excluir_bloqueo_id,
            excluir_bloqueo_id,
        )
        filas = self._conexion.execute(sql, parametros).fetchall()
        return [self._fila_a_bloqueo(f) for f in filas]

    def listar(
        self,
        sillon_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> list[BloqueoSillon]:
        """Lista los bloqueos del tenant aplicando filtros opcionales."""
        clausulas = ["tenant_id = ?"]
        parametros: list[object] = [self._tenant_id]

        if sillon_id is not None:
            clausulas.append("sillon_id = ?")
            parametros.append(sillon_id)

        if fecha_desde is not None:
            clausulas.append("fecha_hora_fin >= ?")
            parametros.append(f"{fecha_desde} 00:00")

        if fecha_hasta is not None:
            clausulas.append("fecha_hora_inicio <= ?")
            parametros.append(f"{fecha_hasta} 23:59")

        where_sql = " AND ".join(clausulas)
        sql = f"""
            SELECT id, tenant_id, sillon_id, fecha_hora_inicio, fecha_hora_fin, motivo, creado_por, creado_en
              FROM bloqueo_sillon
             WHERE {where_sql}
             ORDER BY fecha_hora_inicio, id
        """
        filas = self._conexion.execute(sql, tuple(parametros)).fetchall()
        return [self._fila_a_bloqueo(f) for f in filas]

    def obtener_por_id(self, bloqueo_id: int) -> BloqueoSillon | None:
        """Recupera un bloqueo por su identificador único dentro del tenant."""
        fila = self._conexion.execute(
            """
            SELECT id, tenant_id, sillon_id, fecha_hora_inicio, fecha_hora_fin, motivo, creado_por, creado_en
              FROM bloqueo_sillon
             WHERE tenant_id = ? AND id = ?
            """,
            (self._tenant_id, bloqueo_id),
        ).fetchone()
        if fila is None:
            return None
        return self._fila_a_bloqueo(fila)

    def eliminar(self, bloqueo_id: int) -> bool:
        """Elimina un bloqueo del tenant. Retorna True si fue eliminado, False si no existía."""
        cursor = self._conexion.execute(
            "DELETE FROM bloqueo_sillon WHERE tenant_id = ? AND id = ?",
            (self._tenant_id, bloqueo_id),
        )
        self._conexion.commit()
        return cursor.rowcount > 0
