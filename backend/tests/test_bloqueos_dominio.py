"""Pruebas unitarias de dominio para la integración de bloqueos de sillón (C-10, task 3.1 a 3.3)."""

from dataclasses import replace
import pytest

from src.domain.exceptions import (
    BloqueoNoEncontradoError,
    BloqueoSolapadoError,
    ConflictoTurnosExistentesError,
    SillonBloqueadoError,
)
from src.domain.models import BloqueoSillon, Profesional, Sillon, Turno
from src.domain.services import ServicioTurnos
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria


class RepositorioBloqueosEnMemoria:
    """Implementación de prueba de PuertoBloqueos en memoria."""

    def __init__(self) -> None:
        self._bloqueos: list[BloqueoSillon] = []

    def guardar(self, bloqueo: BloqueoSillon) -> BloqueoSillon:
        if bloqueo.id is None:
            bloqueo = replace(bloqueo, id=len(self._bloqueos) + 1)
        self._bloqueos.append(bloqueo)
        return bloqueo

    def buscar_bloqueos_solapados(
        self,
        sillon_id: int,
        fecha_hora_inicio: str,
        fecha_hora_fin: str,
        excluir_bloqueo_id: int | None = None,
    ) -> list[BloqueoSillon]:
        candidatos = []
        for b in self._bloqueos:
            if excluir_bloqueo_id is not None and b.id == excluir_bloqueo_id:
                continue
            if b.sillon_id != sillon_id:
                continue
            if b.fecha_hora_inicio < fecha_hora_fin and b.fecha_hora_fin > fecha_hora_inicio:
                candidatos.append(b)
        return candidatos

    def listar(
        self,
        sillon_id: int | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> list[BloqueoSillon]:
        res = []
        for b in self._bloqueos:
            if sillon_id is not None and b.sillon_id != sillon_id:
                continue
            if fecha_desde is not None and b.fecha_hora_fin < f"{fecha_desde} 00:00":
                continue
            if fecha_hasta is not None and b.fecha_hora_inicio > f"{fecha_hasta} 23:59":
                continue
            res.append(b)
        return res

    def obtener_por_id(self, bloqueo_id: int) -> BloqueoSillon | None:
        for b in self._bloqueos:
            if b.id == bloqueo_id:
                return b
        return None

    def eliminar(self, bloqueo_id: int) -> bool:
        for i, b in enumerate(self._bloqueos):
            if b.id == bloqueo_id:
                self._bloqueos.pop(i)
                return True
        return False


@pytest.fixture
def servicio_con_bloqueos():
    repo_turnos = RepositorioTurnosEnMemoria()
    repo_bloqueos = RepositorioBloqueosEnMemoria()
    servicio = ServicioTurnos(repositorio=repo_turnos, puerto_bloqueos=repo_bloqueos)
    return servicio, repo_turnos, repo_bloqueos


def test_agendar_turno_rechaza_sillon_bloqueado(servicio_con_bloqueos):
    servicio, _, repo_bloqueos = servicio_con_bloqueos
    repo_bloqueos.guardar(
        BloqueoSillon(
            tenant_id=1,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 08:00",
            fecha_hora_fin="2026-11-20 12:00",
            motivo="Desinfección",
        )
    )

    with pytest.raises(SillonBloqueadoError, match="bloqueado por mantenimiento"):
        servicio.agendar_turno(
            paciente="Paciente Test",
            fecha="2026-11-20",
            hora_inicio="09:00",
            hora_fin="09:30",
            profesional=Profesional(nombre="Dr. Ejemplo", id=1),
            sillon=Sillon(nombre="Sillón 1", id=1),
        )


def test_agendar_turno_contiguo_a_bloqueo_permitido(servicio_con_bloqueos):
    servicio, _, repo_bloqueos = servicio_con_bloqueos
    repo_bloqueos.guardar(
        BloqueoSillon(
            tenant_id=1,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 08:00",
            fecha_hora_fin="2026-11-20 12:00",
            motivo="Desinfección",
        )
    )

    # 12:00 a 12:30 es contiguo al fin del bloqueo: permitido
    turno = servicio.agendar_turno(
        paciente="Paciente Contiguo",
        fecha="2026-11-20",
        hora_inicio="12:00",
        hora_fin="12:30",
        profesional=Profesional(nombre="Dr. Ejemplo", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )
    assert turno.id is not None
    assert turno.estado == "CONFIRMADO"


def test_reprogramar_turno_rechaza_sillon_destino_bloqueado(servicio_con_bloqueos):
    servicio, _, repo_bloqueos = servicio_con_bloqueos

    turno = servicio.agendar_turno(
        paciente="Paciente Reprog",
        fecha="2026-11-19",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )

    repo_bloqueos.guardar(
        BloqueoSillon(
            tenant_id=1,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 14:00",
            fecha_hora_fin="2026-11-20 18:00",
            motivo="Reparación",
        )
    )

    with pytest.raises(SillonBloqueadoError, match="bloqueado por mantenimiento"):
        servicio.reprogramar(
            turno_id=turno.id,
            nueva_fecha="2026-11-20",
            nueva_hora_inicio="15:00",
            nueva_hora_fin="16:00",
        )


def test_reprogramar_turno_contiguo_a_bloqueo_permitido(servicio_con_bloqueos):
    servicio, _, repo_bloqueos = servicio_con_bloqueos

    turno = servicio.agendar_turno(
        paciente="Paciente Reprog",
        fecha="2026-11-19",
        hora_inicio="10:00",
        hora_fin="10:30",
        profesional=Profesional(nombre="Dr. Ejemplo", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )

    repo_bloqueos.guardar(
        BloqueoSillon(
            tenant_id=1,
            sillon_id=1,
            fecha_hora_inicio="2026-11-20 14:00",
            fecha_hora_fin="2026-11-20 18:00",
            motivo="Reparación",
        )
    )

    actualizado = servicio.reprogramar(
        turno_id=turno.id,
        nueva_fecha="2026-11-20",
        nueva_hora_inicio="18:00",
        nueva_hora_fin="18:30",
    )
    assert actualizado.hora_inicio == "18:00"


def test_crear_bloqueo_rechaza_si_hay_turnos_activos_salvaguarda_rp07(servicio_con_bloqueos):
    servicio, _, _ = servicio_con_bloqueos

    # Turno confirmado de 09:00 a 10:00 en sillón 1
    servicio.agendar_turno(
        paciente="Paciente Activo",
        fecha="2026-11-20",
        hora_inicio="09:00",
        hora_fin="10:00",
        profesional=Profesional(nombre="Dr. Pérez", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )

    # Intento de bloquear de 08:00 a 12:00 -> ConflictoTurnosExistentesError
    with pytest.raises(ConflictoTurnosExistentesError, match="turnos activos"):
        servicio.crear_bloqueo(
            tenant_id=1,
            sillon_id=1,
            fecha="2026-11-20",
            hora_inicio="08:00",
            hora_fin="12:00",
            motivo="Mantenimiento",
        )


def test_crear_bloqueo_permite_si_turnos_en_intervalo_estan_cancelados(servicio_con_bloqueos):
    servicio, _, _ = servicio_con_bloqueos

    turno = servicio.agendar_turno(
        paciente="Paciente Cancelado",
        fecha="2026-11-20",
        hora_inicio="09:00",
        hora_fin="10:00",
        profesional=Profesional(nombre="Dr. Pérez", id=1),
        sillon=Sillon(nombre="Sillón 1", id=1),
    )
    servicio.cancelar(turno)

    # Bloqueo permitido porque el turno está cancelado
    bloqueo = servicio.crear_bloqueo(
        tenant_id=1,
        sillon_id=1,
        fecha="2026-11-20",
        hora_inicio="08:00",
        hora_fin="12:00",
        motivo="Mantenimiento",
    )
    assert bloqueo.id is not None


def test_crear_bloqueo_rechaza_bloqueo_solapado(servicio_con_bloqueos):
    servicio, _, _ = servicio_con_bloqueos

    servicio.crear_bloqueo(
        tenant_id=1,
        sillon_id=1,
        fecha="2026-11-20",
        hora_inicio="08:00",
        hora_fin="12:00",
        motivo="Primer Bloqueo",
    )

    with pytest.raises(BloqueoSolapadoError, match="solapa"):
        servicio.crear_bloqueo(
            tenant_id=1,
            sillon_id=1,
            fecha="2026-11-20",
            hora_inicio="11:00",
            hora_fin="13:00",
            motivo="Segundo Bloqueo Solapado",
        )


def test_eliminar_bloqueo_inexistente_lanza_error(servicio_con_bloqueos):
    servicio, _, _ = servicio_con_bloqueos
    with pytest.raises(BloqueoNoEncontradoError):
        servicio.eliminar_bloqueo(9999)
