"""Adaptador de persistencia de Lista de Espera en SQLite con aislamiento por tenant (C-15, F-08, PA-14)."""

from dataclasses import replace
import sqlite3

from src.domain.models import EntradaListaEspera, EstadoListaEspera


class RepositorioListaEsperaSqlite:
    """Implementa `PuertoListaEspera` garantizando aislamiento multitenant y orden FIFO."""

    def __init__(self, conexion: sqlite3.Connection, tenant_id: int) -> None:
        self._conexion = conexion
        self._tenant_id = tenant_id

    def _fila_a_entrada(self, fila: sqlite3.Row | tuple) -> EntradaListaEspera:
        e_id = fila["id"] if isinstance(fila, sqlite3.Row) else fila[0]
        t_id = fila["tenant_id"] if isinstance(fila, sqlite3.Row) else fila[1]
        p_nom = fila["paciente_nombre"] if isinstance(fila, sqlite3.Row) else fila[2]
        p_tel = fila["paciente_telefono"] if isinstance(fila, sqlite3.Row) else fila[3]
        f_des = fila["fecha_deseada"] if isinstance(fila, sqlite3.Row) else fila[4]
        motivo = fila["motivo"] if isinstance(fila, sqlite3.Row) else fila[5]
        prof_nom = fila["profesional_nombre"] if isinstance(fila, sqlite3.Row) else fila[6]
        franja = fila["franja_horaria"] if isinstance(fila, sqlite3.Row) else fila[7]
        estado = fila["estado"] if isinstance(fila, sqlite3.Row) else fila[8]
        creado_en = fila["creado_en"] if isinstance(fila, sqlite3.Row) else fila[9]

        return EntradaListaEspera(
            id=e_id,
            tenant_id=t_id,
            paciente_nombre=p_nom,
            paciente_telefono=p_tel,
            fecha_deseada=f_des,
            motivo=motivo,
            profesional_nombre=prof_nom,
            franja_horaria=franja,
            estado=estado,
            creado_en=creado_en,
        )

    def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        """Persiste una nueva entrada en lista_espera."""
        cursor = self._conexion.execute(
            """
            INSERT INTO lista_espera (
                tenant_id, paciente_nombre, paciente_telefono, fecha_deseada,
                motivo, profesional_nombre, franja_horaria, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._tenant_id,
                entrada.paciente_nombre,
                entrada.paciente_telefono,
                entrada.fecha_deseada,
                entrada.motivo,
                entrada.profesional_nombre,
                entrada.franja_horaria,
                entrada.estado,
            ),
        )
        self._conexion.commit()
        nuevo_id = cursor.lastrowid
        fila = self._conexion.execute(
            "SELECT creado_en FROM lista_espera WHERE id = ?", (nuevo_id,)
        ).fetchone()
        creado_en = fila[0] if fila is not None else None
        return replace(
            entrada,
            id=nuevo_id,
            tenant_id=self._tenant_id,
            creado_en=creado_en,
        )

    def actualizar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        """Actualiza el estado u observaciones de una entrada existente."""
        self._conexion.execute(
            """
            UPDATE lista_espera
            SET estado = ?, motivo = ?, franja_horaria = ?, profesional_nombre = ?
            WHERE id = ? AND tenant_id = ?
            """,
            (
                entrada.estado,
                entrada.motivo,
                entrada.franja_horaria,
                entrada.profesional_nombre,
                entrada.id,
                self._tenant_id,
            ),
        )
        self._conexion.commit()
        return entrada

    def obtener_por_id(self, entrada_id: int) -> EntradaListaEspera | None:
        """Recupera una entrada por ID dentro del tenant."""
        fila = self._conexion.execute(
            """
            SELECT id, tenant_id, paciente_nombre, paciente_telefono, fecha_deseada,
                   motivo, profesional_nombre, franja_horaria, estado, creado_en
            FROM lista_espera
            WHERE id = ? AND tenant_id = ?
            """,
            (entrada_id, self._tenant_id),
        ).fetchone()
        if fila is None:
            return None
        return self._fila_a_entrada(fila)

    def listar(
        self,
        fecha: str | None = None,
        profesional_nombre: str | None = None,
        estado: str | None = None,
    ) -> list[EntradaListaEspera]:
        """Recupera la lista de entradas aplicando filtros opcionales."""
        query = """
            SELECT id, tenant_id, paciente_nombre, paciente_telefono, fecha_deseada,
                   motivo, profesional_nombre, franja_horaria, estado, creado_en
            FROM lista_espera
            WHERE tenant_id = ?
        """
        params: list[object] = [self._tenant_id]

        if fecha:
            query += " AND fecha_deseada = ?"
            params.append(fecha)
        if profesional_nombre:
            query += " AND profesional_nombre = ?"
            params.append(profesional_nombre)
        if estado:
            query += " AND estado = ?"
            params.append(estado)

        query += " ORDER BY creado_en ASC, id ASC"

        filas = self._conexion.execute(query, tuple(params)).fetchall()
        return [self._fila_a_entrada(f) for f in filas]

    def buscar_candidatos(
        self, fecha: str, profesional_nombre: str | None = None
    ) -> list[EntradaListaEspera]:
        """Recupera candidatos pendientes priorizados por orden cronológico (FIFO)."""
        query = """
            SELECT id, tenant_id, paciente_nombre, paciente_telefono, fecha_deseada,
                   motivo, profesional_nombre, franja_horaria, estado, creado_en
            FROM lista_espera
            WHERE tenant_id = ? AND estado = ? AND fecha_deseada = ?
        """
        params: list[object] = [self._tenant_id, EstadoListaEspera.PENDIENTE, fecha]

        if profesional_nombre:
            query += " AND (profesional_nombre = ? OR profesional_nombre IS NULL)"
            params.append(profesional_nombre)

        query += " ORDER BY creado_en ASC, id ASC"

        filas = self._conexion.execute(query, tuple(params)).fetchall()
        return [self._fila_a_entrada(f) for f in filas]

