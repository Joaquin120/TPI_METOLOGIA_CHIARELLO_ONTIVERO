# exponer-api-turnos Specification

## Purpose
Exponer la agenda de turnos por HTTP/JSON con un contrato estable de entrada, salida y errores, resolviendo el tenant de cada operación y manteniendo el dominio libre de dependencias de presentación y persistencia.

## Requirements

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

Toda operación de negocio SHALL ejecutarse dentro de un tenant resuelto a partir de la sesión autenticada del usuario (`tenant_id` en el token JWT verificado). Si la petición no permite resolver un tenant válido por carecer de credenciales o por token inválido o expirado, la API SHALL responder `401` y código `NO_AUTENTICADO` o `TOKEN_INVALIDO`, y SHALL NOT ejecutar ninguna operación sobre datos. Si el usuario no posee un rol autorizado, la API SHALL responder `403` con código `ACCESO_DENEGADO`.

#### Scenario: Petición sin tenant resoluble se rechaza (Error de Negocio)
- **GIVEN** una instancia de la API configurada para exigir un tenant explícito y autenticación activa
- **WHEN** se solicita `GET /api/v1/turnos` o `POST /api/v1/turnos` sin credenciales válidas o con token inválido
- **THEN** la respuesta es `401` con código de error "NO_AUTENTICADO" y no se consulta ni modifica ningún turno

#### Scenario: Petición con tenant válido opera solo en ese tenant (Camino Feliz)
- **GIVEN** dos tenants sembrados con turnos y un usuario autenticado perteneciente al primero
- **WHEN** se solicita `GET /api/v1/turnos` con el token JWT de dicho usuario
- **THEN** la respuesta es `200` y contiene únicamente los turnos del tenant indicado

#### Scenario: Operación de turnos por rol no autorizado se rechaza (Error de Negocio)
- **GIVEN** un usuario autenticado con rol "Profesional"
- **WHEN** intenta crear un turno mediante `POST /api/v1/turnos`
- **THEN** la respuesta es `403` con código de error "ACCESO_DENEGADO" y el turno no se crea

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

`GET /api/v1/turnos` SHALL devolver `200` con la colección de turnos del tenant resuelto, y SHALL NOT incluir turnos de otros tenants. El endpoint SHALL admitir los parámetros de consulta opcionales `fecha` (YYYY-MM-DD), `profesional_id` (entero) y `sillon_id` (entero), aplicando conjunción lógica (AND) cuando se combinan múltiples filtros.

#### Scenario: Listado con turnos del tenant (Camino Feliz)
- **GIVEN** un tenant con dos turnos persistidos
- **WHEN** se solicita `GET /api/v1/turnos` con ese tenant
- **THEN** la respuesta es `200` con exactamente esos dos turnos y sus datos íntegros

#### Scenario: Turnos de otro tenant no aparecen (Error de Negocio)
- **GIVEN** un turno persistido en el tenant A y ningún turno en el tenant B
- **WHEN** se solicita `GET /api/v1/turnos` con el tenant B
- **THEN** la respuesta es `200` con una colección vacía

#### Scenario: Filtrado por fecha específica (Camino Feliz)
- **GIVEN** un tenant con turnos registrados en fechas "2026-11-01" y "2026-11-02"
- **WHEN** se solicita `GET /api/v1/turnos?fecha=2026-11-01`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos del día "2026-11-01"

#### Scenario: Filtrado por profesional (Camino Feliz)
- **GIVEN** un tenant con turnos asignados a distintos profesionales
- **WHEN** una recepcionista solicita `GET /api/v1/turnos?profesional_id=1`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos asignados al profesional con id 1

#### Scenario: Filtrado por sillón (Camino Feliz)
- **GIVEN** un tenant con turnos en distintos sillones
- **WHEN** se solicita `GET /api/v1/turnos?sillon_id=1`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos asignados al sillón con id 1

#### Scenario: Filtrado combinado con conjunción lógica (Camino Feliz)
- **GIVEN** un tenant con múltiples turnos combinando fechas, profesionales y sillones
- **WHEN** se solicita `GET /api/v1/turnos?fecha=2026-11-01&profesional_id=1&sillon_id=2`
- **THEN** la respuesta es `200` conteniendo únicamente los turnos que cumplen simultáneamente todos los criterios

