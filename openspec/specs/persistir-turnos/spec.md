# persistir-turnos Specification

## Purpose
Persistir los turnos y sus recursos en SQLite de forma durable, aislada por tenant y configurable por entorno, de modo que la agenda sobreviva a los reinicios del proceso y toda validación de solapamiento se ejecute contra la base real respetando turnos activos e intervalos semiabiertos.

## Requirements

### Requirement: El turno agendado queda persistido y es consultable
El sistema SHALL almacenar cada turno agendado en la base de datos y SHALL devolverlo en consultas posteriores con el mismo profesional, sillón, paciente, intervalo y estado que los recibidos al agendar, incluso desde una conexión distinta a la base.

#### Scenario: El turno agendado se recupera desde la base (Camino Feliz)
- **GIVEN** una base de datos SQLite recién creada y sembrada para un tenant
- **WHEN** se agenda un turno para "Paciente Ficticio" de "10:00" a "10:30" con "Dr. Ejemplo" en "Sillón 1" el "2026-11-01"
- **AND** se consulta ese turno desde una conexión nueva sobre la misma base
- **THEN** el turno recuperado conserva profesional, sillón, paciente, fecha, intervalo y estado "CONFIRMADO"

#### Scenario: Los turnos se recuperan ordenados y completos tras reabrir la base (Camino Feliz)
- **GIVEN** dos turnos sin conflicto persistidos para el mismo tenant
- **WHEN** se consulta la lista de turnos del tenant desde una instancia nueva del servicio
- **THEN** ambos turnos aparecen con sus datos íntegros y ningún turno se pierde

### Requirement: Aislamiento por tenant en toda consulta persistente
Toda consulta y validación sobre la base SHALL ejecutarse dentro del tenant de la operación: un turno, profesional o sillón de un tenant SHALL ser invisible para cualquier operación de otro tenant (RN-05).

#### Scenario: Un turno de un tenant no es visible desde otro tenant (Esperado)
- **GIVEN** un turno persistido en el tenant "Clínica Ejemplo"
- **WHEN** se consultan los turnos desde el contexto de un segundo tenant
- **THEN** el turno del primer tenant no aparece y el segundo tenant solo ve sus propios recursos

#### Scenario: Un solapamiento no se detecta contra turnos de otro tenant (Caso de Borde)
- **GIVEN** existe un turno activo de un tenant en un intervalo dado
- **WHEN** se agenda un turno en el mismo intervalo desde el contexto de otro tenant
- **THEN** la creación es exitosa porque la validación solo consulta los turnos del tenant en curso

### Requirement: Solo los turnos activos bloquean recursos en la base
La validación de solapamiento consultada sobre la base SHALL considerar únicamente turnos en estado "PENDIENTE" o "CONFIRMADO"; un turno "CANCELADO" o "COMPLETADO" persistido SHALL dejar de bloquear profesional y sillón sin eliminar su registro (RN-04).

#### Scenario: Un turno cancelado en la base no bloquea la re-reserva (Caso de Borde)
- **GIVEN** un turno persistido en estado "CANCELADO" para "Dr. Ejemplo" en "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se solicita un nuevo turno para ese mismo profesional y sillón de "10:15" a "10:45"
- **THEN** la creación es exitosa y el turno cancelado permanece en la base como historial

#### Scenario: Un turno completado en la base tampoco bloquea (Caso de Borde)
- **GIVEN** un turno persistido en estado "COMPLETADO" para "Dr. Ejemplo" en "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se solicita un nuevo turno para ese mismo sillón de "10:15" a "10:45" con otro profesional
- **THEN** la creación es exitosa porque el turno finalizado ya no reserva recursos

### Requirement: Solapamiento evaluado con intervalos semiabiertos sobre la base
La consulta de solapamiento SHALL aplicar el criterio semiabierto `fecha_hora_inicio < :nuevo_fin AND fecha_hora_fin > :nuevo_inicio` (D-07): los turnos contiguos cuyo límite coincide exactamente no constituyen conflicto.

#### Scenario: Turnos contiguos registrados vía base de datos (Caso de Borde)
- **GIVEN** un turno activo persistido para "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se solicita agendar un turno para el mismo sillón de "10:30" a "11:00"
- **THEN** la reserva se registra sin errores de solapamiento

#### Scenario: Solape invertido rechazado vía base de datos (Error de Negocio)
- **GIVEN** un turno activo persistido para "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se solicita agendar un turno para el mismo sillón de "09:45" a "10:15"
- **THEN** el sistema rechaza la solicitud lanzando "SolapamientoSillonError"

### Requirement: Doble validación de recurso ejecutada contra la base
La validación SHALL consultar profesional y sillón de forma simultánea e independiente sobre la base y SHALL rechazar con la excepción de dominio correspondiente cuando exista conflicto en cualquiera de los dos recursos (regla dura 2).

#### Scenario: Conflicto de profesional detectado en la base (Error de Negocio)
- **GIVEN** un turno activo persistido para "Dr. Ejemplo" en "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se solicita un nuevo turno para "Dr. Ejemplo" de "10:15" a "10:45" en "Sillón 2"
- **THEN** el sistema rechaza la solicitud lanzando "SolapamientoProfesionalError"

#### Scenario: Conflicto de sillón detectado en la base (Error de Negocio)
- **GIVEN** un turno activo persistido para "Dr. Ejemplo" en "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se solicita un nuevo turno para "Dra. Ejemplo" de "10:15" a "10:45" en "Sillón 1"
- **THEN** el sistema rechaza la solicitud lanzando "SolapamientoSillonError"

### Requirement: La ruta de la base se resuelve por variables de entorno
La ubicación de la base de datos SHALL resolverse exclusivamente desde variables de entorno (D-05); el código no SHALL contener credenciales, secretos ni rutas sensibles fijas, y el repositorio no SHALL leer configuración de otro origen.

#### Scenario: La persistencia usa la base definida en el entorno (Camino Feliz)
- **GIVEN** la variable de entorno de la base apunta a un archivo dentro de una carpeta temporal
- **WHEN** se inicializa la persistencia y se agenda un turno
- **THEN** ese archivo contiene el turno creado y ningún valor de configuración está embebido en el código

### Requirement: Semilla inicial sintética y sin datos reales
La semilla inicial SHALL crear exactamente un tenant, dos profesionales y dos sillones con datos ficticios, y el repositorio, la base y los tests no SHALL contener datos reales de pacientes ni de profesionales (RN-06).

#### Scenario: Semilla sintética cargada en una base nueva (Camino Feliz)
- **GIVEN** una base de datos recién creada
- **WHEN** se ejecuta la semilla inicial
- **THEN** existen 1 tenant, 2 profesionales y 2 sillones con nombres ficticios como "Clínica Ejemplo", "Dr. Ejemplo" y "Sillón 1"

#### Scenario: La semilla se puede ejecutar más de una vez sin duplicar datos (Caso de Borde)
- **GIVEN** una base en la que la semilla ya fue ejecutada
- **WHEN** se vuelve a ejecutar la semilla
- **THEN** la base sigue teniendo exactamente 1 tenant, 2 profesionales y 2 sillones
