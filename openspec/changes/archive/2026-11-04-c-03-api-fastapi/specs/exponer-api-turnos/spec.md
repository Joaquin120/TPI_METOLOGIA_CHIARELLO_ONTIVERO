# Spec Delta

## Purpose

Exponer la agenda de turnos por HTTP/JSON con un contrato estable de entrada, salida y errores, resolviendo el tenant de cada operación y manteniendo el dominio libre de dependencias de presentación y persistencia.

## ADDED Requirements

### Requirement: Health check disponible sin contexto de tenant

La API SHALL exponer `GET /api/v1/health` como verificación de disponibilidad, sin requerir tenant ni datos de negocio, y SHALL responder `200` con un cuerpo JSON que indique el estado del servicio.

#### Scenario: Health check exitoso (Camino Feliz)
- **GIVEN** una instancia de la API inicializada
- **WHEN** se solicita `GET /api/v1/health` sin encabezado de tenant
- **THEN** la respuesta es `200` con cuerpo JSON `{"status": "ok"}`

#### Scenario: Health check no consulta la base de negocio (Caso de Borde)
- **GIVEN** una instancia de la API cuyo repositorio de turnos no registra operaciones
- **WHEN** se solicita `GET /api/v1/health`
- **THEN** la respuesta es `200` y no se crea ni modifica ningún turno

### Requirement: Resolución explícita de tenant en operaciones de negocio

Toda operación de negocio SHALL ejecutarse dentro de un tenant resuelto explícitamente por la capa de presentación. Si la petición no permite resolver un tenant válido, la API SHALL rechazarla con `400` y código `TENANT_NO_RESUELTO`, y SHALL NOT ejecutar ninguna operación sobre datos.

#### Scenario: Petición sin tenant resoluble se rechaza (Error de Negocio)
- **GIVEN** una instancia de la API configurada para exigir un tenant explícito
- **WHEN** se solicita `GET /api/v1/turnos` sin encabezado `X-Tenant-ID` y sin tenant por defecto configurado
- **THEN** la respuesta es `400` con `{"error": {"code": "TENANT_NO_RESUELTO", "message": ...}}` y no se consulta ningún turno

#### Scenario: Petición con tenant válido opera solo en ese tenant (Camino Feliz)
- **GIVEN** dos tenants sembrados, cada uno con al menos un turno
- **WHEN** se solicita `GET /api/v1/turnos` con el encabezado `X-Tenant-ID` del primero
- **THEN** la respuesta es `200` y contiene únicamente los turnos del tenant indicado

### Requirement: Alta de turno delegando la doble validación al dominio

`POST /api/v1/turnos` SHALL validar el formato de entrada, resolver el tenant e invocar la operación de alta del dominio. La API SHALL NOT reimplementar ni duplicar reglas de solapamiento, y SHALL responder `201` con el turno creado, incluido su identificador y estado, cuando el dominio acepte el alta.

#### Scenario: Alta exitosa de un turno (Camino Feliz)
- **GIVEN** un tenant con "Dr. Ejemplo" y "Sillón 1" libres el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se envía `POST /api/v1/turnos` con paciente "Paciente Ficticio", profesional "Dr. Ejemplo", sillón "Sillón 1", fecha "2026-11-01", hora_inicio "10:00" y hora_fin "10:30"
- **THEN** la respuesta es `201` con `id` no nulo, los mismos datos de entrada y estado "CONFIRMADO"

#### Scenario: El turno creado por la API queda persistido (Camino Feliz)
- **GIVEN** un alta exitosa a través de `POST /api/v1/turnos`
- **WHEN** se solicita `GET /api/v1/turnos` para el mismo tenant
- **THEN** el turno creado aparece en el listado con los mismos datos y estado

#### Scenario: La API no duplica la regla de solapamiento (Caso de Borde)
- **GIVEN** un turno activo del "Dr. Ejemplo" en "Sillón 1" de "10:00" a "10:30"
- **WHEN** se envía un segundo `POST /api/v1/turnos` para el mismo profesional de "10:15" a "10:45" en "Sillón 2"
- **THEN** la API rechaza con `409` y código `SOLAPAMIENTO_PROFESIONAL` porque la decisión provino del dominio, sin una validación paralela en la capa HTTP

### Requirement: Listado de turnos acotado al tenant

`GET /api/v1/turnos` SHALL devolver `200` con la colección de turnos del tenant resuelto, y SHALL NOT incluir turnos de otros tenants. En este change el listado no aplica filtros ni paginación.

