# Proposal

## Why

El ausentismo de pacientes a sus citas odontológicas genera huecos no aprovechables en la agenda y ociosidad en sillones y profesionales. Actualmente, los recordatorios y confirmaciones dependen de llamadas o seguimiento manual por parte de recepción. Implementar un subsistema de notificaciones automáticas y bidireccionales vía WhatsApp (`F-07`, `S-03`) permite enviar recordatorios oportunos (`PA-11`) y recibir confirmaciones o cancelaciones directamente del paciente, reduciendo el ausentismo y liberando inmediatamente los recursos ante cancelaciones (`RN-04`). Conforme a `architecture.md` §8 y `DP-09`, este subsistema debe estar completamente desacoplado para que ninguna degradación del proveedor externo afecte la disponibilidad o el agendamiento operativo del consultorio.

## What Changes

- **Nuevo servicio de notificaciones desacoplado**: Servicio de aplicación y orquestación de mensajes (`NotificacionesService`) impulsado por eventos de dominio (alta de turno, proximidad/recordatorio, cancelación).
- **Resiliencia y no bloqueo**: Mecanismo asíncrono o despachador protegido contra fallos (`try/catch` y registro de error) para que la caída, lentitud o rechazo de WhatsApp jamás aborte el alta de turnos ni las transacciones de negocio (`architecture.md` §8).
- **Puerto y adaptadores de mensajería (Arquitectura Hexagonal - `DP-09`)**:
  - Definición del puerto abstracto `ProveedorWhatsApp` en el dominio/aplicación.
  - Adaptador en memoria/simulador (`WhatsAppSimuladoAdapter`) para desarrollo y tests automatizados con datos sintéticos (`RN-06`).
  - Adaptador configurable para integración Cloud API (Twilio / Meta Graph WhatsApp API) mediante variables de entorno seguras (`DP-10`).
- **Endpoint Webhook de WhatsApp**:
  - Endpoint `POST /api/v1/webhooks/whatsapp` para recibir payloads de confirmación y cancelación de turnos por parte de los pacientes.
  - Validación de firma/token secreto de webhook para seguridad e integridad.
  - Procesamiento seguro: confirmación de asistencia del turno o ejecución de la cancelación del turno liberando recursos en el horario (`RN-04`) y auditando la acción como disparada por el paciente vía WhatsApp (`C-07`).
- **Plantillas y reglas de envío (`PA-11`)**:
  - Plantilla de confirmación inicial tras el alta.
  - Plantilla de recordatorio previo (24 hs antes de la cita).
  - Manejo de opt-in/teléfono de contacto asociado al paciente.

## Capabilities

### New Capabilities

- `notificaciones-whatsapp`: Cobertura completa del ciclo de vida de notificaciones y recordatorios vía WhatsApp: despacho desacoplado de avisos (alta y recordatorios de proximidad), tolerancia absoluta a fallos de red/proveedor sin bloquear el negocio, webhook seguro para recepción de respuestas de pacientes (confirmación y cancelación liberando recursos) y trazabilidad integral en auditoría.

### Modified Capabilities

(Ninguna. Las capacidades existentes de creación, estado y auditoría se consumen a través de sus contratos vigentes sin alterar sus especificaciones normativas).

## Impact

- **Backend**:
  - Nuevo módulo `backend/src/domain/puertos.py` o módulo específico de notificaciones con la interfaz `ProveedorNotificaciones` / `ProveedorWhatsApp`.
  - Nueva capa en `backend/src/infrastructure/notificaciones/` con el adaptador simulado y cliente HTTP.
  - Nuevo router en `backend/src/api/routers/webhooks.py` o `notificaciones.py` conectado en `app.py`.
  - Integración en `TurnoService` o despachador de eventos sin acoplamiento bloqueante.
- **Base de Datos / Migraciones**:
  - Opcional tabla o registro de logs de notificaciones/mensajes enviados para control de estados y reintentos, o reutilización del subsistema de auditoría existente.
- **Dependencias**:
  - Sin dependencias externas obligatorias pesadas; cliente HTTP asíncrono (`httpx` o requests estándar) o simulación pura para tests.

