# cliente-agenda-turnos Specification

## Purpose

Proporciona al personal administrativo y profesional una interfaz web interactiva para visualizar, filtrar, agendar, gestionar transiciones de estado y reprogramar turnos clínicos en la aplicación frontend SPA.

## Requirements

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

### Requirement: Visualización matricial de agenda por franja horaria y recursos
La aplicación web SHALL ofrecer una vista matricial interactiva donde el eje vertical represente franjas horarias y el eje horizontal represente columnas de recursos clínicos (sillones o profesionales), ubicando los turnos en sus celdas correspondientes con código de colores según su estado.

#### Scenario: Visualización de matriz agrupada por sillones
- **WHEN** el usuario selecciona la fecha y el modo de agrupación por sillones
- **THEN** la grilla presenta una columna por cada sillón activo y ubica cada turno en la celda horaria coincidente con su franja `[inicio, fin)`, indicando paciente, profesional y badge de estado

#### Scenario: Visualización de matriz agrupada por profesionales
- **WHEN** el usuario selecciona la fecha y el modo de agrupación por profesionales
- **THEN** la grilla presenta una columna por cada profesional y ubica cada turno en la celda horaria coincidente con su horario, indicando paciente, sillón y badge de estado

#### Scenario: Restricción de vista matricial para rol Profesional
- **WHEN** un usuario con rol `Profesional` accede a la vista matricial
- **THEN** la interfaz bloquea el selector de modo o filtra las columnas para exhibir exclusivamente su propia agenda de atención

### Requirement: Alternancia interactiva entre vista de lista y vista matricial
La interfaz de agenda SHALL disponer de un control de alternancia que permita al usuario cambiar de manera inmediata entre la vista de lista cronológica y la vista matricial bidimensional conservando los filtros activos.

#### Scenario: Cambio de modo de visualización conservando contexto
- **WHEN** el usuario cambia el selector de vista de "Lista" a "Matriz"
- **THEN** la pantalla actualiza la renderización al formato matricial manteniendo la fecha y los recursos seleccionados sin requerir recarga completa

### Requirement: Visualización de bloqueos de sillón en la matriz
Cuando la matriz esté agrupada por sillones, el sistema SHALL representar visualmente los bloqueos de sillón vigentes por mantenimiento preventivo en las celdas horarias afectadas.

#### Scenario: Identificación de franja horaria bloqueada
- **WHEN** un sillón posee un bloqueo activo en una franja horaria de la jornada consultada
- **THEN** la celda matricial correspondiente SHALL desplegarse con estilo de inhabilitación visual y mostrar el motivo de bloqueo impidiendo agendar turnos ordinarios en dicho slot

### Requirement: Interacción directa sobre celdas matriciales
La grilla matricial SHALL permitir la apertura de acciones de gestión sobre turnos existentes o la creación rápida de nuevos turnos a partir del clic en celdas libres.

#### Scenario: Clic en turno existente de la matriz
- **WHEN** el usuario presiona un turno posicionado en una celda de la matriz
- **THEN** la aplicación despliega las acciones contextuales correspondientes a su estado (confirmar, reprogramar, cancelar o completar)

#### Scenario: Clic en celda libre de la matriz
- **WHEN** un usuario con rol autorizado presiona una celda horaria libre en una columna de sillón o profesional
- **THEN** el sistema abre el modal de nuevo turno precompletando automáticamente la fecha, la hora de inicio y el recurso de la columna