#### Scenario: Listado con turnos del tenant (Camino Feliz)
- **GIVEN** un tenant con dos turnos persistidos
- **WHEN** se solicita `GET /api/v1/turnos` con ese tenant
- **THEN** la respuesta es `200` con exactamente esos dos turnos y sus datos íntegros

#### Scenario: Turnos de otro tenant no aparecen (Error de Negocio)
- **GIVEN** un turno persistido en el tenant A y ningún turno en el tenant B
- **WHEN** se solicita `GET /api/v1/turnos` con el tenant B
- **THEN** la respuesta es `200` con una colección vacía

### Requirement: Conflicto de profesional se mapea a 409 con envelope estable

Cuando el dominio rechaza un alta por `SolapamientoProfesionalError`, la API SHALL responder `409` con el envelope `{"error": {"code": "SOLAPAMIENTO_PROFESIONAL", "message": <mensaje>}}` y SHALL NOT persistir el turno rechazado.

#### Scenario: Conflicto de profesional devuelve 409 (Error de Negocio)
- **GIVEN** un turno activo del "Dr. Ejemplo" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se envía `POST /api/v1/turnos` para el "Dr. Ejemplo" de "10:15" a "10:45" en "Sillón 2"
- **THEN** la respuesta es `409`, `error.code` es "SOLAPAMIENTO_PROFESIONAL" y `GET /api/v1/turnos` sigue mostrando un solo turno

### Requirement: Conflicto de sillón se mapea a 409 con envelope estable

Cuando el dominio rechaza un alta por `SolapamientoSillonError`, la API SHALL responder `409` con el envelope `{"error": {"code": "SOLAPAMIENTO_SILLON", "message": <mensaje>}}` y SHALL NOT persistir el turno rechazado.

#### Scenario: Conflicto de sillón devuelve 409 (Error de Negocio)
- **GIVEN** un turno activo en "Sillón 1" el "2026-11-01" de "10:00" a "10:30"
- **WHEN** se envía `POST /api/v1/turnos` para "Dra. Ejemplo" de "10:15" a "10:45" en "Sillón 1"
- **THEN** la respuesta es `409`, `error.code` es "SOLAPAMIENTO_SILLON" y el turno rechazado no se persiste

### Requirement: Transición inválida se mapea a 409 con envelope estable

Cuando una operación expuesta por la API recibe del dominio un `TransicionInvalidaError`, la API SHALL responder `409` con `{"error": {"code": "TRANSICION_INVALIDA", "message": <mensaje>}}`. El mapeo SHALL quedar registrado aunque el endpoint de cambio de estado pertenezca a un change posterior.

#### Scenario: Transición inválida devuelve 409 (Error de Negocio)
- **GIVEN** una operación HTTP que provoca `TransicionInvalidaError` en el dominio
- **WHEN** la excepción alcanza la capa de presentación
- **THEN** la respuesta es `409` con `error.code` "TRANSICION_INVALIDA" y el estado del turno no cambia

### Requirement: Validación de entrada se mapea a 422 con envelope estable

La API SHALL rechazar con `422` y envelope `{"error": {"code": "VALIDACION", "message": <detalle>}}` toda petición cuyo cuerpo o parámetros no cumplan el esquema de entrada, y SHALL NOT invocar la operación de dominio.

#### Scenario: Cuerpo inválido devuelve 422 (Error de Negocio)
- **GIVEN** una petición `POST /api/v1/turnos` a la que le falta `hora_fin`
- **WHEN** la API valida la entrada
- **THEN** la respuesta es `422` con `error.code` "VALIDACION" y no se crea ningún turno

#### Scenario: Formato de hora inválido devuelve 422 (Caso de Borde)
- **GIVEN** una petición `POST /api/v1/turnos` con `hora_inicio` "25:99"
- **WHEN** la API valida la entrada
- **THEN** la respuesta es `422` con `error.code` "VALIDACION"

### Requirement: El dominio permanece libre de HTTP y persistencia

El paquete de dominio SHALL NOT importar frameworks HTTP, bibliotecas de validación de presentación, drivers de base de datos ni módulos de repositorios o infraestructura. Esta separación SHALL verificarse de forma automática en la suite de pruebas.

#### Scenario: Guard de pureza del dominio (Caso de Borde)
- **GIVEN** el código fuente de `backend/src/domain/`
- **WHEN** se inspeccionan sus imports y referencias
- **THEN** no aparece `fastapi`, `pydantic`, `sqlite3`, `src.repositories` ni `src.infrastructure`
