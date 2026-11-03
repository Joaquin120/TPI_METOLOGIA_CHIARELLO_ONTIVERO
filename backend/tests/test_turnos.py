"""Pruebas de los 3 escenarios Gherkin: creación de turnos sin solapamientos.

Todos los datos son sintéticos (regla de privacidad de AGENTS.md).
"""

import pytest

from src.domain.exceptions import (
    SolapamientoProfesionalError,
    SolapamientoSillonError,
)
from src.domain.models import Profesional, Sillon, Turno
from src.domain.services import ServicioTurnos


# ---------------------------------------------------------------------------
# Task 1: modelos de dominio
# ---------------------------------------------------------------------------


def test_modelos_dominio_disponibles() -> None:
    """Task 1: los modelos de dominio existen y se pueden instanciar."""
    profesional = Profesional(nombre="Dr. Pérez")
    sillon = Sillon(nombre="Sillón 1")
    turno = Turno(
        profesional=profesional,
        sillon=sillon,
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente A",
    )
    assert turno.profesional.nombre == "Dr. Pérez"
    assert turno.sillon.nombre == "Sillón 1"
    assert turno.estado == "CONFIRMADO"


# ---------------------------------------------------------------------------
# Task 2: excepciones de dominio
# ---------------------------------------------------------------------------


def test_excepciones_de_dominio_son_excepciones() -> None:
    """Task 2: las excepciones de solapamiento son excepciones de dominio explícitas."""
    assert issubclass(SolapamientoProfesionalError, Exception)
    assert issubclass(SolapamientoSillonError, Exception)
    assert issubclass(SolapamientoProfesionalError, SolapamientoSillonError) is False


# ---------------------------------------------------------------------------
# Escenario 1 (Gherkin): Creación exitosa de turno sin conflicto (Camino Feliz)
# ---------------------------------------------------------------------------


def test_escenario_1_creacion_exitosa_sin_conflicto() -> None:
    """El turno se registra con éxito y queda con estado CONFIRMADO."""
    servicio = ServicioTurnos()
    turno = servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert turno.estado == "CONFIRMADO"
    assert turno.paciente == "Paciente A"
    assert servicio.turnos_registrados() == [turno]


# ---------------------------------------------------------------------------
# Escenario 2 (Gherkin): Rechazo por conflicto de agenda (Error de Negocio)
# ---------------------------------------------------------------------------


def test_escenario_2_rechazo_por_conflicto_de_profesional() -> None:
    """Un solapamiento del profesional lanza SolapamientoProfesionalError aunque cambie el sillón."""
    servicio = ServicioTurnos()
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    with pytest.raises(SolapamientoProfesionalError):
        servicio.agendar_turno(
            paciente="Paciente B",
            fecha="2026-11-01",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional=Profesional(nombre="Dr. Pérez"),
            sillon=Sillon(nombre="Sillón 2"),
        )


# ---------------------------------------------------------------------------
# Escenario 3 (Gherkin): Turnos contiguos en el límite exacto (Caso de Borde)
# ---------------------------------------------------------------------------


def test_escenario_3_turnos_contiguos_no_son_solapamiento() -> None:
    """a_fin == b_inicio NO es solapamiento: la reserva se permite."""
    servicio = ServicioTurnos()
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    turno_2 = servicio.agendar_turno(
        paciente="Paciente B",
        fecha="2026-11-01",
        hora_inicio="10:30",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert turno_2.estado == "CONFIRMADO"
    assert len(servicio.turnos_registrados()) == 2


# ---------------------------------------------------------------------------
# Triangulación: doble validación de recurso (AGENTS.md regla 2)
# ---------------------------------------------------------------------------


def test_triangulacion_conflicto_de_sillon_lanza_solapamiento_sillon() -> None:
    """El sillón ocupado por OTRO profesional lanza SolapamientoSillonError."""
    servicio = ServicioTurnos()
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    with pytest.raises(SolapamientoSillonError):
        servicio.agendar_turno(
            paciente="Paciente B",
            fecha="2026-11-01",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional=Profesional(nombre="Dr. Ejemplo"),
            sillon=Sillon(nombre="Sillón 1"),
        )


def test_triangulacion_solape_invertido_es_conflicto() -> None:
    """Un turno nuevo que termina DESPUÉS de iniciar el existente: solapa."""
    servicio = ServicioTurnos()
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:15",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    with pytest.raises(SolapamientoProfesionalError):
        servicio.agendar_turno(
            paciente="Paciente B",
            fecha="2026-11-01",
            hora_inicio="10:00",
            hora_fin="10:20",
            profesional=Profesional(nombre="Dr. Pérez"),
            sillon=Sillon(nombre="Sillón 2"),
        )


def test_triangulacion_fechas_diferentes_no_conflictan() -> None:
    """El mismo horario en otra fecha no genera solapamiento."""
    servicio = ServicioTurnos()
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    turno_2 = servicio.agendar_turno(
        paciente="Paciente B",
        fecha="2026-11-02",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    assert turno_2.estado == "CONFIRMADO"
