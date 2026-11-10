"""Tests de integración para el despacho de notificaciones en agendamiento de turnos (TDD task 2.2)."""

import pytest
from src.domain.notificaciones import NotificacionesService
from src.domain.models import Profesional, Sillon, TipoMensajeWhatsApp
from src.domain.services import ServicioTurnos
from src.infrastructure.whatsapp import WhatsAppSimuladoAdapter
from src.repositories.turnos_memoria import RepositorioTurnosEnMemoria


def test_agendar_turno_con_telefono_despacha_notificacion() -> None:
    """Al agendar un turno con teléfono del paciente, se despacha la notificación de WhatsApp."""
    repo = RepositorioTurnosEnMemoria()
    proveedor = WhatsAppSimuladoAdapter()
    notificaciones = NotificacionesService(proveedor=proveedor)
    servicio = ServicioTurnos(repositorio=repo, servicio_notificaciones=notificaciones)

    turno = servicio.agendar_turno(
        paciente="Ana Gomez",
        fecha="2026-11-25",
        hora_inicio="09:00",
        hora_fin="10:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
        telefono_paciente="+5491133334444",
    )

    assert turno.id is not None
    assert len(proveedor.mensajes_enviados) == 1
    msg = proveedor.mensajes_enviados[0]
    assert msg.destinatario_telefono == "+5491133334444"
    assert msg.turno_id == turno.id
    assert msg.tipo == TipoMensajeWhatsApp.ALTA_TURNO
    assert "Ana Gomez" in msg.contenido


def test_agendar_turno_sin_telefono_no_despacha_notificacion() -> None:
    """Si el teléfono es None o no se pasa, no se despacha mensaje y el turno se agenda normalmente."""
    repo = RepositorioTurnosEnMemoria()
    proveedor = WhatsAppSimuladoAdapter()
    notificaciones = NotificacionesService(proveedor=proveedor)
    servicio = ServicioTurnos(repositorio=repo, servicio_notificaciones=notificaciones)

    turno = servicio.agendar_turno(
        paciente="Lucia Diaz",
        fecha="2026-11-25",
        hora_inicio="10:00",
        hora_fin="11:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
    )

    assert turno.id is not None
    assert len(proveedor.mensajes_enviados) == 0


def test_fallo_o_excepcion_en_whatsapp_no_bloquea_alta_de_turno() -> None:
    """Garantía de architecture.md §8: el fallo del proveedor NO aborta ni lanza excepción en el alta."""
    repo = RepositorioTurnosEnMemoria()
    proveedor = WhatsAppSimuladoAdapter()
    # Configuramos fallo y excepción extrema en el proveedor
    proveedor.configurar_excepcion(activar=True, excepcion=TimeoutError("Servicio de WhatsApp no responde"))
    notificaciones = NotificacionesService(proveedor=proveedor)
    servicio = ServicioTurnos(repositorio=repo, servicio_notificaciones=notificaciones)

    # Debe completarse con éxito la reserva del turno a pesar del timeout
    turno = servicio.agendar_turno(
        paciente="Marcos Silva",
        fecha="2026-11-25",
        hora_inicio="11:00",
        hora_fin="12:00",
        profesional=Profesional(nombre="Dr. Perez"),
        sillon=Sillon(nombre="Sillón 1"),
        telefono_paciente="+5491177778888",
    )

    assert turno.id is not None
    # El turno está correctamente persistido en el repositorio
    assert repo.obtener_por_id(turno.id) is not None

