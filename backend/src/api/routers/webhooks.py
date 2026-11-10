"""Router para endpoints de webhooks entrantes (C-14, F-07)."""

from datetime import datetime
import os
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status

from src.api.esquemas import WebhookWhatsAppPeticion, WebhookWhatsAppRespuesta
from src.domain.models import CANCELADO, COMPLETADO, PENDIENTE, RegistroAuditoria
from src.domain.services import ServicioTurnos
from src.infrastructure.database import abrir_conexion
from src.repositories.auditoria_sqlite import RepositorioAuditoriaSqlite
from src.repositories.turnos_sqlite import RepositorioTurnosSqlite

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/whatsapp", response_model=WebhookWhatsAppRespuesta)
def webhook_whatsapp(
    datos: WebhookWhatsAppPeticion,
    request: Request,
    x_webhook_secret: Annotated[str | None, Header(alias="X-Webhook-Secret")] = None,
) -> WebhookWhatsAppRespuesta:
    """Procesa confirmaciones y cancelaciones enviadas por pacientes vía WhatsApp."""
    secreto_esperado = os.environ.get("WHATSAPP_WEBHOOK_SECRET", "secreto-webhook-default")
    if not x_webhook_secret or x_webhook_secret != secreto_esperado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma o secreto de webhook ausente o inválido",
        )

    conexion = abrir_conexion(request.app.state.ruta_db)
    try:
        fila = conexion.execute(
            "SELECT tenant_id FROM turno WHERE id = ?", (datos.turno_id,)
        ).fetchone()
        if fila is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Turno {datos.turno_id} no encontrado",
            )

        tenant_id = fila["tenant_id"] if isinstance(fila, sqlite3.Row) else fila[0]
        repo_turnos = RepositorioTurnosSqlite(conexion, tenant_id=tenant_id)
        servicio = ServicioTurnos(repositorio=repo_turnos)

        turno = servicio.obtener_por_id(datos.turno_id)
        if turno is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Turno {datos.turno_id} no encontrado",
            )

        repo_auditoria = RepositorioAuditoriaSqlite(conexion)
        accion_norm = datos.accion.upper()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Buscamos un usuario del tenant para atribuir la auditoría del sistema
        fila_usr = conexion.execute(
            "SELECT id FROM usuario WHERE tenant_id = ? ORDER BY id ASC LIMIT 1",
            (tenant_id,),
        ).fetchone()
        usuario_id = (
            (fila_usr["id"] if isinstance(fila_usr, sqlite3.Row) else fila_usr[0])
            if fila_usr
            else 1
        )

        if accion_norm == "CONFIRMAR":
            if turno.estado == PENDIENTE:
                turno = servicio.confirmar(turno)

            repo_auditoria.registrar(
                RegistroAuditoria(
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    accion="WHATSAPP_CONFIRMACION",
                    entidad="TURNO",
                    entidad_id=datos.turno_id,
                    detalle=f"Confirmación de asistencia recibida por WhatsApp de paciente: {turno.paciente}",
                    fecha_hora=ahora,
                )
            )

            mensaje = (
                "Asistencia confirmada exitosamente"
                if turno.estado != CANCELADO
                else "El turno ya se encontraba cancelado"
            )
            return WebhookWhatsAppRespuesta(
                mensaje=mensaje,
                turno_id=datos.turno_id,
                estado_actual=turno.estado,
                accion_procesada="CONFIRMAR",
            )

        elif accion_norm == "CANCELAR":
            if turno.estado == COMPLETADO:
                return WebhookWhatsAppRespuesta(
                    mensaje="El turno ya ha sido completado y no puede ser cancelado",
                    turno_id=datos.turno_id,
                    estado_actual=turno.estado,
                    accion_procesada="CANCELAR",
                )
            elif turno.estado == CANCELADO:
                return WebhookWhatsAppRespuesta(
                    mensaje="El turno ya se encontraba cancelado",
                    turno_id=datos.turno_id,
                    estado_actual=turno.estado,
                    accion_procesada="CANCELAR",
                )
            else:
                turno_cancelado = servicio.cancelar(turno)
                repo_auditoria.registrar(
                    RegistroAuditoria(
                        tenant_id=tenant_id,
                        usuario_id=usuario_id,
                        accion="WHATSAPP_CANCELACION",
                        entidad="TURNO",
                        entidad_id=datos.turno_id,
                        detalle=(
                            f"Cancelación de turno recibida por WhatsApp de paciente: {turno.paciente}. "
                            "Recursos liberados (RN-04)."
                        ),
                        fecha_hora=ahora,
                    )
                )
                return WebhookWhatsAppRespuesta(
                    mensaje="Turno cancelado exitosamente y recursos liberados",
                    turno_id=datos.turno_id,
                    estado_actual=turno_cancelado.estado,
                    accion_procesada="CANCELAR",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Acción '{datos.accion}' no soportada por el webhook",
            )
    finally:
        conexion.close()
