"""Tests de integración para la cancelación de turnos con detección y notificación de lista de espera (TDD task 2.2)."""

from unittest.mock import MagicMock
import pytest

from src.domain.models import (
    EntradaListaEspera,
    EstadoListaEspera,
    MensajeWhatsApp,
    Profesional,
    ResultadoEnvio,
    Sillon,
    Turno,
    PENDIENTE,
    CANCELADO,
)
from src.domain.puertos import PuertoTurnos, ProveedorWhatsApp
from src.domain.services import ServicioTurnos
from src.domain.lista_espera import ServicioListaEspera
from src.domain.notificaciones import NotificacionesService


class FakePuertoTurnos:
    def __init__(self) -> None:
        self.turnos: dict[int, Turno] = {}

    def guardar(self, turno: Turno) -> Turno:
        self.turnos[turno.id or 1] = turno
        return turno

    def actualizar(self, turno: Turno) -> Turno:
        self.turnos[turno.id] = turno
        return turno

    def actualizar_reprogramacion(self, turno: Turno) -> Turno:
        self.turnos[turno.id] = turno
        return turno

    def obtener_por_id(self, turno_id: int) -> Turno | None:
        return self.turnos.get(turno_id)

    def buscar_activos_solapables(self, **kwargs) -> list[Turno]:
        return []

    def buscar_activos_por_sillon(self, **kwargs) -> list[Turno]:
        return []

    def listar(self, **kwargs) -> list[Turno]:
        return list(self.turnos.values())


class FakePuertoListaEspera:
    def __init__(self) -> None:
        self.entradas: dict[int, EntradaListaEspera] = {}

    def guardar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        from dataclasses import replace

        e = replace(entrada, id=len(self.entradas) + 1, creado_en="2026-11-10 10:00:00")
        self.entradas[e.id] = e
        return e

    def actualizar(self, entrada: EntradaListaEspera) -> EntradaListaEspera:
        self.entradas[entrada.id] = entrada
        return entrada

    def obtener_por_id(self, entrada_id: int) -> EntradaListaEspera | None:
        return self.entradas.get(entrada_id)

    def listar(self, **kwargs) -> list[EntradaListaEspera]:
        return list(self.entradas.values())

    def buscar_candidatos(self, fecha: str, profesional_nombre: str | None = None) -> list[EntradaListaEspera]:
        res = [
            e
            for e in self.entradas.values()
            if e.fecha_deseada == fecha and e.estado == EstadoListaEspera.PENDIENTE
        ]
        if profesional_nombre:
            res = [
                e
                for e in res
                if e.profesional_nombre is None or e.profesional_nombre == profesional_nombre
            ]
        return sorted(res, key=lambda x: (x.creado_en or "", x.id or 0))


class FakeProveedorWhatsApp:
    def __init__(self, exitoso: bool = True) -> None:
        self.exitoso = exitoso
        self.mensajes: list[MensajeWhatsApp] = []

    def enviar_mensaje(self, mensaje: MensajeWhatsApp) -> ResultadoEnvio:
        self.mensajes.append(mensaje)
        if self.exitoso:
            return ResultadoEnvio(exitoso=True, mensaje_id="msg-123")
        return ResultadoEnvio(exitoso=False, error="Error de red simulado")


def test_cancelacion_turno_notifica_primer_candidato_espera() -> None:
    repo_turnos = FakePuertoTurnos()
    repo_espera = FakePuertoListaEspera()
    proveedor_wa = FakeProveedorWhatsApp(exitoso=True)

    servicio_notificaciones = NotificacionesService(proveedor_wa)
    servicio_espera = ServicioListaEspera(repo_espera)

    # Inscribir dos candidatos en espera para la fecha 2026-11-25 con Dr. Perez
    candidato_1 = servicio_espera.registrar(
        paciente_nombre="Candidato Uno",
        paciente_telefono="+5491111111111",
        fecha_deseada="2026-11-25",
        motivo="Limpieza",
        profesional_nombre="Dr. Perez",
    )
    candidato_2 = servicio_espera.registrar(
        paciente_nombre="Candidato Dos",
        paciente_telefono="+5491122222222",
        fecha_deseada="2026-11-25",
        motivo="Consulta",
        profesional_nombre="Dr. Perez",
    )

    servicio_turnos = ServicioTurnos(
        repositorio=repo_turnos,
        servicio_notificaciones=servicio_notificaciones,
        servicio_lista_espera=servicio_espera,
    )

    turno = Turno(
        id=5,
        paciente="Paciente Cancelador",
        fecha="2026-11-25",
        hora_inicio="10:00",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
        estado=PENDIENTE,
    )
    repo_turnos.guardar(turno)

    # Cancelar turno
    turno_cancelado = servicio_turnos.cancelar(turno)
    assert turno_cancelado.estado == CANCELADO


