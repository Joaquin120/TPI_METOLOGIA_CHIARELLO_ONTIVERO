# Spec Delta

## Purpose

Permite dar de alta y consultar pacientes dentro de una clínica odontológica (tenant), garantizando unicidad de DNI por centro, validación de formato de documento y teléfono, privacidad estricta con datos sintéticos y aislamiento multi-tenant.

## ADDED Requirements

### Requirement: Alta de pacientes en el tenant
El sistema SHALL exponer un endpoint `POST /api/v1/pacientes` que permita registrar un nuevo paciente para el tenant autenticado, validando campos mínimos obligatorios (`dni`, `nombre`, `telefono`), asignando `tenant_id` desde la sesión e impidiendo que el cliente lo suministre manualmente.

#### Scenario: Alta exitosa de paciente con datos sintéticos válidos
- **GIVEN** un usuario autenticado con rol `Recepcionista` o `Administrador`
- **WHEN** envía una petición `POST /api/v1/pacientes` con `dni` numérico de 8 dígitos, `nombre` no vacío y `telefono` válido
- **THEN** el sistema registra al paciente, responde con código HTTP 201 y devuelve el objeto del paciente con su `id` asignado y los atributos registrados

#### Scenario: Rechazo por DNI duplicado en el mismo tenant
- **GIVEN** un paciente con DNI `10000001` ya registrado en el tenant 1
- **WHEN** un usuario autenticado del tenant 1 intenta registrar otro paciente con DNI `10000001`
- **THEN** el sistema rechaza la operación con código HTTP 409 y código de error `PACIENTE_DUPLICADO`

#### Scenario: Admisión del mismo DNI en tenants distintos
- **GIVEN** un paciente con DNI `10000001` registrado en el tenant 1
- **WHEN** un usuario autenticado del tenant 2 registra un paciente con DNI `10000001`
- **THEN** el sistema completa el alta con código HTTP 201 en el tenant 2 sin conflicto

#### Scenario: Rechazo por formato inválido de DNI o teléfono
- **GIVEN** un usuario autenticado con rol autorizado
- **WHEN** envía un payload donde `dni` no tiene 8 dígitos numéricos o `telefono` no cumple el formato esperado
- **THEN** el sistema rechaza la petición con código HTTP 422 y código de error `VALIDACION`

#### Scenario: Rechazo por atributos no permitidos en el cuerpo
- **GIVEN** un usuario autenticado intentando inyectar `tenant_id` o `id` en el cuerpo de la petición
- **WHEN** envía una petición `POST /api/v1/pacientes` con campos adicionales
- **THEN** el sistema rechaza la petición con código HTTP 422 y código de error `VALIDACION`

### Requirement: Consulta y filtrado de pacientes por tenant
El sistema SHALL exponer un endpoint `GET /api/v1/pacientes` que devuelve los pacientes pertenecientes al tenant del usuario autenticado, permitiendo filtrado opcional por `dni` o por `nombre`.

#### Scenario: Listado exitoso de pacientes del tenant
- **GIVEN** un usuario autenticado perteneciente a un tenant con pacientes registrados
- **WHEN** envía una petición `GET /api/v1/pacientes` sin parámetros de filtro
- **THEN** el sistema responde con código HTTP 200 y una lista con los pacientes del tenant

#### Scenario: Filtrado por DNI y nombre
- **GIVEN** pacientes registrados en el tenant con distintos DNIs y nombres
- **WHEN** el usuario consulta `GET /api/v1/pacientes?dni=10000001` o `GET /api/v1/pacientes?nombre=Ana`
- **THEN** la respuesta contiene únicamente los pacientes que coinciden con los criterios de búsqueda dentro del tenant

#### Scenario: Aislamiento horizontal estricto entre tenants
- **GIVEN** pacientes registrados en el tenant A y en el tenant B
- **WHEN** un usuario del tenant A consulta `GET /api/v1/pacientes`
- **THEN** el listado devuelto no contiene ningún registro correspondiente al tenant B

### Requirement: Control de acceso a pacientes por roles
El sistema SHALL autorizar el alta de pacientes únicamente a los roles `Recepcionista` y `Administrador`, y la consulta de pacientes a los roles `Recepcionista`, `Administrador` y `Profesional`.

#### Scenario: Alta permitida a recepcionista y administrador
- **GIVEN** un usuario autenticado con rol `Recepcionista` o `Administrador`
- **WHEN** realiza una petición `POST /api/v1/pacientes` con datos válidos
- **THEN** el sistema autoriza la operación y devuelve código HTTP 201

#### Scenario: Rechazo de alta para rol no autorizado
- **GIVEN** un usuario autenticado con un rol no autorizado para creación de pacientes
- **WHEN** intenta realizar una petición `POST /api/v1/pacientes`
- **THEN** el sistema deniega el acceso con código HTTP 403 y código de error `ACCESO_DENEGADO`

#### Scenario: Rechazo de peticiones sin autenticación
- **WHEN** un cliente invoca `POST /api/v1/pacientes` o `GET /api/v1/pacientes` sin token JWT o con token inválido
- **THEN** el sistema rechaza la solicitud con código HTTP 401 y código de error `NO_AUTENTICADO`

### Requirement: Envelope uniforme de errores
El sistema SHALL estructurar todas las respuestas de error en los endpoints de pacientes bajo el envelope uniforme `{"error": {"code": "...", "message": "..."}}`.

#### Scenario: Envelope consistente ante errores de validación y negocio
- **WHEN** ocurre un error de validación (422), conflicto (409), autenticación (401) o autorización (403)
- **THEN** la respuesta JSON contiene la clave raíz `error` con sub-claves `code` y `message` de texto legible
