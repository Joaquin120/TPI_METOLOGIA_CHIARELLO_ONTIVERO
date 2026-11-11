# Proposal

## Why

Cuando un paciente solicita atención pero no encuentra disponibilidad en la agenda (o desea un horario/profesional ya reservado), el consultorio suele perder la oportunidad de atención si no existe un registro ordenado de demanda insatisfecha. Al mismo tiempo, cuando otro paciente cancela su cita (`RN-04`), el horario liberado corre el riesgo de quedar ocioso si recepción no contacta inmediatamente a un paciente en espera. La gestión de Lista de Espera y Reasignación (`F-08`, `PA-14`) permite registrar el interés de pacientes por fechas o franjas horarias ocupadas, establecer prioridades y notificar o reasignar automáticamente los turnos cancelados respetando la doble validación física (`RN-01`, `RN-08`).

## What Changes

- **Modelo y ciclo de vida de Lista de Espera**:
  - Entidad de dominio `EntradaListaEspera` que vincula paciente, profesional (opcional o requerido), fecha deseada, franja horaria preferente, motivo y estado (`PENDIENTE`, `NOTIFICADO`, `ASIGNADO`, `CANCELADO`).
  - Criterio de orden y prioridad cronológica (FIFO por fecha de inscripción) con soporte para ponderación de urgencias o preferencias (`PA-14`).
- **Endpoints de API para Recepción y Gestión**:
  - `POST /api/v1/lista-espera`: registrar un paciente en la lista de espera con validación de paciente y tenant.
  - `GET /api/v1/lista-espera`: listar pacientes en espera con filtros por fecha, profesional y estado.
  - `PATCH /api/v1/lista-espera/{id}/cancelar`: dar de baja una solicitud de espera a petición del paciente o recepción.
  - `POST /api/v1/lista-espera/{id}/asignar`: convertir la entrada en espera en un turno activo, asignando sillón y validando que no existan conflictos de solapamiento (`RN-01`, `RN-08`).
- **Integración con Cancelación y Notificaciones (`F-07` / `C-14`)**:
  - Servicio de dominio/aplicación que, ante la cancelación de un turno (desde recepción o vía webhook de WhatsApp), detecta candidatos compatibles en lista de espera y despacha una notificación de oportunidad vacante al paciente prioritario.
- **Persistencia en SQLite y Trazabilidad**:
  - Tabla `lista_espera` con aislamiento estricto por `tenant_id`.
  - Pistas de auditoría (`C-09`) para cada alta, notificación, reasignación o cancelación de lista de espera.

## Capabilities

### New Capabilities

- `lista-espera`: Gestión integral del registro de pacientes en lista de espera para turnos no disponibles, priorización cronológica, detección automática de candidatos ante cancelaciones de citas, despacho de avisos por WhatsApp y reasignación directa de turnos validando disponibilidad de profesional y sillón.

### Modified Capabilities

(Ninguna. Se consumen los servicios de turnos y notificaciones mediante sus puertos y contratos existentes sin modificar sus requerimientos).

## Impact

- **Backend**:
  - Nuevas entidades y excepciones en `backend/src/domain/` (`EntradaListaEspera`, `EstadoListaEspera`).
  - Puerto de persistencia `PuertoListaEspera` en `backend/src/domain/puertos.py`.
  - Migración `008_lista_espera.sql` en `backend/src/infrastructure/migrations/`.
  - Adaptador `RepositorioListaEsperaSqlite` en `backend/src/repositories/lista_espera_sqlite.py`.
  - Router `backend/src/api/routers/lista_espera.py` incluido en `app.py`.
- **Integraciones**:
  - Utiliza `NotificacionesService` para emitir mensajes a pacientes cuando se libera un slot vacante.

