# Spec Delta

## Purpose

Permite registrar pacientes en lista de espera ante horarios no disponibles, priorizar la demanda insatisfecha por orden cronológico y reasignar turnos liberados por cancelaciones garantizando la doble validación de recursos y el aislamiento por clínica.

## ADDED Requirements

### Requirement: Registro de pacientes en lista de espera
El sistema SHALL permitir el alta de solicitudes en la lista de espera asociando paciente, fecha solicitada, profesional opcional, franja horaria preferente y motivo dentro del tenant autenticado.

#### Scenario: Alta exitosa en lista de espera
- **WHEN** un recepcionista envía una solicitud válida para incorporar a un paciente en lista de espera
- **THEN** el sistema registra la entrada con estado PENDIENTE, fecha de creación y orden de prioridad cronológico

#### Scenario: Rechazo de registro con campos requeridos ausentes
- **WHEN** se envía una solicitud sin identificar al paciente o con formato de fecha inválido
- **THEN** el sistema rechaza la petición con código HTTP 422 y no crea ningún registro

### Requirement: Consulta y filtrado de la lista de espera
El sistema SHALL exponer un endpoint para listar las solicitudes de lista de espera del tenant resuelto con soporte de filtrado opcional por fecha, profesional y estado.

#### Scenario: Listado ordenado por prioridad cronológica
- **WHEN** un usuario autorizado consulta la lista de espera sin filtros
- **THEN** el sistema devuelve las entradas del tenant ordenadas por fecha y hora de inscripción ascendente (criterio FIFO)

#### Scenario: Aislamiento multi-tenant en consulta de lista de espera
- **WHEN** un usuario del Tenant A consulta la lista de espera
- **THEN** la respuesta contiene únicamente registros pertenecientes al Tenant A y excluye los de otros tenants

### Requirement: Cancelación de entrada en lista de espera
El sistema SHALL permitir cancelar una entrada de lista de espera cuando el paciente desista o cuando recepción lo determine.

#### Scenario: Cancelación exitosa de entrada en espera
- **WHEN** recepción solicita cancelar una entrada en espera con estado PENDIENTE
- **THEN** la entrada cambia a estado CANCELADO y deja de ser considerada para futuras reasignaciones

#### Scenario: Intento de cancelar una entrada inexistente
- **WHEN** se intenta cancelar un identificador de lista de espera que no existe en el tenant
- **THEN** el sistema responde con código HTTP 404

### Requirement: Detección y notificación automática de vacantes ante cancelaciones
Al cancelarse un turno activo, el sistema SHALL buscar candidatos compatibles en lista de espera para la fecha y horario liberados y despachar el aviso de disponibilidad correspondiente.

#### Scenario: Aviso despachado al primer candidato en lista de espera
- **WHEN** se cancela un turno y existe al menos un paciente en lista de espera para esa fecha y horario
- **THEN** el sistema detecta al candidato con mayor prioridad y despacha un mensaje de notificación vía WhatsApp informando la vacante

#### Scenario: Cancelación sin pacientes en espera
- **WHEN** se cancela un turno y no existen candidatos registrados en lista de espera para ese intervalo
- **THEN** la cancelación del turno se completa normalmente sin arrojar advertencias ni excepciones

### Requirement: Reasignación y conversión a turno activo
El sistema SHALL permitir transformar una entrada de lista de espera en un turno activo, asignando un sillón disponible y verificando la regla de no solapamiento por profesional y sillón.

#### Scenario: Reasignación exitosa genera turno y marca entrada como asignada
- **WHEN** se aprueba la reasignación indicando un sillón libre para el horario de la entrada en espera
- **THEN** se crea y confirma el nuevo turno odontológico y el estado de la entrada en espera pasa a ASIGNADO

#### Scenario: Rechazo de reasignación ante conflicto de sillón
- **WHEN** se intenta reasignar la entrada indicando un sillón que ya está ocupado en ese horario
- **THEN** el sistema rechaza la operación con código HTTP 409 y mantiene la entrada en estado PENDIENTE

