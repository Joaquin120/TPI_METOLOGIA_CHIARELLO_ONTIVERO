"""Pruebas del puerto de persistencia e inyección en el servicio (task 2.4, design D1/D2).

Verifica el comportamiento de dominio operando sobre el contrato `PuertoTurnos`.
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
from src.domain.puertos import PuertoTurnos
from src.domain.services import ServicioTurnos
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria


def test_servicio_exige_repositorio() -> None:
    """ServicioTurnos ya no tiene repositorio por defecto: sin argumento es TypeError."""
    with pytest.raises(TypeError):
        ServicioTurnos()  # type: ignore[call-arg]


def test_servicio_acepta_adaptador_en_memoria() -> None:
    """Triangulación: con el adaptador en memoria explícito el servicio queda operativo."""
    repo = RepositorioTurnosEnMemoria()
    servicio = ServicioTurnos(repo)
    assert isinstance(servicio._repositorio, RepositorioTurnosEnMemoria)
    assert isinstance(servicio._repositorio, PuertoTurnos)
    assert servicio.turnos_registrados() == []


def test_servicio_acepta_doble_de_prueba_del_puerto() -> None:
    """Triangulación: acepta cualquier objeto que implemente `PuertoTurnos`."""

    class DoblePuerto:
        def __init__(self) -> None:
            self.turnos: list[Turno] = []
            self.consultas: list[tuple] = []

        def guardar(self, turno: Turno) -> Turno:
            self.turnos.append(turno)
            return turno

        def actualizar(self, turno: Turno) -> Turno:
            self.turnos.append(turno)
            return turno

        def listar(self) -> list[Turno]:
            return list(self.turnos)

        def agregar(self, turno: Turno) -> None:
            self.turnos.append(turno)

        def buscar_activos_solapables(self, **_kwargs) -> list[Turno]:
            self.consultas.append(tuple(_kwargs))
            return []

    doble = DoblePuerto()
    servicio = ServicioTurnos(doble)
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
    )

    assert turno in doble.turnos
    assert servicio.turnos_registrados() == [turno]
    assert len(doble.consultas) == 1



def test_inyeccion_de_repositorio_personalizado() -> None:
    """ServicioTurnos delega correctamente en un puerto inyectado explícitamente."""
    repo = RepositorioTurnosEnMemoria()
    servicio = ServicioTurnos(repositorio=repo)

    prof = Profesional(nombre="Dr. Ejemplo")
    sil = Sillon(nombre="Sillón 1")
    turno = servicio.agendar_turno(
        paciente="Paciente Ficticio",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=prof,
        sillon=sil,
    )

    assert turno.id is not None
    assert repo.listar() == [turno]
    assert servicio.turnos_registrados() == [turno]


def test_puerto_detecta_conflicto_de_profesional() -> None:
    """El puerto provee los candidatos y el servicio rechaza con SolapamientoProfesionalError."""
    repo = RepositorioTurnosEnMemoria()
    servicio = ServicioTurnos(repositorio=repo)
    prof = Profesional(nombre="Dr. Ejemplo")
    sil1 = Sillon(nombre="Sillón 1")
    sil2 = Sillon(nombre="Sillón 2")

    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=prof,
        sillon=sil1,
    )

    with pytest.raises(SolapamientoProfesionalError):
        servicio.agendar_turno(
            paciente="Paciente B",
            fecha="2026-11-01",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional=prof,
            sillon=sil2,
        )


def test_puerto_detecta_conflicto_de_sillon() -> None:
    """El puerto provee los candidatos y el servicio rechaza con SolapamientoSillonError."""
    repo = RepositorioTurnosEnMemoria()
    servicio = ServicioTurnos(repositorio=repo)
    prof1 = Profesional(nombre="Dr. Ejemplo")
    prof2 = Profesional(nombre="Dra. Ejemplo")
    sil = Sillon(nombre="Sillón 1")

    servicio.agendar_turno(
        paciente="Paciente A",
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=prof1,
        sillon=sil,
    )

    with pytest.raises(SolapamientoSillonError):
        servicio.agendar_turno(
            paciente="Paciente B",
            fecha="2026-11-01",
            hora_inicio="10:15",
            hora_fin="10:45",
            profesional=prof2,
            sillon=sil,
        )


def test_transiciones_actualizan_a_traves_del_puerto() -> None:
    """confirmar, cancelar y completar actualizan el turno en el repositorio."""
    repo = RepositorioTurnosEnMemoria()
    servicio = ServicioTurnos(repositorio=repo)

    turno_p = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
        estado=PENDIENTE,
    )
    repo.agregar(turno_p)

    confirmado = servicio.confirmar(turno_p)
    assert confirmado.estado == CONFIRMADO
    assert repo.listar()[0].estado == CONFIRMADO

    completado = servicio.completar(confirmado)
    assert completado.estado == COMPLETADO
    assert repo.listar()[0].estado == COMPLETADO

    with pytest.raises(TransicionInvalidaError):
        servicio.cancelar(completado)


def test_memoria_actualizar_agrega_si_no_existe() -> None:
    """Actualizar un turno inexistente en memoria lo agrega a la lista."""
    repo = RepositorioTurnosEnMemoria()
    turno = Turno(
        profesional=Profesional(nombre="Dr. Ejemplo"),
        sillon=Sillon(nombre="Sillón 1"),
        fecha="2026-11-01",
        hora_inicio="10:00",
        hora_fin="10:30",
        paciente="Paciente Ficticio",
        id=999,
    )
    repo.actualizar(turno)
    assert repo.listar() == [turno]