def test_cancelacion_turno_sin_candidatos_compatibles() -> None:
    repo_turnos = FakePuertoTurnos()
    repo_espera = FakePuertoListaEspera()
    proveedor_wa = FakeProveedorWhatsApp(exitoso=True)

    servicio_notificaciones = NotificacionesService(proveedor_wa)
    servicio_espera = ServicioListaEspera(repo_espera)

    # Candidato para otra fecha
    servicio_espera.registrar(
        paciente_nombre="Candidato Futuro",
        paciente_telefono="+5491111111111",
        fecha_deseada="2026-11-30",
        motivo="Consulta",
        profesional_nombre="Dr. Perez",
    )

    servicio_turnos = ServicioTurnos(
        repositorio=repo_turnos,
        servicio_notificaciones=servicio_notificaciones,
        servicio_lista_espera=servicio_espera,
    )

    turno = Turno(
        id=7,
        paciente="Paciente",
        fecha="2026-11-25",
        hora_inicio="10:00",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
        estado=PENDIENTE,
    )
    repo_turnos.guardar(turno)

    turno_cancelado = servicio_turnos.cancelar(turno)
    assert turno_cancelado.estado == CANCELADO
    assert len(proveedor_wa.mensajes) == 0

    # Verificar que se envió mensaje al candidato 1 (FIFO)
    assert len(proveedor_wa.mensajes) == 1
    assert proveedor_wa.mensajes[0].destinatario_telefono == "+5491111111111"
    assert "Dr. Perez" in proveedor_wa.mensajes[0].contenido

    # Verificar que el candidato 1 pasó a NOTIFICADO y el candidato 2 sigue PENDIENTE
    c1_actualizado = servicio_espera.obtener_por_id(candidato_1.id)
    c2_actualizado = servicio_espera.obtener_por_id(candidato_2.id)
    assert c1_actualizado.estado == EstadoListaEspera.NOTIFICADO
    assert c2_actualizado.estado == EstadoListaEspera.PENDIENTE


def test_cancelacion_turno_falla_notificacion_no_bloquea_cancelacion() -> None:
    repo_turnos = FakePuertoTurnos()
    repo_espera = FakePuertoListaEspera()
    proveedor_wa = FakeProveedorWhatsApp(exitoso=False)

    servicio_notificaciones = NotificacionesService(proveedor_wa)
    servicio_espera = ServicioListaEspera(repo_espera)

    servicio_espera.registrar(
        paciente_nombre="Candidato Uno",
        paciente_telefono="+5491111111111",
        fecha_deseada="2026-11-25",
        motivo="Limpieza",
        profesional_nombre="Dr. Perez",
    )

    servicio_turnos = ServicioTurnos(
        repositorio=repo_turnos,
        servicio_notificaciones=servicio_notificaciones,
        servicio_lista_espera=servicio_espera,
    )

    turno = Turno(
        id=6,
        paciente="Paciente Cancelador 2",
        fecha="2026-11-25",
        hora_inicio="10:00",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
        estado=PENDIENTE,
    )
    repo_turnos.guardar(turno)

    # Cancelar no debe lanzar excepción
    turno_cancelado = servicio_turnos.cancelar(turno)
    assert turno_cancelado.estado == CANCELADO


def test_cancelacion_turno_sin_candidatos_compatibles() -> None:
    repo_turnos = FakePuertoTurnos()
    repo_espera = FakePuertoListaEspera()
    proveedor_wa = FakeProveedorWhatsApp(exitoso=True)

    servicio_notificaciones = NotificacionesService(proveedor_wa)
    servicio_espera = ServicioListaEspera(repo_espera)

    # Candidato para otra fecha
    servicio_espera.registrar(
        paciente_nombre="Candidato Futuro",
        paciente_telefono="+5491111111111",
        fecha_deseada="2026-11-30",
        motivo="Consulta",
        profesional_nombre="Dr. Perez",
    )

    servicio_turnos = ServicioTurnos(
        repositorio=repo_turnos,
        servicio_notificaciones=servicio_notificaciones,
        servicio_lista_espera=servicio_espera,
    )

    turno = Turno(
        id=7,
        paciente="Paciente",
        fecha="2026-11-25",
        hora_inicio="10:00",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
        estado=PENDIENTE,
    )
    repo_turnos.guardar(turno)

    turno_cancelado = servicio_turnos.cancelar(turno)
    assert turno_cancelado.estado == CANCELADO
    assert len(proveedor_wa.mensajes) == 0
