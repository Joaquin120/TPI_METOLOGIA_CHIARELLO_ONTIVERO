# Design

## Context

El sistema ya cuenta con el ciclo de vida completo de turnos (alta, confirmación, cancelación y reprogramación) y un subsistema de mensajería desacoplado vía WhatsApp (`C-14`). Ver `proposal.md` para la motivación.
Cuando un turno es cancelado conforme a `RN-04`, el profesional y el sillón quedan liberados inmediatamente, pero hasta ahora no existía un mecanismo para retener y recuperar la demanda de pacientes que no habían encontrado turno (`F-08`, `PA-14`).
El nivel de gobernanza de este change es **MEDIO** (lógica de negocio interna, reasignaciones y persistencia).

## Goals / Non-Goals

**Goals:**
- Definir la entidad `EntradaListaEspera` en el dominio con estados (`PENDIENTE`, `NOTIFICADO`, `ASIGNADO`, `CANCELADO`).
- Proveer el puerto `PuertoListaEspera` y el adaptador SQLite `RepositorioListaEsperaSqlite` con estricto aislamiento por `tenant_id`.
- Implementar `ServicioListaEspera` para encolar solicitudes, ordenar por prioridad FIFO (`creado_en ASC`) y buscar candidatos compatibles ante turnos liberados (`PA-14`).
- Integrar la cancelación de turnos para que dispare la búsqueda del primer candidato en espera y despache un aviso de vacante vía `NotificacionesService`.
- Exponer endpoints REST en `/api/v1/lista-espera` para crear, listar, cancelar y reasignar (creando el turno y validando sillón según `RN-01` y `RN-08`).

**Non-Goals:**
- No incluye cambios de interfaz gráfica en frontend (módulo estrictamente de backend y API REST).
- No admite excepciones por sobreturnos o urgencias que solapen recursos activos (`RN-08`).

## Decisions

### 1. Modelo de Dominio y Prioridad (`PA-14`)
- **Decisión**: La entidad `EntradaListaEspera` contendrá:
  - `id: int | None`
  - `tenant_id: int`
  - `paciente_id: int` (o nombre/teléfono del paciente)
  - `profesional_id: int | None` (opcional: si es `None`, aplica a cualquier profesional de la fecha)
  - `fecha_deseada: str` (`YYYY-MM-DD`)
  - `franja_horaria: str | None` (ej. "MAÑANA", "TARDE" o "09:00-12:00")
  - `motivo: str`
  - `estado: str` (`PENDIENTE`, `NOTIFICADO`, `ASIGNADO`, `CANCELADO`)
  - `creado_en: str`
- **Prioridad**: Se resuelve `PA-14` mediante un criterio First-In, First-Out (FIFO) determinístico: `ORDER BY creado_en ASC, id ASC`. El paciente que solicitó primero tiene prioridad para ser notificado o reasignado.

### 2. Integración ante Cancelaciones
- **Decisión**: `ServicioTurnos.cancelar(...)` o un coordinador de aplicación consultará `ServicioListaEspera.obtener_candidatos_para_intervalo(fecha, profesional_id)`. Si hay candidatos pendientes, toma al primero, actualiza su estado a `NOTIFICADO` y utiliza `NotificacionesService` para enviarle un mensaje por WhatsApp con los datos del horario vacante.
- **Resiliencia**: Esta notificación no bloquea ni revierte la cancelación del turno en curso.

### 3. Reasignación y Conversión en Turno
- **Decisión**: Endpoint `POST /api/v1/lista-espera/{id}/asignar`.
  - Recibe: `sillon: str`, `hora_inicio: str`, `hora_fin: str`, `profesional: str`.
  - Valida que la entrada esté en estado `PENDIENTE` o `NOTIFICADO`.
  - Invoca `ServicioTurnos.agendar_turno(...)` para validar el doble candado (profesional + sillón libres).
  - Si es exitoso, actualiza el estado de la entrada a `ASIGNADO` y registra auditoría (`C-09`).
  - Si hay conflicto con el sillón, lanza `409 Conflict` (`SolapamientoSillonError`).

### 4. UI Mockups
- **Decisión**: `Decision: no (no UI)`.
- **Razón**: Change de backend, infraestructura de datos y contratos REST sin impacto visual en el cliente web.

## Risks / Trade-offs

- **[Riesgo] Asignación concurrente de dos pacientes de lista de espera al mismo horario**  
  → *Mitigación*: La doble validación de recursos de `ServicioTurnos` en SQLite impide que dos turnos ocupen el mismo sillón o profesional.
- **[Riesgo] Notificación redundante al cancelar turnos que no tenían demanda en espera**  
  → *Mitigación*: La búsqueda de candidatos evalúa estrictamente `fecha = turno.fecha` y profesional compatible, retornando inmediatamente si la lista está vacía.

## Migration Plan

1. Crear migración `008_lista_espera.sql` con tabla `lista_espera` e índices `(tenant_id, fecha_deseada, estado)`.
2. Registrar el nuevo router en `src/api/app.py`.
3. Rollback directo sin impacto en tablas existentes.

