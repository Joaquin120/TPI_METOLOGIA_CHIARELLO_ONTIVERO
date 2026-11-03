"""Servicio de dominio para el agendamiento de turnos odontológicos."""

from dataclasses import replace

from src.domain.exceptions import (
    SolapamientoProfesionalError,
    SolapamientoSillonError,
    TransicionInvalidaError,
)
from src.domain.models import (
    CANCELADO,
    COMPLETADO,
    CONFIRMADO,
    PENDIENTE,
    Profesional,
    Sillon,
    Turno,
)

# Lista blanca de transiciones válidas: (estado_actual, acción) → estado_destino.
# Toda pareja ausente es inválida y debe rechazarse con `TransicionInvalidaError`
# (los estados finales CANCELADO/COMPLETADO son absorbentes: cero transiciones
# salientes). Matriz validada contra RN-03 / design D2.
_TRANSICIONES: dict[tuple[str, str], str] = {
    (PENDIENTE, "confirmar"): CONFIRMADO,
    (PENDIENTE, "cancelar"): CANCELADO,
    (CONFIRMADO, "cancelar"): CANCELADO,
    (CONFIRMADO, "completar"): COMPLETADO,
}

# Estados que siguen bloqueando profesional y sillón en `agendar_turno()`
# (RN-04: al cancelar/liberarse, el turno deja de ser activo) — design D4.
ESTADOS_ACTIVOS = frozenset({PENDIENTE, CONFIRMADO})


def _horas_a_minutos(hora: str) -> int:
    """Convierte una hora 'HH:MM' a minutos desde medianoche."""
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def _hay_solapamiento(
    inicio_a: int, fin_a: int, inicio_b: int, fin_b: int
) -> bool:
    """Intervalos semiabiertos [inicio, fin): solapan iff a_inicio < b_fin and a_fin > b_inicio.

    Si fin_a == inicio_b (contiguo) NO hay solapamiento.
    """
    return inicio_a < fin_b and fin_a > inicio_b


class ServicioTurnos:
    """Registra turnos validando solapamientos por profesional y por sillón de forma independiente."""

    def __init__(self) -> None:
        self._turnos: list[Turno] = []

    def agendar_turno(
        self,
        paciente: str,
        fecha: str,
        hora_inicio: str,
        hora_fin: str,
        profesional: Profesional,
        sillon: Sillon,
    ) -> Turno:
        """Crea y registra un turno si no hay solapamiento de profesional ni de sillón."""
        inicio = _horas_a_minutos(hora_inicio)
        fin = _horas_a_minutos(hora_fin)

        for turno_existente in self._turnos:
            if turno_existente.fecha != fecha:
                continue
            # RN-04: solo los turnos activos bloquean recursos; al cancelar o
            # completar, el turno deja de bloquear profesional Y sillón (D4).
            if turno_existente.estado not in ESTADOS_ACTIVOS:
                continue
            existente_inicio = _horas_a_minutos(turno_existente.hora_inicio)
            existente_fin = _horas_a_minutos(turno_existente.hora_fin)
            if not _hay_solapamiento(inicio, fin, existente_inicio, existente_fin):
                continue
            # Doble validación de recurso: profesional y sillón, de forma independiente.
            if turno_existente.profesional == profesional:
                raise SolapamientoProfesionalError(
                    f"El profesional {profesional.nombre} ya tiene un turno "
                    f"el {fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )
            if turno_existente.sillon == sillon:
                raise SolapamientoSillonError(
                    f"El sillón {sillon.nombre} ya está ocupado "
                    f"el {fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )

        turno = Turno(
            profesional=profesional,
            sillon=sillon,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            paciente=paciente,
        )
        self._turnos.append(turno)
        return turno

    def turnos_registrados(self) -> list[Turno]:
        """Devuelve una copia de la lista de turnos registrados."""
        return list(self._turnos)

    def _transicionar(self, turno: Turno, accion: str) -> Turno:
        """Aplica una acción de la lista blanca `_TRANSICIONES` y reemplaza el turno registrado.

        Devuelve la instancia actualizada (design D5); la referencia previa queda
        como snapshot del estado anterior.
        """
        destino = _TRANSICIONES.get((turno.estado, accion))
        if destino is None:
            raise TransicionInvalidaError(
                f"No se puede aplicar '{accion}' sobre un turno en estado "
                f"'{turno.estado}'"
            )
        actualizado = replace(turno, estado=destino)
        for indice, registrado in enumerate(self._turnos):
            if registrado is turno or registrado == turno:
                self._turnos[indice] = actualizado
                break
        return actualizado

    def confirmar(self, turno: Turno) -> Turno:
        """PENDIENTE → CONFIRMADO (RN-03)."""
        return self._transicionar(turno, "confirmar")

    def cancelar(self, turno: Turno) -> Turno:
        """PENDIENTE | CONFIRMADO → CANCELADO (RN-03). Libera profesional y sillón."""
        return self._transicionar(turno, "cancelar")

    def completar(self, turno: Turno) -> Turno:
        """CONFIRMADO → COMPLETADO (RN-03)."""
        return self._transicionar(turno, "completar")
