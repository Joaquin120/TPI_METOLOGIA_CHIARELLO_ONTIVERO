"""Pruebas unitarias de dominio para la reprogramación de turnos (C-08b, task 1.3).

Verifica todas las reglas de negocio de F-09 en aislamiento total:
- Modificación in-place (preservación de id, paciente y estado).
- Liberación del horario previo para nuevas reservas.
- Precedencia RN-09 de errores (profesional prioritario).
- Rechazo de estados terminales (CANCELADO, COMPLETADO).
- Desplazamiento parcial en la misma franja horaria sin auto-solapamiento.
"""

import pytest

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
from src.domain.services import ServicioTurnos
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria


@pytest.fixture
def servicio() -> ServicioTurnos:
    return ServicioTurnos(RepositorioTurnosEnMemoria())


def test_reprogramacion_exitosa_in_place_conserva_id_paciente_y_estado(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Reprogramación exitosa a un nuevo intervalo libre (Camino Feliz)."""
    p = Profesional(nombre="Dr. Pérez")
    s = Sillon(nombre="Sillón 1")
    original = servicio.agendar_turno(
        paciente="Paciente Ejemplo",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=p,
        sillon=s,
    )
    assert original.id is not None
    assert original.estado == CONFIRMADO

    reprogramado = servicio.reprogramar(
        turno_id=original.id,
        nueva_fecha="2026-11-01",
        nueva_hora_inicio="14:00",
        nueva_hora_fin="14:30",
    )

    assert reprogramado.id == original.id
    assert reprogramado.paciente == "Paciente Ejemplo"
    assert reprogramado.estado == CONFIRMADO
    assert reprogramado.fecha == "2026-11-01"
    assert reprogramado.hora_inicio == "14:00"
    assert reprogramado.hora_fin == "14:30"
    assert reprogramado.profesional == p
    assert reprogramado.sillon == s


def test_reprogramacion_libera_inmediatamente_horario_anterior(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Liberación inmediata del intervalo anterior para nuevas reservas."""
    p = Profesional(nombre="Dr. Pérez")
    s = Sillon(nombre="Sillón 1")
    turno_1 = servicio.agendar_turno(
        paciente="Paciente 1",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=p,
        sillon=s,
    )

    servicio.reprogramar(
        turno_id=turno_1.id,  # type: ignore[arg-type]
        nueva_fecha="2026-11-01",
        nueva_hora_inicio="14:00",
        nueva_hora_fin="14:30",
    )

    # Ahora el intervalo 10:00-10:30 debe poder agendarse libremente
    nuevo_turno = servicio.agendar_turno(
        paciente="Paciente 2",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=p,
        sillon=s,
    )
    assert nuevo_turno.estado == CONFIRMADO
    assert nuevo_turno.paciente == "Paciente 2"


def test_reprogramacion_con_cambio_de_profesional_y_sillon(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Reprogramación con cambio opcional de profesional y sillón."""
    p1 = Profesional(nombre="Dr. Pérez")
    s1 = Sillon(nombre="Sillón 1")
    p2 = Profesional(nombre="Dra. Colega")
    s2 = Sillon(nombre="Sillón 2")

    turno = servicio.agendar_turno(
        paciente="Paciente 1",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=p1,
        sillon=s1,
    )

    actualizado = servicio.reprogramar(
        turno_id=turno.id,  # type: ignore[arg-type]
        nueva_fecha="2026-11-02",
        nueva_hora_inicio="11:00",
        nueva_hora_fin="12:00",
        nuevo_profesional=p2,
        nuevo_sillon=s2,
    )

    assert actualizado.profesional == p2
    assert actualizado.sillon == s2
    assert actualizado.fecha == "2026-11-02"


def test_reprogramacion_rechaza_conflicto_de_profesional(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Conflicto por profesional ocupado en el nuevo horario."""
    dr_perez = Profesional(nombre="Dr. Pérez")
    sillon_1 = Sillon(nombre="Sillón 1")
    sillon_2 = Sillon(nombre="Sillón 2")

    # Turno existente de Dr. Perez de 14:00 a 15:00
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="14:00",
        hora_fin="15:00",
        profesional=dr_perez,
        sillon=sillon_1,
    )

    # Turno a reprogramar
    turno_b = servicio.agendar_turno(
        paciente="Paciente B",
        fecha="2026-11-01",
        hora_inicio="09:00",
        hora_fin="10:00",
        profesional=dr_perez,
        sillon=sillon_2,
    )

    # Intento de reprogramar turno_b hacia 14:30-15:30 con Dr. Pérez
    with pytest.raises(SolapamientoProfesionalError):
        servicio.reprogramar(
            turno_id=turno_b.id,  # type: ignore[arg-type]
            nueva_fecha="2026-11-01",
            nueva_hora_inicio="14:30",
            nueva_hora_fin="15:30",
        )


def test_reprogramacion_rechaza_conflicto_de_sillon(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Conflicto por sillón ocupado en el nuevo horario."""
    dr_perez = Profesional(nombre="Dr. Pérez")
    dra_colega = Profesional(nombre="Dra. Colega")
    sillon_1 = Sillon(nombre="Sillón 1")
    sillon_2 = Sillon(nombre="Sillón 2")

    # Sillón 1 ocupado por Dra. Colega de 14:00 a 15:00
    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="14:00",
        hora_fin="15:00",
        profesional=dra_colega,
        sillon=sillon_1,
    )

    # Turno a reprogramar (Dr. Perez en Sillon 2)
    turno_b = servicio.agendar_turno(
        paciente="Paciente B",
        fecha="2026-11-01",
        hora_inicio="09:00",
        hora_fin="10:00",
        profesional=dr_perez,
        sillon=sillon_2,
    )

    # Se intenta mover al Sillón 1 en 14:30-15:30
    with pytest.raises(SolapamientoSillonError):
        servicio.reprogramar(
            turno_id=turno_b.id,  # type: ignore[arg-type]
            nueva_fecha="2026-11-01",
            nueva_hora_inicio="14:30",
            nueva_hora_fin="15:30",
            nuevo_sillon=sillon_1,
        )


def test_reprogramacion_conflicto_simultaneo_aplica_precedencia_rn09(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Conflicto simultáneo de profesional y sillón aplica precedencia RN-09."""
    dr = Profesional(nombre="Dr. Pérez")
    sil = Sillon(nombre="Sillón 1")

    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="14:00",
        hora_fin="15:00",
        profesional=dr,
        sillon=sil,
    )

    turno_b = servicio.agendar_turno(
        paciente="Paciente B",
        fecha="2026-11-01",
        hora_inicio="09:00",
        hora_fin="10:00",
        profesional=dr,
        sillon=sil,
    )

    # Ambos recursos colisionan en 14:15-14:45 -> Debe lanzar SolapamientoProfesionalError
    with pytest.raises(SolapamientoProfesionalError):
        servicio.reprogramar(
            turno_id=turno_b.id,  # type: ignore[arg-type]
            nueva_fecha="2026-11-01",
            nueva_hora_inicio="14:15",
            nueva_hora_fin="14:45",
        )


def test_reprogramacion_turnos_contiguos_permitidos(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Turnos contiguos en el nuevo horario son válidos."""
    dr = Profesional(nombre="Dr. Pérez")
    sil = Sillon(nombre="Sillón 1")

    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=dr,
        sillon=sil,
    )

    turno_b = servicio.agendar_turno(
        paciente="Paciente B",
        fecha="2026-11-01",
        hora_inicio="12:00",
        hora_fin="12:30",
        profesional=dr,
        sillon=sil,
    )

    # Mover a 10:30-11:00 (contiguo al final de 10:00-10:30)
    actualizado = servicio.reprogramar(
        turno_id=turno_b.id,  # type: ignore[arg-type]
        nueva_fecha="2026-11-01",
        nueva_hora_inicio="10:30",
        nueva_hora_fin="11:00",
    )
    assert actualizado.hora_inicio == "10:30"
    assert actualizado.hora_fin == "11:00"


def test_reprogramacion_desplazamiento_parcial_sin_auto_solapamiento(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Desplazamiento parcial del horario original del propio turno."""
    dr = Profesional(nombre="Dr. Pérez")
    sil = Sillon(nombre="Sillón 1")

    turno = servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="11:00",
        profesional=dr,
        sillon=sil,
    )

    # Desplazar 30 min hacia adelante (10:30 a 11:30), solapa consigo mismo entre 10:30 y 11:00
    actualizado = servicio.reprogramar(
        turno_id=turno.id,  # type: ignore[arg-type]
        nueva_fecha="2026-11-01",
        nueva_hora_inicio="10:30",
        nueva_hora_fin="11:30",
    )
    assert actualizado.hora_inicio == "10:30"
    assert actualizado.hora_fin == "11:30"


def test_reprogramar_turno_cancelado_rechazado_con_transicion_invalida(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Intento de reprogramar un turno cancelado se rechaza."""
    turno = servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    cancelado = servicio.cancelar(turno)
    assert cancelado.estado == CANCELADO

    with pytest.raises(TransicionInvalidaError, match="CANCELADO"):
        servicio.reprogramar(
            turno_id=cancelado.id,  # type: ignore[arg-type]
            nueva_fecha="2026-11-02",
            nueva_hora_inicio="10:00",
            nueva_hora_fin="10:30",
        )


def test_reprogramar_turno_completado_rechazado_con_transicion_invalida(
    servicio: ServicioTurnos,
) -> None:
    """Escenario: Intento de reprogramar un turno completado se rechaza."""
    turno = servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Pérez"),
        sillon=Sillon(nombre="Sillón 1"),
    )
    completado = servicio.completar(turno)
    assert completado.estado == COMPLETADO

    with pytest.raises(TransicionInvalidaError, match="COMPLETADO"):
        servicio.reprogramar(
            turno_id=completado.id,  # type: ignore[arg-type]
            nueva_fecha="2026-11-02",
            nueva_hora_inicio="10:00",
            nueva_hora_fin="10:30",
        )


def test_reprogramar_turno_inexistente_lanza_value_error(
    servicio: ServicioTurnos,
) -> None:
    with pytest.raises(ValueError, match="El turno 999 no existe"):
        servicio.reprogramar(
            turno_id=999,
            nueva_fecha="2026-11-02",
            nueva_hora_inicio="10:00",
            nueva_hora_fin="10:30",
        )
