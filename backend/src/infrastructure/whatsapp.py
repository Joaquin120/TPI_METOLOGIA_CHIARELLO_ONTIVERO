"""Adaptadores de mensajería externa para WhatsApp (C-14, DP-09)."""

from src.domain.models import MensajeWhatsApp, ResultadoEnvio
from src.domain.puertos import ProveedorWhatsApp


class WhatsAppSimuladoAdapter(ProveedorWhatsApp):
    """Adaptador de WhatsApp en memoria para entornos de desarrollo y pruebas."""

    def __init__(self) -> None:
        self.mensajes_enviados: list[MensajeWhatsApp] = []
        self._simular_fallo: bool = False
        self._mensaje_error: str = "Error de conexión simulado"
        self._simular_excepcion: bool = False
        self._excepcion_a_lanzar: Exception | None = None

    def configurar_fallo(self, activar: bool, mensaje_error: str = "Error de conexión simulado") -> None:
        """Configura si el adapter debe devolver un ResultadoEnvio con exitoso=False."""
        self._simular_fallo = activar
        self._mensaje_error = mensaje_error

    def configurar_excepcion(self, activar: bool, excepcion: Exception | None = None) -> None:
        """Configura si el adapter debe lanzar una excepción para evaluar tolerancia a fallos."""
        self._simular_excepcion = activar
        self._excepcion_a_lanzar = excepcion or RuntimeError("Error de red simulado")

    def limpiar(self) -> None:
        """Limpia el buzón de mensajes enviados y resetea las configuraciones."""
        self.mensajes_enviados.clear()
        self._simular_fallo = False
        self._simular_excepcion = False
        self._excepcion_a_lanzar = None

    def enviar_mensaje(self, mensaje: MensajeWhatsApp) -> ResultadoEnvio:
        """Despacha un mensaje registrándolo en memoria o simulando el comportamiento configurado."""
        if self._simular_excepcion and self._excepcion_a_lanzar:
            raise self._excepcion_a_lanzar

        if self._simular_fallo:
            return ResultadoEnvio(exitoso=False, error=self._mensaje_error)

        self.mensajes_enviados.append(mensaje)
        msg_id = f"sim-{len(self.mensajes_enviados)}-{abs(hash(mensaje.contenido)) % 10000}"
        return ResultadoEnvio(exitoso=True, mensaje_id=msg_id)

