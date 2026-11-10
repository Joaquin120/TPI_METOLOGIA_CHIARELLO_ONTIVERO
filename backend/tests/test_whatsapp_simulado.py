"""Pruebas unitarias para WhatsAppSimuladoAdapter (TDD task 1.2)."""

import pytest
from src.domain.models import MensajeWhatsApp, TipoMensajeWhatsApp
from src.domain.puertos import ProveedorWhatsApp
from src.infrastructure.whatsapp import WhatsAppSimuladoAdapter


def test_adaptador_simulado_cumple_protocolo() -> None:
    """El adaptador implementa el puerto ProveedorWhatsApp."""
    adaptador = WhatsAppSimuladoAdapter()
    assert isinstance(adaptador, ProveedorWhatsApp)


def test_envio_exitoso_y_registro_de_mensajes() -> None:
    """Envío exitoso almacena el mensaje y devuelve resultado exitoso."""
    adaptador = WhatsAppSimuladoAdapter()
    mensaje = MensajeWhatsApp(
        destinatario_telefono="+5491100001111",
        contenido="Recordatorio de turno",
        tipo=TipoMensajeWhatsApp.RECORDATORIO,
        turno_id=42,
    )

    resultado = adaptador.enviar_mensaje(mensaje)

    assert resultado.exitoso is True
    assert resultado.mensaje_id is not None
    assert resultado.error is None
    assert len(adaptador.mensajes_enviados) == 1
    assert adaptador.mensajes_enviados[0] == mensaje


def test_simulacion_de_fallo_y_excepcion() -> None:
    """Permite configurar fallo de envío o lanzamiento de excepción para pruebas de resiliencia."""
    adaptador = WhatsAppSimuladoAdapter()
    mensaje = MensajeWhatsApp(
        destinatario_telefono="+5491100001111",
        contenido="Aviso",
    )

    # 1. Fallo controlado sin excepción (HTTP 500 simulado devuelto por proveedor)
    adaptador.configurar_fallo(activar=True, mensaje_error="503 Service Unavailable")
    res_fallo = adaptador.enviar_mensaje(mensaje)
    assert res_fallo.exitoso is False
    assert res_fallo.error == "503 Service Unavailable"

    # 2. Excepción de red / timeout no capturada internamente para testear capas superiores
    adaptador.configurar_excepcion(activar=True, excepcion=TimeoutError("Timeout al conectar con WhatsApp"))
    with pytest.raises(TimeoutError, match="Timeout al conectar"):
        adaptador.enviar_mensaje(mensaje)

    # 3. Limpieza y vuelta a la normalidad
    adaptador.configurar_fallo(activar=False)
    adaptador.configurar_excepcion(activar=False)
    adaptador.limpiar()
    assert len(adaptador.mensajes_enviados) == 0
    res_ok = adaptador.enviar_mensaje(mensaje)
    assert res_ok.exitoso is True

