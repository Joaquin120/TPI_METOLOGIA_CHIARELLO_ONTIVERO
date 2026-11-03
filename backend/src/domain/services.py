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
    ESTADOS_ACTIVOS,
    PENDIENTE,
    Profesional,
    Sillon,
    Turno,
)
from src.domain.puertos import PuertoTurnos
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria

# Lista blanca de transiciones válidas: (estado_actual, acción) → estado_destino.
_TRANSICIONES: dict[tuple[str, str], str] = {
    (PENDIENTE, "confirmar"): CONFIRMADO,
    (PENDIENTE, "cancelar"): CANCELADO,
    (CONFIRMADO, "cancelar"): CANCELADO,
    (CONFIRMADO, "completar"): COMPLETADO,
}


class ServicioTurnos:
    """Registra turnos validando solapamientos por profesional y por sillón de forma independiente."""

    def __init__(self, repositorio: PuertoTurnos | None = None) -> None:
        self._repositorio: PuertoTurnos = (
            repositorio if repositorio is not None else RepositorioTurnosEnMemoria()
        )

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
        candidatos = self._repositorio.buscar_activos_solapables(
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            profesional=profesional,
            sillon=sillon,
        )

        for turno_existente in candidatos:
            # Doble validación de recurso: profesional y sillón, de forma independiente.
            # Precedencia RN-09: se valida profesional primero, sillón segundo.
            if (
                turno_existente.profesional == profesional
                or turno_existente.profesional.nombre == profesional.nombre
            ):
                raise SolapamientoProfesionalError(
                    f"El profesional {profesional.nombre} ya tiene un turno "
                    f"el {fecha} de {turno_existente.hora_inicio} a {turno_existente.hora_fin}"
                )
            if (
                turno_existente.sillon == sillon
                or turno_existente.sillon.nombre == sillon.nombre
            ):
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
        return self._repositorio.guardar(turno)

    def turnos_registrados(self) -> list[Turno]:
        """Devuelve una copia de la lista de turnos registrados."""
        return self._repositorio.listar()

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
        return self._repositorio.actualizar(actualizado)

    def confirmar(self, turno: Turno) -> Turno:
        """PENDIENTE → CONFIRMADO (RN-03)."""
        return self._transicionar(turno, "confirmar")

    def cancelar(self, turno: Turno) -> Turno:
        """PENDIENTE | CONFIRMADO → CANCELADO (RN-03). Libera profesional y sillón."""
        return self._transicionar(turno, "cancelar")

    def completar(self, turno: Turno) -> Turno:
        """CONFIRMADO → COMPLETADO (RN-03)."""
        return self._transicionar(turno, "completar")
