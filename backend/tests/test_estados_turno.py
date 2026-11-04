"""Pruebas del ciclo de vida del turno: estados, transiciones y liberación de recursos.

Cubre los 3 escenarios obligatorios de la spec `gestionar-estados-turno`:
  - Esperado: la cancelación libera el intervalo del profesional y del sillón.
  - Error de Negocio: los estados finales son absorbentes (TransicionInvalidaError).
  - Caso de Borde: re-reserva en el intervalo semiabierto liberado.

Todos los datos son sintéticos (regla de privacidad de AGENTS.md).
"""

import pytest

from src.domain.exceptions import TransicionInvalidaError
from src.domain.models import (
    CANCELADO,
    COMPLETADO,
    CONFIRMADO,
    PENDIENTE,
    Profesional,
    Sillon,
    Turno,
)
from src.domain.services import ServicioTurnos
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria


def test_constantes_de_estado_disponibles() -> None:
    """Task 1.1: las cuatro constantes de estado existen, son distintas y el default no cambia."""
    estados = {PENDIENTE, CONFIRMADO, CANCELADO, COMPLETADO}
    assert len(estados) == 4
    assert estados == {"PENDIENTE", "CONFIRMADO", "CANCELADO", "COMPLETADO"}

    turno = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
    )
    assert turno.estado == CONFIRMADO


def test_transicion_invalida_sigue_el_patron_de_excepciones() -> None:
    """Task 2.1: TransicionInvalidaError sigue el patrón de `src/domain/exceptions.py`."""
    assert issubclass(TransicionInvalidaError, Exception)
    assert str(TransicionInvalidaError()) == (
        "La transición no es válida para el estado del turno"
    )
    assert str(TransicionInvalidaError("detalle propio")) == "detalle propio"


# ---------------------------------------------------------------------------
# Helpers de datos sintéticos
# ---------------------------------------------------------------------------


def _agendar(servicio: ServicioTurnos) -> Turno:
    """Agenda un turno CONFIRMADO 10:00–10:30 del 2026-11-01 (Dr. Pérez / Sillón 1)."""
    return servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )


def _sembrar(servicio: ServicioTurnos, estado: str) -> Turno:
    """Registra un turno en un estado arbitrario (misma ventana horaria que `_agendar`).

    `agendar_turno()` nace siempre en CONFIRMADO (alta `PA-13` abierta, design D6),
    por lo que los estados que el alta no alcanza se instancian directamente y se
    siembran en el servicio — es la única forma de probar `PENDIENTE`, `CANCELADO`
    y `COMPLETADO` sin resolver `PA-13`.
    """
    turno = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
        estado=estado,
    )
    servicio._repositorio.agregar(turno)
    return turno


def _sembrar_pendiente(servicio: ServicioTurnos) -> Turno:
    """Registra un turno en estado PENDIENTE (ver `_sembrar`)."""
    return _sembrar(servicio, PENDIENTE)


# ---------------------------------------------------------------------------
# Task 3: camino feliz de la spec — transiciones válidas (RN-03)
# ---------------------------------------------------------------------------


def test_confirmar_pendiente_pasa_a_confirmado() -> None:
    """Escenario 'Confirmación de un turno pendiente': PENDIENTE → CONFIRMADO."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    pendiente = _sembrar_pendiente(servicio)

    confirmado = servicio.confirmar(pendiente)

    assert confirmado.estado == CONFIRMADO
    registrados = servicio.turnos_registrados()
    assert len(registrados) == 1
    assert registrados[0].estado == CONFIRMADO
    assert registrados[0].profesional == pendiente.profesional
    assert registrados[0].sillon == pendiente.sillon
    assert registrados[0].hora_inicio == pendiente.hora_inicio
    assert registrados[0].hora_fin == pendiente.hora_fin


def test_cancelar_confirmado_pasa_a_cancelado() -> None:
    """Cancelar un turno CONFIRMADO lo lleva a CANCELADO y lo conserva registrado."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _agendar(servicio)

    cancelado = servicio.cancelar(turno)

    assert cancelado.estado == CANCELADO
    registrados = servicio.turnos_registrados()
    assert len(registrados) == 1
    assert registrados[0].estado == CANCELADO
    assert registrados[0].profesional == turno.profesional
    assert registrados[0].sillon == turno.sillon


def test_completar_confirmado_pasa_a_completado() -> None:
    """Escenario 'Finalización de un turno confirmado': CONFIRMADO → COMPLETADO."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _agendar(servicio)

    completado = servicio.completar(turno)

    assert completado.estado == COMPLETADO
    registrados = servicio.turnos_registrados()
    assert len(registrados) == 1
    assert registrados[0].estado == COMPLETADO
    assert registrados[0].profesional == turno.profesional
    assert registrados[0].sillon == turno.sillon


# ---------------------------------------------------------------------------
# Task 4: estados finales absorbentes — Escenario de Error de Negocio
# ---------------------------------------------------------------------------


def test_estado_final_cancelado_no_admite_completar() -> None:
    """Escenario 'Completar un turno cancelado se rechaza': CANCELADO es absorbente."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _sembrar(servicio, CANCELADO)

    with pytest.raises(TransicionInvalidaError):
        servicio.completar(turno)

    registrados = servicio.turnos_registrados()
    assert registrados[0].estado == CANCELADO


