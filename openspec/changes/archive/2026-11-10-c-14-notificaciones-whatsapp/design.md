# Design

## Context

El sistema cuenta actualmente con un núcleo de dominio sólido (FastAPI, SQLite, repositorio desacoplado por tenant, auditoría y métricas). Ver `proposal.md` para la motivación de negocio.
Conforme a `architecture.md` §8, las integraciones con servicios externos (en este caso WhatsApp) tienen una restricción arquitectónica estricta: **no deben bloquear ni degradar el alta de turnos**. Si el servicio de mensajería falla, tiene timeout o devuelve un error, la reserva debe confirmarse de todos modos en la base de datos local.
Asimismo, el nivel de gobernanza de este change es **ALTO** debido a que involucra comunicación directa hacia pacientes y un webhook de entrada que muta el estado de turnos y libera recursos operativos.

## Goals / Non-Goals

**Goals:**
- Implementar el puerto `ProveedorWhatsApp` en la capa de aplicación/dominio para desacoplar el core de cualquier SDK o proveedor específico (`DP-09`).
- Proveer un adaptador en memoria / simulador (`WhatsAppSimuladoAdapter`) que permita testear exhaustivamente envíos, fallas inducidas y webhooks con datos sintéticos (`RN-06`).
- Garantizar que `TurnoService.crear_turno()` despache la notificación de alta de manera no bloqueante y resiliente a errores de red (`architecture.md` §8).
- Exponer el endpoint `POST /api/v1/webhooks/whatsapp` con validación de token/firma para recibir confirmaciones y cancelaciones del paciente.
- Reutilizar el flujo de cancelación del dominio (`RN-04`) para liberar inmediatamente profesional y sillón cuando el paciente cancele vía WhatsApp, registrando la auditoría correspondiente (`C-07`).

**Non-Goals:**
- No incluye envío masivo de marketing ni campañas de difusión.
- No incluye interfaz gráfica dedicada en frontend (es puramente backend y API/webhook).
- No requiere contratar ni aprovisionar líneas reales de WhatsApp Business en este sprint (se implementa el adapter conectable con simulador integral para testing continuo).

## Decisions

### 1. Arquitectura Hexagonal para Mensajería (`DP-09`)
- **Decisión**: Crear una interfaz abstracta `ProveedorWhatsApp` (Protocol / ABC) en `backend/src/domain/puertos.py` o `backend/src/infrastructure/notificaciones/puerto.py`.
- **Implementaciones**:
  1. `WhatsAppSimuladoAdapter`: almacena los mensajes despachados en una lista/cola en memoria; permite simular caídas de red configurables para verificar la resiliencia en tests.
  2. `WhatsAppHttpAdapter`: implementación lista para proveedores reales (Meta Cloud API / Twilio) configurada vía variables de entorno.
- **Alternativa descartada**: Acoplar `requests` o un SDK propietario directamente en los endpoints o en el servicio de turnos. Se descartó porque viola la pureza del dominio y la testabilidad sin conexión a internet.

### 2. Despacho no bloqueante y tolerancia a fallos
- **Decisión**: `NotificacionesService.notificar_alta_turno()` o el despachador de eventos ejecutará el envío envolviendo la llamada al proveedor en un bloque `try/except Exception` robusto y/o utilizando `BackgroundTasks` de FastAPI.
- **Razón**: `architecture.md` §8 exige explícitamente: *"Las integraciones externas no deben bloquear el alta de turnos: la reserva se confirma con las reglas de dominio y la notificación se procesa como evento posterior"*. Si WhatsApp falla, se captura el error, se escribe en el logger/auditoría y la respuesta HTTP 201 de creación del turno retorna normalmente.

### 3. Autenticación y procesamiento del Webhook
- **Decisión**: Endpoint `POST /api/v1/webhooks/whatsapp`.
- **Seguridad**: Se valida el header de autenticación (`X-Webhook-Secret` o token de verificación configurable `WHATSAPP_WEBHOOK_SECRET`). Si la firma o secreto no coinciden, se retorna HTTP 401 Unauthorized.
- **Idempotencia y acciones**:
  - `accion: "CONFIRMAR"`: Registra la confirmación del paciente sobre el turno.
  - `accion: "CANCELAR"`: Invoca la lógica de transición a `CANCELADO` de `TurnoService`, liberando el horario del sillón y del profesional (`RN-04`).
- **Auditoría**: Se invoca `AuditoriaService.registrar()` indicando `accion="WHATSAPP_CONFIRMACION"` o `accion="WHATSAPP_CANCELACION"` con `usuario_id="SISTEMA_WHATSAPP"`.

### 4. UI Mockups
- **Decisión**: `Decision: no (no UI)`.
- **Razón**: Change 100% backend, infraestructura, APIs y webhooks. No altera vistas visuales del frontend.

## Risks / Trade-offs

- **[Riesgo] Invocación maliciosa o flooding del webhook de WhatsApp**  
  → *Mitigación*: Validación obligatoria del secreto de webhook antes de ejecutar cualquier consulta o mutación de turnos.
- **[Riesgo] Reintentos duplicados del proveedor de WhatsApp ante latencias en el webhook**  
  → *Mitigación*: Idempotencia en la cancelación/confirmación: si el turno ya fue cancelado, se retorna HTTP 200 informando el estado sin arrojar errores de concurrencia.
- **[Riesgo] Pérdida de notificaciones si el servidor colapsa antes de enviar el mensaje en background**  
  → *Mitigación*: Para la segunda etapa actual, se persiste la intención o registro del mensaje en base de datos (`notificaciones_log` o auditoría) antes o durante el despacho.

## Migration Plan

1. Crear migración `007_notificaciones.sql` (opcional tabla `notificaciones_log` con `id`, `tenant_id`, `turno_id`, `tipo`, `estado_envio`, `destinatario`, `created_at`).
2. Configurar variables opcionales en `config.py`: `WHATSAPP_PROVIDER` (default `"simulado"`), `WHATSAPP_WEBHOOK_SECRET`.
3. Rollback inmediato: si se requiere deshabilitar notificaciones, basta con configurar `WHATSAPP_PROVIDER=deshabilitado` o mantener el adapter simulado sin efectos colaterales.

