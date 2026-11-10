# Spec Delta

## Purpose

Proporciona al personal administrativo y profesional una interfaz web interactiva para visualizar, filtrar, agendar, gestionar transiciones de estado y reprogramar turnos clínicos en la aplicación frontend SPA.

## ADDED Requirements

### Requirement: Visualización y filtrado de turnos en grilla operativa
La aplicación web SHALL mostrar los turnos correspondientes a la fecha seleccionada en una grilla o lista cronológica, permitiendo filtrar por profesional y sillón odontológico, reflejando el estado de cada turno mediante etiquetas y códigos de color normalizados.

#### Scenario: Consulta de turnos de una fecha con filtros activos
- **WHEN** el usuario selecciona una fecha, profesional o sillón en los controles de filtro
- **THEN** la vista consulta la API con los parámetros correspondientes y actualiza la lista de turnos mostrando horario, paciente, profesional, sillón y estado visual

#### Scenario: Restricción de visualización para rol Profesional
- **WHEN** un usuario autenticado con rol `Profesional` accede a la vista de agenda
- **THEN** el selector de profesional SHALL quedar bloqueado en su propio identificador y la consulta solo SHALL solicitar y mostrar los turnos asignados a dicho profesional

### Requirement: Alta de turno desde interfaz web con feedback de solapamiento
La aplicación web SHALL ofrecer un formulario modal para registrar un nuevo turno seleccionando paciente, profesional, sillón, fecha y franja horaria semiabierta `[inicio, fin)`, gestionando el éxito y los posibles rechazos por solapamiento de recursos sin recargar la página.

#### Scenario: Alta exitosa de turno clínico
- **WHEN** el usuario completa los datos requeridos sin conflictos de agenda y confirma el formulario
- **THEN** el sistema envía la solicitud POST a la API, cierra el modal, muestra una notificación de éxito y refresca la grilla de turnos reflejando el nuevo registro

#### Scenario: Intento de alta con solapamiento de horario
- **WHEN** el usuario intenta agendar un turno que colisiona con otro turno activo del mismo profesional o sillón y la API responde con código HTTP 409
- **THEN** el formulario modal SHALL permanecer abierto y desplegar un mensaje claro de error indicando el conflicto de solapamiento detectado

### Requirement: Transición de estados de turno en la interfaz
La interfaz web SHALL exponer acciones contextuales directas sobre cada turno para permitir su confirmación, cancelación o finalización según las reglas de transición vigentes.

#### Scenario: Confirmación de un turno en estado pendiente
- **WHEN** el usuario presiona la acción de confirmar sobre un turno en estado `PENDIENTE`
- **THEN** la aplicación envía la solicitud de confirmación a la API y actualiza la tarjeta del turno al estado `CONFIRMADO` con su correspondiente indicador verde

#### Scenario: Cancelación de turno con confirmación de liberación
- **WHEN** el usuario solicita cancelar un turno activo y ratifica la advertencia de liberación de horario
- **THEN** la aplicación ejecuta la cancelación vía API y actualiza el estado a `CANCELADO` o lo remueve de los turnos activos de la jornada

#### Scenario: Finalización de turno atendido
- **WHEN** el usuario marca un turno confirmado como completado tras la atención clínica
- **THEN** la aplicación envía la actualización a la API y el turno pasa visualmente a estado `COMPLETADO`

### Requirement: Reprogramación interactiva de turnos
La aplicación web SHALL proveer un modal de reprogramación para turnos existentes que permita modificar la fecha y el horario `[inicio, fin)` respetando la disponibilidad de los recursos.

#### Scenario: Reprogramación exitosa de horario
- **WHEN** el usuario define un nuevo horario libre para un turno existente y confirma el cambio
- **THEN** el sistema envía la solicitud de reprogramación a la API, actualiza la agenda y muestra la cita en su nuevo bloque horario

