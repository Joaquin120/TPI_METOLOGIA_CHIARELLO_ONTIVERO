"""Tests unitarios para NotificacionesService (TDD task 2.1)."""

import pytest
from src.domain.models import MensajeWhatsApp, ResultadoEnvio, TipoMensajeWhatsApp
from src.domain.notificaciones import NotificacionesService
from src.infrastructure.whatsapp import WhatsAppSimuladoAdapter


def test_formateo_mensajes_alta_y_recordatorio() -> None:
    """Verifica que el servicio arme mensajes claros con los datos del turno."""
    proveedor = WhatsAppSimuladoAdapter()
    servicio = NotificacionesService(proveedor=proveedor)

    texto_alta = servicio.formatear_mensaje_alta(
        paciente="Juan Perez",
        profesional="Dra. Gómez",
        fecha="2026-11-20",
        hora_inicio="10:00",
        turno_id=15,
    )
    assert "Juan Perez" in texto_alta
    assert "Dra. Gómez" in texto_alta
    assert "2026-11-20 a las 10:00" in texto_alta
    assert "CONFIRMAR" in texto_alta
    assert "CANCELAR" in texto_alta

    texto_rec = servicio.formatear_mensaje_recordatorio(
        paciente="Juan Perez",
        profesional="Dra. Gómez",
        fecha="2026-11-20",
        hora_inicio="10:00",
        turno_id=15,
    )
    assert "recordamos" in texto_rec.lower()
    assert "CONFIRMAR" in texto_rec


def test_despacho_notificacion_alta_exitoso() -> None:
    """Envío con teléfono válido despacha mensaje por WhatsApp."""
    proveedor = WhatsAppSimuladoAdapter()
    servicio = NotificacionesService(proveedor=proveedor)

    resultado = servicio.notificar_alta(
        paciente="Maria Lopez",
        telefono="+5491144445555",
        profesional="Dr. Pérez",
        fecha="2026-11-21",
        hora_inicio="14:30",
        turno_id=22,
    )

    assert resultado is not None
    assert resultado.exitoso is True
    assert len(proveedor.mensajes_enviados) == 1
    msg = proveedor.mensajes_enviados[0]
    assert msg.destinatario_telefono == "+5491144445555"
    assert msg.turno_id == 22
    assert msg.tipo == TipoMensajeWhatsApp.ALTA_TURNO


def test_paciente_sin_telefono_omite_envio() -> None:
    """Si el paciente no tiene teléfono registrado o está vacío, omite el envío sin error."""
    proveedor = WhatsAppSimuladoAdapter()
    servicio = NotificacionesService(proveedor=proveedor)

    res_none = servicio.notificar_alta(
        paciente="Anonimo",
        telefono=None,
        profesional="Dr. Pérez",
        fecha="2026-11-21",
        hora_inicio="14:30",
        turno_id=23,
    )
    assert res_none is None

    res_vacio = servicio.notificar_alta(
        paciente="Anonimo",
        telefono="   ",
        profesional="Dr. Pérez",
        fecha="2026-11-21",
        hora_inicio="14:30",
        turno_id=24,
    )
    assert res_vacio is None
    assert len(proveedor.mensajes_enviados) == 0


def test_tolerancia_a_fallos_y_excepciones_del_proveedor() -> None:
    """Si el proveedor arroja una excepción no controlada o timeout, el servicio la absorbe y retorna error sin crashear."""
    proveedor = WhatsAppSimuladoAdapter()
    proveedor.configurar_excepcion(activar=True, excepcion=ConnectionError("Fallo catastrófico de red"))
    servicio = NotificacionesService(proveedor=proveedor)

    resultado = servicio.notificar_alta(
        paciente="Carlos Sanchez",
        telefono="+5491199998888",
        profesional="Dr. Pérez",
        fecha="2026-11-21",
        hora_inicio="16:00",
        turno_id=25,
    )

    assert resultado is not None
    assert resultado.exitoso is False
    assert "Fallo catastrófico de red" in (resultado.error or "")