def test_estado_final_cancelado_no_admite_cancelar() -> None:
    """CANCELADO → CANCELADO también es inválida: no hay transición saliente."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _sembrar(servicio, CANCELADO)

    with pytest.raises(TransicionInvalidaError):
        servicio.cancelar(turno)

    assert servicio.turnos_registrados()[0].estado == CANCELADO


def test_estado_final_completado_no_admite_cancelar() -> None:
    """Escenario 'Cancelar un turno completado se rechaza': COMPLETADO es absorbente."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _sembrar(servicio, COMPLETADO)

    with pytest.raises(TransicionInvalidaError):
        servicio.cancelar(turno)

    assert servicio.turnos_registrados()[0].estado == COMPLETADO


def test_estado_final_completado_no_admite_completar() -> None:
    """Triangulación: COMPLETADO → COMPLETADO también es inválida."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _sembrar(servicio, COMPLETADO)

    with pytest.raises(TransicionInvalidaError):
        servicio.completar(turno)

    assert servicio.turnos_registrados()[0].estado == COMPLETADO


def test_transicion_invalida_describe_estado_y_accion() -> None:
    """El rechazo informa el estado actual y la acción pedida (design D3)."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    _sembrar(servicio, CANCELADO)

    with pytest.raises(TransicionInvalidaError) as excinfo:
        servicio.completar(servicio.turnos_registrados()[0])

    mensaje = str(excinfo.value)
    assert CANCELADO in mensaje
    assert "completar" in mensaje


def test_confirmar_desde_confirmado_es_invalida() -> None:
    """Triangulación de lista blanca: CONFIRMADO → CONFIRMADO no está en RN-03."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = _agendar(servicio)

    with pytest.raises(TransicionInvalidaError):
        servicio.confirmar(turno)

    assert servicio.turnos_registrados()[0].estado == CONFIRMADO


# ---------------------------------------------------------------------------
# Task 5: liberación de recursos por cancelación (RN-04 + D-07)
# ---------------------------------------------------------------------------


def test_liberacion_cancelar_libera_profesional_y_sillon() -> None:
    """Escenario Esperado: al cancelar, ni el profesional ni el sillón quedan bloqueados."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )

    cancelado = servicio.cancelar(turno)
    assert cancelado.estado == CANCELADO

    # Re-agendar el mismo profesional Y el mismo sillón dentro de ["10:00", "10:30").
    reagendado = servicio.agendar_turno(
        paciente="Paciente Ficticio B",
        fecha="2026-11-01",
        hora_inicio="10:15",
        hora_fin="10:45",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert reagendado.estado == CONFIRMADO
    assert len(servicio.turnos_registrados()) == 2


def test_liberacion_doble_validacion_otro_profesional_mismo_sillon() -> None:
    """Triangulación: el sillón liberado está libre para OTRO profesional."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    servicio.cancelar(turno)

    reagendado = servicio.agendar_turno(
        paciente="Paciente Ficticio B",
        fecha="2026-11-01",
        hora_inicio="10:15",
        hora_fin="10:45",
        profesional=Profesional(nombre="Dr. Ejemplo 2"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert reagendado.estado == CONFIRMADO


def test_liberacion_doble_validacion_mismo_profesional_otro_sillon() -> None:
    """Triangulación: el profesional liberado está libre en OTRO sillón."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    servicio.cancelar(turno)

    reagendado = servicio.agendar_turno(
        paciente="Paciente Ficticio B",
        fecha="2026-11-01",
        hora_inicio="10:15",
        hora_fin="10:45",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 2"),
    )
    assert reagendado.estado == CONFIRMADO


def test_liberacion_turno_completado_no_bloquea() -> None:
    """COMPLETADO también deja de ser activo: no bloquea profesional ni sillón."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    servicio.completar(turno)

    reagendado = servicio.agendar_turno(
        paciente="Paciente Ficticio B",
        fecha="2026-11-01",
        hora_inicio="10:15",
        hora_fin="10:45",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert reagendado.estado == CONFIRMADO
    assert len(servicio.turnos_registrados()) == 2


def test_liberacion_turno_cancelado_se_conserva_como_historial() -> None:
    """Triangulación negativa: el filtro es por activos, no un borrado del historial."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    servicio.cancelar(turno)

    # El turno cancelado se conserva como historial (RN-04 / flows §4).
    registrados = servicio.turnos_registrados()
    assert len(registrados) == 1
    assert registrados[0].estado == CANCELADO


def test_liberacion_re_reserva_contigua_en_t_fin() -> None:
    """Caso de Borde: la re-reserva que empieza exactamente en T_fin no solapa (D-07).

    Red de seguridad: debe pasar desde ya, sin el cambio de la task 5.3, porque
    `_hay_solapamiento()` ya usa intervalos semiabiertos [inicio, fin).
    """
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    servicio.cancelar(turno)

    contiguo = servicio.agendar_turno(
        paciente="Paciente Ficticio B",
        fecha="2026-11-01",
        hora_inicio="10:30",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert contiguo.estado == CONFIRMADO
    assert len(servicio.turnos_registrados()) == 2
