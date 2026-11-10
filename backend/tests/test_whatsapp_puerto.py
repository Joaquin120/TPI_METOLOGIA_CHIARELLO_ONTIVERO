"""Tests de contrato y modelos para el puerto de WhatsApp (TDD task 1.1)."""

from src.domain.models import MensajeWhatsApp, ResultadoEnvio, TipoMensajeWhatsApp
from src.domain.puertos import ProveedorWhatsApp


def test_modelos_mensajeria_instanciacion() -> None:
    """Verifica atributos e inmutabilidad de MensajeWhatsApp y ResultadoEnvio."""
    mensaje = MensajeWhatsApp(
        destinatario_telefono="+5491112345678",
        contenido="Tu turno ha sido confirmado.",
        tipo=TipoMensajeWhatsApp.ALTA_TURNO,
        turno_id=10,
    )
    assert mensaje.destinatario_telefono == "+5491112345678"
    assert mensaje.tipo == TipoMensajeWhatsApp.ALTA_TURNO
    assert mensaje.turno_id == 10
    assert mensaje.metadata == {}

    resultado = ResultadoEnvio(
        exitoso=True,
        mensaje_id="msg-12345",
        error=None,
    )
    assert resultado.exitoso is True
    assert resultado.mensaje_id == "msg-12345"
    assert resultado.error is None


def test_puerto_whatsapp_runtime_checkable() -> None:
    """Verifica que ProveedorWhatsApp actúe como Protocol runtime_checkable."""

    class MockValido:
        def enviar_mensaje(self, mensaje: MensajeWhatsApp) -> ResultadoEnvio:
            return ResultadoEnvio(exitoso=True, mensaje_id="test-ok")

    class MockInvalido:
        pass

    assert isinstance(MockValido(), ProveedorWhatsApp)
    assert not isinstance(MockInvalido(), ProveedorWhatsApp)

