"""Adaptador de persistencia analítica de métricas en SQLite con aislamiento por tenant (C-08, RN-05)."""

import sqlite3
from typing import Any


class RepositorioMetricasSqlite:
    """Consultas analíticas agregadas de turnos y recursos sobre SQLite real."""

    def __init__(self, conexion: sqlite3.Connection) -> None:
        self._conexion = conexion

    def obtener_metricas_turnos(
        self,
        tenant_id: int,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> dict[str, Any]:
        """Calcula métricas agregadas de turnos acotadas incondicionalmente por tenant_id."""
        clausulas = ["tenant_id = ?"]
        parametros: list[Any] = [tenant_id]

        if fecha_desde is not None:
            clausulas.append("fecha_hora_inicio >= ?")
            parametros.append(f"{fecha_desde} 00:00")

        if fecha_hasta is not None:
            clausulas.append("fecha_hora_inicio <= ?")
            parametros.append(f"{fecha_hasta} 23:59")

        where_sql = " AND ".join(clausulas)
        sql = f"""
            SELECT estado, COUNT(*) as cantidad
              FROM turno
             WHERE {where_sql}
             GROUP BY estado
        """
        filas = self._conexion.execute(sql, tuple(parametros)).fetchall()

        por_estado: dict[str, int] = {
            "PENDIENTE": 0,
            "CONFIRMADO": 0,
            "CANCELADO": 0,
            "COMPLETADO": 0,
        }
        for fila in filas:
            estado = fila["estado"] if isinstance(fila, sqlite3.Row) else fila[0]
            cant = fila["cantidad"] if isinstance(fila, sqlite3.Row) else fila[1]
            por_estado[estado] = cant

        total = sum(por_estado.values())
        cancelados = por_estado["CANCELADO"]
        tasa_cancelacion = (
            round((cancelados / total) * 100.0, 2) if total > 0 else 0.0
        )

        return {
            "total": total,
            "por_estado": por_estado,
            "tasa_cancelacion": tasa_cancelacion,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        }

    def obtener_metricas_recursos(
        self,
        tenant_id: int,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> dict[str, Any]:
        """Calcula distribución de turnos por profesional y sillón acotados al tenant_id."""
        clausulas_turno_prof: list[str] = ["t.tenant_id = p.tenant_id"]
        parametros_turno: list[Any] = []

        if fecha_desde is not None:
            clausulas_turno_prof.append("t.fecha_hora_inicio >= ?")
            parametros_turno.append(f"{fecha_desde} 00:00")

        if fecha_hasta is not None:
            clausulas_turno_prof.append("t.fecha_hora_inicio <= ?")
            parametros_turno.append(f"{fecha_hasta} 23:59")

        join_cond_prof = " AND ".join(clausulas_turno_prof)
        sql_prof = f"""
            SELECT p.id as profesional_id, p.nombre, COUNT(t.id) as total_turnos
              FROM profesional p
              LEFT JOIN turno t ON t.profesional_id = p.id AND {join_cond_prof}
             WHERE p.tenant_id = ?
             GROUP BY p.id, p.nombre
             ORDER BY p.id
        """
        filas_prof = self._conexion.execute(
            sql_prof, (*parametros_turno, tenant_id)
        ).fetchall()

        profesionales = [
            {
                "profesional_id": fila["profesional_id"]
                if isinstance(fila, sqlite3.Row)
                else fila[0],
                "nombre": fila["nombre"]
                if isinstance(fila, sqlite3.Row)
                else fila[1],
                "total_turnos": fila["total_turnos"]
                if isinstance(fila, sqlite3.Row)
                else fila[2],
            }
            for fila in filas_prof
        ]

        clausulas_turno_sil: list[str] = ["t.tenant_id = s.tenant_id"]
        if fecha_desde is not None:
            clausulas_turno_sil.append("t.fecha_hora_inicio >= ?")
        if fecha_hasta is not None:
            clausulas_turno_sil.append("t.fecha_hora_inicio <= ?")

        join_cond_sil = " AND ".join(clausulas_turno_sil)
        sql_sil = f"""
            SELECT s.id as sillon_id, s.nombre, COUNT(t.id) as total_turnos
              FROM sillon s
              LEFT JOIN turno t ON t.sillon_id = s.id AND {join_cond_sil}
             WHERE s.tenant_id = ?
             GROUP BY s.id, s.nombre
             ORDER BY s.id
        """
        filas_sil = self._conexion.execute(
            sql_sil, (*parametros_turno, tenant_id)
        ).fetchall()

        sillones = [
            {
                "sillon_id": fila["sillon_id"]
                if isinstance(fila, sqlite3.Row)
                else fila[0],
                "nombre": fila["nombre"]
                if isinstance(fila, sqlite3.Row)
                else fila[1],
                "total_turnos": fila["total_turnos"]
                if isinstance(fila, sqlite3.Row)
                else fila[2],
            }
            for fila in filas_sil
        ]

        return {
            "profesionales": profesionales,
            "sillones": sillones,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        }
