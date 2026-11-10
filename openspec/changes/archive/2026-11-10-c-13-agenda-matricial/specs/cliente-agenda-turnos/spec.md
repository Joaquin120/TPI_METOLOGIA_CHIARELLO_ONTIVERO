# Spec Delta

## ADDED Requirements

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

