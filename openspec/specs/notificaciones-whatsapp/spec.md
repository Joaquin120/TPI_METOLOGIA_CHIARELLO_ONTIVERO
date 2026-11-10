# notificaciones-whatsapp Specification

## Purpose
Permite gestionar el envío automático y desacoplado de recordatorios y avisos por WhatsApp, así como la recepción y procesamiento de respuestas de pacientes (confirmación o cancelación) mediante webhooks sin comprometer la disponibilidad ni las transacciones del sistema de turnos.

## Requirements

### Requirement: Despacho desacoplado de notificaciones ante eventos de turno
El sistema SHALL orquestar el envío de mensajes y recordatorios vía WhatsApp ante la creación de un turno o ante la proximidad de la cita (24 hs antes), sin bloquear la operación de negocio.

#### Scenario: Notificación enviada al crear un turno
- **WHEN** un recepcionista crea un turno válido para un paciente con número de teléfono
- **THEN** el sistema encola o despacha un mensaje de WhatsApp informando los datos de la reserva y opciones para confirmar o cancelar

#### Scenario: Notificación de recordatorio por proximidad
- **WHEN** se ejecuta el proceso de recordatorios para turnos programados dentro de las próximas 24 horas
- **THEN** el sistema despacha el recordatorio de asistencia por WhatsApp a los pacientes correspondientes

### Requirement: Tolerancia a fallos e independencia operativa
El sistema MUST garantizar que ningún fallo de red, caída del proveedor externo o timeout en WhatsApp bloquee, revierta o degrade la reserva o modificación de turnos en el consultorio.

#### Scenario: Fallo del proveedor de mensajería no interrumpe el agendamiento
- **WHEN** el proveedor de WhatsApp responde con error HTTP 500 o timeout durante el intento de envío
- **THEN** el turno se registra y confirma exitosamente en la base de datos y el fallo de notificación queda registrado en el log sin arrojar excepción al usuario

#### Scenario: Paciente sin teléfono registrado omite el envío
- **WHEN** se crea un turno para un paciente sin número telefónico asociado
- **THEN** el sistema omite el intento de envío de WhatsApp y registra la novedad sin interrumpir el flujo

### Requirement: Recepción y autenticación de webhooks de WhatsApp
El sistema SHALL exponer un endpoint seguro para recibir eventos entrantes de WhatsApp y validar la autenticidad del payload mediante token o firma criptográfica.

#### Scenario: Payload de webhook con firma válida aceptado
- **WHEN** se recibe una petición POST en el webhook con el token/firma de seguridad correcto
- **THEN** el sistema responde con HTTP 200 y procede a procesar la acción comunicada por el paciente

#### Scenario: Petición de webhook con firma inválida o ausente rechazada
- **WHEN** se recibe una petición POST en el webhook con firma inválida o sin autenticación
- **THEN** el sistema rechaza la solicitud con HTTP 401 o 403 y no altera ningún turno

### Requirement: Procesamiento de confirmación de asistencia desde WhatsApp
El sistema SHALL registrar la confirmación de asistencia del paciente cuando éste responda afirmativamente al mensaje de recordatorio.

#### Scenario: Confirmación exitosa recibida por webhook
- **WHEN** el webhook procesa una respuesta de confirmación para un turno en estado CONFIRMADO o PENDIENTE
- **THEN** el turno registra la confirmación de asistencia del paciente y mantiene o actualiza su estado operativo

#### Scenario: Confirmación recibida para un turno ya cancelado
- **WHEN** el webhook procesa una respuesta de confirmación para un turno que ya se encuentra en estado CANCELADO
- **THEN** el sistema responde informando que el turno ya no está activo y no revierte la cancelación

### Requirement: Procesamiento de cancelación y liberación de recursos por webhook
El sistema SHALL ejecutar la cancelación del turno y liberar inmediatamente el sillón y profesional conforme a la regla RN-04 cuando el paciente responda solicitando la cancelación.

#### Scenario: Cancelación exitosa vía WhatsApp libera recursos
- **WHEN** el webhook procesa una solicitud de cancelación válida enviada por el paciente
- **THEN** el turno cambia a estado CANCELADO y los intervalos de horario del profesional y sillón quedan disponibles para nuevas reservas

#### Scenario: Intento de cancelación sobre un turno ya completado
- **WHEN** el webhook recibe una cancelación para un turno con estado COMPLETADO
- **THEN** el sistema rechaza la cancelación sin modificar el turno y responde informando el estado definitivo

### Requirement: Trazabilidad y auditoría de eventos de mensajería
El sistema MUST registrar eventos de auditoría para cada notificación enviada, fallo de comunicación y acción de confirmación o cancelación originada vía WhatsApp.

#### Scenario: Auditoría de despacho y respuestas registradas
- **WHEN** se envía una notificación o se procesa un webhook entrante de confirmación o cancelación
- **THEN** el sistema persiste un registro de auditoría con el tenant, el turno asociado, el tipo de evento y el origen WhatsApp