### Requirement: Restricción de agenda para rol Profesional

Cuando un usuario autenticado con rol `Profesional` consulta `GET /api/v1/turnos`, la API SHALL restringir automáticamente la respuesta a los turnos asignados a su propio `profesional_id`. Si se especifica un `profesional_id` distinto en la consulta, la API SHALL ignorarlo o responder `403` con código `ACCESO_DENEGADO`.

#### Scenario: Profesional consulta su propia agenda (Camino Feliz)
- **GIVEN** un usuario autenticado con rol "Profesional" vinculado al profesional_id 1
- **WHEN** solicita `GET /api/v1/turnos`
- **THEN** la respuesta es `200` y lista únicamente los turnos donde profesional_id es 1

#### Scenario: Profesional no puede acceder a turnos de otros profesionales (Seguridad)
- **GIVEN** un usuario autenticado con rol "Profesional" vinculado al profesional_id 1 y turnos del profesional 2
- **WHEN** intenta consultar `GET /api/v1/turnos?profesional_id=2`
- **THEN** la API rechaza con `403` y código "ACCESO_DENEGADO" o no devuelve ningún turno del profesional 2

### Requirement: Transición de estado del turno vía HTTP

`PATCH /api/v1/turnos/{id}/estado` SHALL validar el identificador del turno y el tenant resuelto, verificar los permisos del usuario (`Recepcionista` o `Administrador`), delegar la transición solicitada (`confirmar`, `cancelar` o `completar`) al dominio y responder `200` con el turno actualizado. Al cancelar, los recursos quedan inmediatamente disponibles para nuevas reservas.

#### Scenario: Cancelación exitosa de un turno y liberación de recursos (Camino Feliz)
- **GIVEN** un turno en estado "CONFIRMADO" en el tenant del usuario
- **WHEN** una recepcionista envía `PATCH /api/v1/turnos/{id}/estado` con acción "cancelar"
- **THEN** la respuesta es `200` con estado "CANCELADO" y los recursos quedan libres para agendar en ese horario

#### Scenario: Confirmación exitosa de un turno (Camino Feliz)
- **GIVEN** un turno en estado "PENDIENTE" en el tenant del usuario
- **WHEN** una recepcionista envía `PATCH /api/v1/turnos/{id}/estado` con acción "confirmar"
- **THEN** la respuesta es `200` con estado "CONFIRMADO"

#### Scenario: Finalización exitosa de un turno confirmado (Camino Feliz)
- **GIVEN** un turno en estado "CONFIRMADO" en el tenant del usuario
- **WHEN** un usuario autorizado envía `PATCH /api/v1/turnos/{id}/estado` con acción "completar"
- **THEN** la respuesta es `200` con estado "COMPLETADO"

#### Scenario: Turno inexistente o de otro tenant devuelve 404 (Error de Negocio)
- **GIVEN** un identificador de turno que no existe en el tenant autenticado
- **WHEN** se envía `PATCH /api/v1/turnos/{id}/estado` con acción "cancelar"
- **THEN** la respuesta es `404` con código de error "TURNO_NO_ENCONTRADO"

#### Scenario: Transición inválida rechazada por el dominio devuelve 409 (Error de Negocio)
- **GIVEN** un turno en estado final "CANCELADO"
- **WHEN** se envía `PATCH /api/v1/turnos/{id}/estado` con acción "completar"
- **THEN** la respuesta es `409` con código de error "TRANSICION_INVALIDA"

#### Scenario: Rol no autorizado para cambiar estado devuelve 403 (Error de Negocio)
- **GIVEN** un usuario autenticado con rol "Profesional"
- **WHEN** intenta enviar `PATCH /api/v1/turnos/{id}/estado` con acción "cancelar"
- **THEN** la respuesta es `403` con código de error "ACCESO_DENEGADO"

#### Scenario: Solicitud con acción no reconocida devuelve 422 (Error de Negocio)
- **GIVEN** un cuerpo de petición con acción "reprogramar_invalido"
- **WHEN** la API valida el esquema de entrada
- **THEN** la respuesta es `422` con código de error "VALIDACION"

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
