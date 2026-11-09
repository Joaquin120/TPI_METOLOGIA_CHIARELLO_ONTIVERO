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
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria


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


def test_modelos_profesional_y_sillon_atributos_operativos() -> None:
    """Task 1.2 (C-06): Profesional y Sillon admiten atributos operativos con defaults retrocompatibles."""
    # Instanciación mínima con defaults
    p_defecto = Profesional(nombre="Dra. Defecto")
    assert p_defecto.nombre == "Dra. Defecto"
    assert p_defecto.id is None
    assert p_defecto.matricula is None
    assert p_defecto.especialidad is None
    assert p_defecto.activo is True

    s_defecto = Sillon(nombre="Sillón 1")
    assert s_defecto.nombre == "Sillón 1"
    assert s_defecto.id is None
    assert s_defecto.equipamiento is None
    assert s_defecto.activo is True

    # Instanciación completa
    p_completo = Profesional(
        nombre="Dr. Gómez",
        id=5,
        matricula="MP-9999",
        especialidad="Endodoncia",
        activo=False,
    )
    assert p_completo.matricula == "MP-9999"
    assert p_completo.especialidad == "Endodoncia"
    assert p_completo.activo is False

    s_completo = Sillon(
        nombre="Sillón Quirúrgico",
        id=3,
        equipamiento="Turbina LED + Rayos X",
        activo=False,
    )
    assert s_completo.equipamiento == "Turbina LED + Rayos X"
    assert s_completo.activo is False


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
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
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
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
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
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
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


# ---------------------------------------------------------------------------
# Triangulación: doble validación de recurso (AGENTS.md regla 2)
# ---------------------------------------------------------------------------


def test_triangulacion_conflicto_de_sillon_lanza_solapamiento_sillon() -> None:
    """El sillón ocupado por OTRO profesional lanza SolapamientoSillonError."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
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
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
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
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
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


# ---------------------------------------------------------------------------
# C-05: Task 1.1 - Búsqueda por ID y filtros opcionales en ServicioTurnos
# ---------------------------------------------------------------------------


def test_servicio_obtener_por_id_existente() -> None:
    """Task 1.1: ServicioTurnos.obtener_por_id retorna el turno con el ID buscado."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    turno = servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )
    assert turno.id is not None
    recuperado = servicio.obtener_por_id(turno.id)
    assert recuperado is not None
    assert recuperado.id == turno.id
    assert recuperado.paciente == "Paciente A"


def test_servicio_obtener_por_id_inexistente_retorna_none() -> None:
    """Task 1.1: ServicioTurnos.obtener_por_id retorna None si el turno no existe."""
    servicio = ServicioTurnos(RepositorioTurnosEnMemoria())
    assert servicio.obtener_por_id(9999) is None


def test_servicio_turnos_registrados_con_filtros() -> None:
    """Task 1.1: ServicioTurnos.turnos_registrados delega filtros al repositorio."""
    repo = RepositorioTurnosEnMemoria()
    servicio = ServicioTurnos(repo)
    t1 = servicio.agendar_turno(
        paciente="Paciente 1",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )
    t2 = servicio.agendar_turno(
        paciente="Paciente 2",
        fecha="2026-11-02",
        hora_inicio="11:00",
        hora_fin="11:30",
        profesional=Profesional(nombre="Dra. Gómez", id=2),
        sillon=Sillon(nombre="Sillón 2", id=2),
    )
    # Filtrar por fecha
    filtrados_fecha = servicio.turnos_registrados(fecha="2026-11-01")
    assert len(filtrados_fecha) == 1
    assert filtrados_fecha[0].id == t1.id

    # Filtrar por profesional_id
    filtrados_prof = servicio.turnos_registrados(profesional_id=2)
    assert len(filtrados_prof) == 1
    assert filtrados_prof[0].id == t2.id

    # Filtrar por sillón_id
    filtrados_sillon = servicio.turnos_registrados(sillon_id=1)
    assert len(filtrados_sillon) == 1
    assert filtrados_sillon[0].id == t1.id

    # Filtro combinado sin coincidencias
    assert len(servicio.turnos_registrados(fecha="2026-11-01", profesional_id=2)) == 0

