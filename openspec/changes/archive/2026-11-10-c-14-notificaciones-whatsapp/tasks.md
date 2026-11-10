# Tasks

## 1. Puerto y Adaptadores de WhatsApp (Arquitectura Hexagonal)

- [x] 1.1 Definir el puerto abstracto `ProveedorWhatsApp` y los esquemas/modelos de datos para mensajes (`MensajeWhatsApp`, `ResultadoEnvio`, `TipoMensajeWhatsApp`) en `backend/src/domain/puertos.py` o módulo de mensajería. Verificar mediante test unitario de contrato en `backend/tests/test_whatsapp_puerto.py`.
- [x] 1.2 Implementar `WhatsAppSimuladoAdapter` en `backend/src/infrastructure/` con soporte para almacenar mensajes enviados y forzar fallos/timeouts controlados en tests. Verificar con pruebas unitarias en `backend/tests/test_whatsapp_simulado.py`.

## 2. Servicio de Notificaciones y Despacho Resiliente

- [x] 2.1 Implementar `NotificacionesService` para la generación de mensajes formateados (alta de turno y recordatorio de proximidad con links/opciones de confirmación/cancelación). Verificar mediante tests unitarios en `backend/tests/test_notificaciones_servicio.py`.
- [x] 2.2 Integrar el despacho de notificación en `TurnoService.crear_turno()` asegurando no bloqueo y tolerancia absoluta a fallas de red/proveedor conforme a `architecture.md` §8. Verificar mediante tests de integración en `backend/tests/test_turnos_notificaciones.py`.

## 3. Endpoint Webhook de WhatsApp y Liberación de Recursos

- [x] 3.1 Implementar el endpoint `POST /api/v1/webhooks/whatsapp` con autenticación/validación de firma mediante `WHATSAPP_WEBHOOK_SECRET`, retornando HTTP 401/403 ante firmas ausentes o inválidas. Verificar mediante tests en `backend/tests/test_api_webhooks_whatsapp.py`.
- [x] 3.2 Implementar el procesamiento de respuestas de confirmación de turno vía webhook y su registro en `AuditoriaService`. Verificar mediante tests en `backend/tests/test_api_webhooks_whatsapp.py`.
- [x] 3.3 Implementar el procesamiento de respuestas de cancelación de turno vía webhook aplicando la regla `RN-04` (liberación del sillón y profesional) y registrando la auditoría correspondiente. Verificar mediante tests en `backend/tests/test_api_webhooks_whatsapp.py`.

## 4. Verificación Integral del Sistema

- [x] 4.1 Ejecutar la suite completa de tests unitarios y de integración del backend con `pytest` y verificar que todas las pruebas pasen en verde sin advertencias ni regresiones.

