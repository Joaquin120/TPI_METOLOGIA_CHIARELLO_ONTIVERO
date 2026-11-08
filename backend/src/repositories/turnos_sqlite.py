"""Adaptador de persistencia de turnos en SQLite con aislamiento por tenant (design D3/D5/D6)."""

from dataclasses import replace
import sqlite3

from src.domain.models import ESTADOS_ACTIVOS, Profesional, Sillon, Turno
from src.repositories.recursos import (
    RepositorioPacientes,
    RepositorioProfesionales,
    RepositorioSillones,
)


class RepositorioTurnosSqlite:
    """Implementa `PuertoTurnos` contra SQLite real garantizando aislamiento por tenant (RN-05)."""

    def __init__(self, conexion: sqlite3.Connection, tenant_id: int) -> None:
        self._conexion = conexion
        self._tenant_id = tenant_id
        self._repo_profesionales = RepositorioProfesionales(conexion, tenant_id)
        self._repo_sillones = RepositorioSillones(conexion, tenant_id)
        self._repo_pacientes = RepositorioPacientes(conexion, tenant_id)

    def guardar(self, turno: Turno) -> Turno:
        """Persiste un turno nuevo en la tabla `turno` dentro del tenant."""
        paciente_id = self._repo_pacientes.resolver_id(turno.paciente)
        profesional_id = self._repo_profesionales.resolver_id(turno.profesional.nombre)
        sillon_id = self._repo_sillones.resolver_id(turno.sillon.nombre)

        fecha_hora_inicio = f"{turno.fecha} {turno.hora_inicio}"
        fecha_hora_fin = f"{turno.fecha} {turno.hora_fin}"

        cursor = self._conexion.execute(
            """
            INSERT INTO turno (
                tenant_id, paciente_id, profesional_id, sillon_id,
                fecha_hora_inicio, fecha_hora_fin, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._tenant_id,
                paciente_id,
                profesional_id,
                sillon_id,
                fecha_hora_inicio,
                fecha_hora_fin,
                turno.estado,
            ),
        )
        self._conexion.commit()

        nuevo_id = cursor.lastrowid
        return replace(
            turno,
            id=nuevo_id,
            profesional=replace(turno.profesional, id=profesional_id),
            sillon=replace(turno.sillon, id=sillon_id),
        )

    def actualizar(self, turno: Turno) -> Turno:
        """Actualiza el estado de un turno persistido dentro del tenant."""
        if turno.id is not None:
            self._conexion.execute(
                "UPDATE turno SET estado = ? WHERE id = ? AND tenant_id = ?",
                (turno.estado, turno.id, self._tenant_id),
            )
            self._conexion.commit()
            return turno
        else:
            prof_id = self._repo_profesionales.resolver_id(turno.profesional.nombre)
            sil_id = self._repo_sillones.resolver_id(turno.sillon.nombre)
            fecha_hora_inicio = f"{turno.fecha} {turno.hora_inicio}"
            fecha_hora_fin = f"{turno.fecha} {turno.hora_fin}"
            fila = self._conexion.execute(
                """
                SELECT id FROM turno
                 WHERE tenant_id = ?
                   AND profesional_id = ?
                   AND sillon_id = ?
                   AND fecha_hora_inicio = ?
                   AND fecha_hora_fin = ?
                """,
                (self._tenant_id, prof_id, sil_id, fecha_hora_inicio, fecha_hora_fin),
            ).fetchone()
            if fila is not None:
                turno_id = fila[0] if isinstance(fila, (tuple, list)) else fila["id"]
                self._conexion.execute(
                    "UPDATE turno SET estado = ? WHERE id = ? AND tenant_id = ?",
                    (turno.estado, turno_id, self._tenant_id),
                )
                self._conexion.commit()
                return replace(turno, id=turno_id)
            else:
                self._conexion.commit()
                return turno

    def _fila_a_turno(self, fila: sqlite3.Row | tuple) -> Turno:
        """Convierte una fila de la consulta SQL a la entidad Turno."""
        f_inicio = fila["fecha_hora_inicio"] if isinstance(fila, sqlite3.Row) else fila[1]
        f_fin = fila["fecha_hora_fin"] if isinstance(fila, sqlite3.Row) else fila[2]
        estado = fila["estado"] if isinstance(fila, sqlite3.Row) else fila[3]
        prof_id = fila["profesional_id"] if isinstance(fila, sqlite3.Row) else fila[4]
        prof_nom = fila["profesional_nombre"] if isinstance(fila, sqlite3.Row) else fila[5]
        sil_id = fila["sillon_id"] if isinstance(fila, sqlite3.Row) else fila[6]
        sil_nom = fila["sillon_nombre"] if isinstance(fila, sqlite3.Row) else fila[7]
        pac_nom = fila["paciente_nombre"] if isinstance(fila, sqlite3.Row) else fila[8]
        t_id = fila["id"] if isinstance(fila, sqlite3.Row) else fila[0]

        fecha, hora_inicio = f_inicio.split(" ")
        _, hora_fin = f_fin.split(" ")

        return Turno(
            id=t_id,
            profesional=Profesional(nombre=prof_nom, id=prof_id),
            sillon=Sillon(nombre=sil_nom, id=sil_id),
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            paciente=pac_nom,
            estado=estado,
        )

    def obtener_por_id(self, turno_id: int) -> Turno | None:
        """Recupera un turno por su ID dentro del tenant o None si no existe."""
        fila = self._conexion.execute(
            """
            SELECT t.id, t.fecha_hora_inicio, t.fecha_hora_fin, t.estado,
                   p.id AS profesional_id, p.nombre AS profesional_nombre,
                   s.id AS sillon_id, s.nombre AS sillon_nombre,
                   pac.nombre AS paciente_nombre
              FROM turno t
              JOIN profesional p ON t.profesional_id = p.id
              JOIN sillon s ON t.sillon_id = s.id
              JOIN paciente pac ON t.paciente_id = pac.id
             WHERE t.tenant_id = ?
               AND t.id = ?
            """,
            (self._tenant_id, turno_id),
        ).fetchone()
        if fila is None:
            return None
        return self._fila_a_turno(fila)

    def listar(
        self,
        fecha: str | None = None,
        profesional_id: int | None = None,
        sillon_id: int | None = None,
    ) -> list[Turno]:
        """Recupera los turnos del tenant con filtros opcionales ordenados cronológicamente."""
        clausulas = ["t.tenant_id = ?"]
        parametros: list[object] = [self._tenant_id]

        if fecha is not None:
            clausulas.append("t.fecha_hora_inicio LIKE ?")
            parametros.append(f"{fecha}%")

        if profesional_id is not None:
            clausulas.append("t.profesional_id = ?")
            parametros.append(profesional_id)

        if sillon_id is not None:
            clausulas.append("t.sillon_id = ?")
            parametros.append(sillon_id)

        where_sql = " AND ".join(clausulas)
        sql = f"""
            SELECT t.id, t.fecha_hora_inicio, t.fecha_hora_fin, t.estado,
                   p.id AS profesional_id, p.nombre AS profesional_nombre,
                   s.id AS sillon_id, s.nombre AS sillon_nombre,
                   pac.nombre AS paciente_nombre
              FROM turno t
              JOIN profesional p ON t.profesional_id = p.id
              JOIN sillon s ON t.sillon_id = s.id
              JOIN paciente pac ON t.paciente_id = pac.id
             WHERE {where_sql}
             ORDER BY t.fecha_hora_inicio, t.id
        """
        filas = self._conexion.execute(sql, tuple(parametros)).fetchall()
        return [self._fila_a_turno(fila) for fila in filas]

    def agregar(self, turno: Turno) -> None:
        """Siembra un turno directamente delegando en guardar."""
        self.guardar(turno)

    def buscar_activos_solapables(
        self,
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        profesional: Profesional,
        sillon: Sillon,
    ) -> list[Turno]:
        """Consulta en SQL los turnos activos en conflicto potencial (design D5, RN-04, D-07)."""
        prof_id = self._repo_profesionales.resolver_id(profesional.nombre)
        sil_id = self._repo_sillones.resolver_id(sillon.nombre)

        nuevo_inicio = f"{fecha} {hora_inicio}"
        nuevo_fin = f"{fecha} {hora_fin}"

        # Cláusula estado IN generada dinámicamente desde ESTADOS_ACTIVOS (RN-04 / design D5)
        estados_placeholder = ", ".join("?" for _ in ESTADOS_ACTIVOS)
        estados_valores = tuple(ESTADOS_ACTIVOS)

        sql = f"""
            SELECT t.id, t.fecha_hora_inicio, t.fecha_hora_fin, t.estado,
                   p.id AS profesional_id, p.nombre AS profesional_nombre,
                   s.id AS sillon_id, s.nombre AS sillon_nombre,
                   pac.nombre AS paciente_nombre
              FROM turno t
              JOIN profesional p ON t.profesional_id = p.id
              JOIN sillon s ON t.sillon_id = s.id
              JOIN paciente pac ON t.paciente_id = pac.id
             WHERE t.tenant_id = ?
               AND t.estado IN ({estados_placeholder})
               AND (t.profesional_id = ? OR t.sillon_id = ?)
               AND t.fecha_hora_inicio < ?
               AND t.fecha_hora_fin > ?
             ORDER BY t.id
        """

        parametros = (
            self._tenant_id,
            *estados_valores,
            prof_id,
            sil_id,
            nuevo_fin,
            nuevo_inicio,
        )

        filas = self._conexion.execute(sql, parametros).fetchall()

        candidatos: list[Turno] = []
        for fila in filas:
            f_inicio = fila["fecha_hora_inicio"] if isinstance(fila, sqlite3.Row) else fila[1]
            f_fin = fila["fecha_hora_fin"] if isinstance(fila, sqlite3.Row) else fila[2]
            estado = fila["estado"] if isinstance(fila, sqlite3.Row) else fila[3]
            p_id = fila["profesional_id"] if isinstance(fila, sqlite3.Row) else fila[4]
            p_nom = fila["profesional_nombre"] if isinstance(fila, sqlite3.Row) else fila[5]
            s_id = fila["sillon_id"] if isinstance(fila, sqlite3.Row) else fila[6]
            s_nom = fila["sillon_nombre"] if isinstance(fila, sqlite3.Row) else fila[7]
            pac_nom = fila["paciente_nombre"] if isinstance(fila, sqlite3.Row) else fila[8]
            t_id = fila["id"] if isinstance(fila, sqlite3.Row) else fila[0]

            f_part, h_inicio = f_inicio.split(" ")
            _, h_fin = f_fin.split(" ")

            candidatos.append(
                Turno(
                    id=t_id,
                    profesional=Profesional(nombre=p_nom, id=p_id),
                    sillon=Sillon(nombre=s_nom, id=s_id),
                    fecha=f_part,
                    hora_inicio=h_inicio,
                    hora_fin=h_fin,
                    paciente=pac_nom,
                    estado=estado,
                )
            )
        return candidatos
