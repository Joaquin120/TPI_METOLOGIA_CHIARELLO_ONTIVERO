"""Adaptador de repositorio de turnos en memoria (design D1, D2)."""

from dataclasses import replace

from src.domain.models import ESTADOS_ACTIVOS, Profesional, Sillon, Turno


def _horas_a_minutos(hora: str) -> int:
    """Convierte una hora 'HH:MM' a minutos desde medianoche."""
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def _hay_solapamiento(
    inicio_a: int, fin_a: int, inicio_b: int, fin_b: int
) -> bool:
    """Intervalos semiabiertos [inicio, fin): solapan iff a_inicio < b_fin and a_fin > b_inicio.

    Si fin_a == inicio_b (contiguo) NO hay solapamiento (D-07).
    """
    return inicio_a < fin_b and fin_a > inicio_b


class RepositorioTurnosEnMemoria:
    """Implementación en memoria de `PuertoTurnos` para pruebas unitarias sin BD."""

    def __init__(self) -> None:
        self._turnos: list[Turno] = []

    def guardar(self, turno: Turno) -> Turno:
        """Persiste un turno nuevo en memoria y asigna un id autoincremental provisorio."""
        if turno.id is None:
            turno = replace(turno, id=len(self._turnos) + 1)
        self._turnos.append(turno)
        return turno

    def actualizar(self, turno: Turno) -> Turno:
        """Actualiza un turno existente en la lista."""
        for indice, registrado in enumerate(self._turnos):
            if turno.id is not None and registrado.id == turno.id:
                self._turnos[indice] = turno
                return turno
            if (
                registrado.fecha == turno.fecha
                and registrado.hora_inicio == turno.hora_inicio
                and registrado.hora_fin == turno.hora_fin
                and registrado.profesional.nombre == turno.profesional.nombre
                and registrado.sillon.nombre == turno.sillon.nombre
                and registrado.paciente == turno.paciente
            ):
                self._turnos[indice] = turno
                return turno
        self._turnos.append(turno)
        return turno

    def actualizar_reprogramacion(self, turno: Turno) -> Turno:
        """Actualiza un turno existente en memoria preservando su id."""
        for indice, registrado in enumerate(self._turnos):
            if turno.id is not None and registrado.id == turno.id:
                self._turnos[indice] = turno
                return turno
        self._turnos.append(turno)
        return turno

    def obtener_por_id(self, turno_id: int) -> Turno | None:
        """Recupera un turno por su ID en memoria."""
        for turno in self._turnos:
            if turno.id == turno_id:
                return turno
        return None

    def listar(
        self,
        fecha: str | None = None,
        profesional_id: int | None = None,
        sillon_id: int | None = None,
    ) -> list[Turno]:
        """Devuelve una copia de la lista de turnos registrados aplicando filtros."""
        resultado: list[Turno] = []
        for turno in self._turnos:
            if fecha is not None and turno.fecha != fecha:
                continue
            if (
                profesional_id is not None
                and turno.profesional.id != profesional_id
            ):
                continue
            if sillon_id is not None and turno.sillon.id != sillon_id:
                continue
            resultado.append(turno)
        return resultado

    def agregar(self, turno: Turno) -> None:
        """Agrega un turno directamente (soporte para sembrado en tests)."""
        self._turnos.append(turno)

    def buscar_activos_solapables(
        self,
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        profesional: Profesional,
        sillon: Sillon,
        excluir_turno_id: int | None = None,
    ) -> list[Turno]:
        """Filtra turnos activos que solapan temporalmente con el intervalo solicitado."""
        inicio = _horas_a_minutos(hora_inicio)
        fin = _horas_a_minutos(hora_fin)
        candidatos: list[Turno] = []

        for turno_existente in self._turnos:
            if excluir_turno_id is not None and turno_existente.id == excluir_turno_id:
                continue
            if turno_existente.fecha != fecha:
                continue
            if turno_existente.estado not in ESTADOS_ACTIVOS:
                continue
            existente_inicio = _horas_a_minutos(turno_existente.hora_inicio)
            existente_fin = _horas_a_minutos(turno_existente.hora_fin)
            if not _hay_solapamiento(inicio, fin, existente_inicio, existente_fin):
                continue
            if (
                turno_existente.profesional.nombre == profesional.nombre
                or turno_existente.sillon.nombre == sillon.nombre
            ):
                candidatos.append(turno_existente)
        return candidatos

    def buscar_activos_por_sillon(
        self,
        sillon_id: int,
        fecha_hora_inicio: str,
        fecha_hora_fin: str,
    ) -> list[Turno]:
        """Devuelve turnos activos asignados al sillón en el intervalo dado (RP-07)."""
        candidatos: list[Turno] = []
        for t in self._turnos:
            if t.estado not in ESTADOS_ACTIVOS:
                continue
            if t.sillon.id != sillon_id and t.sillon.nombre != str(sillon_id):
                continue
            t_inicio = f"{t.fecha} {t.hora_inicio}"
            t_fin = f"{t.fecha} {t.hora_fin}"
            if t_inicio < fecha_hora_fin and t_fin > fecha_hora_inicio:
                candidatos.append(t)
        return candidatos

