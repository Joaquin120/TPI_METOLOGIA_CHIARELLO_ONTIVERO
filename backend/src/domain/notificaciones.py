"""Servicio de dominio para el formateo y despacho de notificaciones vía WhatsApp (C-14, F-07)."""

import logging
from src.domain.models import MensajeWhatsApp, ResultadoEnvio, TipoMensajeWhatsApp
from src.domain.puertos import ProveedorWhatsApp

logger = logging.getLogger(__name__)


class NotificacionesService:
    """Orquesta el armado y despacho desacoplado de avisos a pacientes por WhatsApp."""

    def __init__(self, proveedor: ProveedorWhatsApp) -> None:
        self._proveedor = proveedor

    def formatear_mensaje_alta(
        self,
        paciente: str,
        profesional: str,
        fecha: str,
        hora_inicio: str,
        turno_id: int | None = None,
    ) -> str:
        """Genera el mensaje estándar tras la confirmación de alta de un turno."""
        id_str = f" [Turno #{turno_id}]" if turno_id is not None else ""
        return (
            f"Hola {paciente}, tu turno odontológico{id_str} con {profesional} ha sido agendado "
            f"para el {fecha} a las {hora_inicio}. Responde CONFIRMAR para confirmar tu asistencia "
            f"o CANCELAR si no puedes asistir."
        )

    def formatear_mensaje_recordatorio(
        self,
        paciente: str,
        profesional: str,
        fecha: str,
        hora_inicio: str,
        turno_id: int | None = None,
    ) -> str:
        """Genera el mensaje recordatorio de proximidad (24 hs antes de la cita)."""
        id_str = f" [Turno #{turno_id}]" if turno_id is not None else ""
        return (
            f"Hola {paciente}, te recordamos tu turno odontológico{id_str} de mañana {fecha} a las "
            f"{hora_inicio} con {profesional}. Responde CONFIRMAR para mantener tu turno o CANCELAR para liberarlo."
        )

    def notificar_alta(
        self,
        paciente: str,
        telefono: str | None,
        profesional: str,
        fecha: str,
        hora_inicio: str,
        turno_id: int | None = None,
    ) -> ResultadoEnvio | None:
        """Despacha la notificación de alta de turno de forma segura y tolerante a fallos."""
        if not telefono or not telefono.strip():
            logger.info("Paciente sin teléfono registrado o vacío. Se omite notificación de WhatsApp.")
            return None

        contenido = self.formatear_mensaje_alta(
            paciente=paciente,
            profesional=profesional,
            fecha=fecha,
            hora_inicio=hora_inicio,
            turno_id=turno_id,
        )

        mensaje = MensajeWhatsApp(
            destinatario_telefono=telefono.strip(),
            contenido=contenido,
            tipo=TipoMensajeWhatsApp.ALTA_TURNO,
            turno_id=turno_id,
        )

        try:
            return self._proveedor.enviar_mensaje(mensaje)
        except Exception as err:
            logger.error("Error al despachar notificación de alta por WhatsApp: %s", err, exc_info=True)
            return ResultadoEnvio(exitoso=False, error=str(err))

    def notificar_recordatorio(
        self,
        paciente: str,
        telefono: str | None,
        profesional: str,
        fecha: str,
        hora_inicio: str,
        turno_id: int | None = None,
    ) -> ResultadoEnvio | None:
        """Despacha un recordatorio preventivo de forma segura y tolerante a fallos."""
        if not telefono or not telefono.strip():
            return None

        contenido = self.formatear_mensaje_recordatorio(
            paciente=paciente,
            profesional=profesional,
            fecha=fecha,
            hora_inicio=hora_inicio,
            turno_id=turno_id,
        )

        mensaje = MensajeWhatsApp(
            destinatario_telefono=telefono.strip(),
            contenido=contenido,
            tipo=TipoMensajeWhatsApp.RECORDATORIO,
            turno_id=turno_id,
        )

        try:
            return self._proveedor.enviar_mensaje(mensaje)
        except Exception as err:
            logger.error("Error al despachar recordatorio por WhatsApp: %s", err, exc_info=True)
            return ResultadoEnvio(exitoso=False, error=str(err))

