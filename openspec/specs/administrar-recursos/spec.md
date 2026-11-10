# administrar-recursos Specification

## Purpose
Permite a los administradores de la clínica dar de alta y modificar recursos clínicos (profesionales odontólogos y sillones/boxes de atención) con control de duplicados por tenant, validación de atributos operativos, trazabilidad inmutable en la bitácora de auditoría y disponibilidad inmediata para la asignación de turnos.

## Requirements

### Requirement: Alta de profesional por el administrador
El sistema SHALL exponer un endpoint `POST /api/v1/profesionales` que permita registrar un nuevo profesional en el tenant del administrador autenticado, requiriendo `nombre` no vacío y aceptando opcionalmente `matricula`, `especialidad` y `activo` (por defecto `True`), respondiendo con código HTTP 201 y la entidad creada.

#### Scenario: Alta exitosa de un profesional con datos completos (Camino Feliz)
- **GIVEN** un usuario autenticado con rol `Administrador`
- **WHEN** envía `POST /api/v1/profesionales` con nombre "Dra. Nueva", matricula "MN-9988", especialidad "Ortodoncia" y activo true
- **THEN** el sistema responde con código HTTP 201 y los datos del profesional persistido incluyendo un id numérico asignado

#### Scenario: Profesional creado queda disponible de inmediato para asignar turnos (Camino Feliz)
- **GIVEN** un profesional creado exitosamente mediante `POST /api/v1/profesionales`
- **WHEN** la recepcionista solicita crear un turno asignando a dicho profesional
- **THEN** el sistema acepta el agendamiento reconociendo al profesional en el catálogo del tenant

#### Scenario: Rechazo por nombre duplicado de profesional en el mismo tenant (Error de Negocio)
- **GIVEN** un profesional con nombre "Dr. Existente" ya registrado en el tenant
- **WHEN** el administrador intenta crear otro profesional con el mismo nombre "Dr. Existente"
- **THEN** el sistema rechaza la operación con código HTTP 409 y código de error "NOMBRE_PROFESIONAL_DUPLICADO"

### Requirement: Modificación de profesional por el administrador
El sistema SHALL exponer un endpoint `PUT /api/v1/profesionales/{id}` que permita actualizar los datos de un profesional existente dentro del tenant (`nombre`, `matricula`, `especialidad`, `activo`), respondiendo con código HTTP 200 y los datos actualizados.

#### Scenario: Modificación exitosa de datos y estado de profesional (Camino Feliz)
- **GIVEN** un profesional existente con id 1 en el tenant
- **WHEN** el administrador envía `PUT /api/v1/profesionales/1` con nombre "Dr. Pérez Modificado", especialidad "Endodoncia", matricula "MN-1234" y activo false
- **THEN** el sistema responde con código HTTP 200 y refleja los nuevos valores en persistencia

#### Scenario: Rechazo por colisión de nombre con otro profesional del tenant al editar (Error de Negocio)
- **GIVEN** dos profesionales registrados: "Dr. Uno" con id 1 y "Dr. Dos" con id 2 en el mismo tenant
- **WHEN** el administrador envía `PUT /api/v1/profesionales/2` intentando cambiar el nombre a "Dr. Uno"
- **THEN** el sistema rechaza la solicitud con código HTTP 409 y código de error "NOMBRE_PROFESIONAL_DUPLICADO"

#### Scenario: Profesional inexistente o de otro tenant devuelve 404 (Error de Negocio)
- **GIVEN** un id de profesional que no pertenece al tenant del usuario autenticado
- **WHEN** el administrador intenta modificarlo mediante `PUT /api/v1/profesionales/{id}`
- **THEN** el sistema responde con código HTTP 404 y código de error "PROFESIONAL_NO_ENCONTRADO"

### Requirement: Alta de sillón/box por el administrador
El sistema SHALL exponer un endpoint `POST /api/v1/sillones` que permita registrar un nuevo sillón/box de atención en el tenant del administrador autenticado, requiriendo `nombre` no vacío y aceptando opcionalmente `equipamiento` y `activo` (por defecto `True`), respondiendo con código HTTP 201 y la entidad creada.

#### Scenario: Alta exitosa de un sillón con equipamiento y estado (Camino Feliz)
- **GIVEN** un usuario autenticado con rol `Administrador`
- **WHEN** envía `POST /api/v1/sillones` con nombre "Sillón Quirúrgico 4", equipamiento "Turbina LED y Cavitador" y activo true
- **THEN** el sistema responde con código HTTP 201 y los datos del sillón persistido incluyendo un id numérico asignado

#### Scenario: Sillón creado queda disponible de inmediato para asignar turnos (Camino Feliz)
- **GIVEN** un sillón creado exitosamente mediante `POST /api/v1/sillones`
- **WHEN** la recepcionista solicita crear un turno asignando dicho sillón
- **THEN** el sistema acepta el agendamiento reconociendo al sillón en el catálogo del tenant

#### Scenario: Rechazo por nombre duplicado de sillón en el mismo tenant (Error de Negocio)
- **GIVEN** un sillón con nombre "Sillón Principal" ya registrado en el tenant
- **WHEN** el administrador intenta crear otro sillón con el nombre "Sillón Principal"
- **THEN** el sistema rechaza la operación con código HTTP 409 y código de error "NOMBRE_SILLON_DUPLICADO"

### Requirement: Modificación de sillón/box por el administrador
El sistema SHALL exponer un endpoint `PUT /api/v1/sillones/{id}` que permita actualizar los datos de un sillón existente dentro del tenant (`nombre`, `equipamiento`, `activo`), respondiendo con código HTTP 200 y los datos actualizados.

#### Scenario: Modificación exitosa de equipamiento y estado de sillón (Camino Feliz)
- **GIVEN** un sillón existente con id 1 en el tenant
- **WHEN** el administrador envía `PUT /api/v1/sillones/1` con nombre "Sillón 1 Renovado", equipamiento "Lámpara blanqueamiento" y activo true
- **THEN** el sistema responde con código HTTP 200 y refleja los nuevos datos en persistencia

#### Scenario: Rechazo por colisión de nombre con otro sillón del tenant al editar (Error de Negocio)
- **GIVEN** dos sillones registrados: "Sillón A" con id 1 y "Sillón B" con id 2 en el mismo tenant
- **WHEN** el administrador envía `PUT /api/v1/sillones/2` intentando cambiar el nombre a "Sillón A"
- **THEN** el sistema rechaza la solicitud con código HTTP 409 y código de error "NOMBRE_SILLON_DUPLICADO"

#### Scenario: Sillón inexistente o de otro tenant devuelve 404 (Error de Negocio)
- **GIVEN** un id de sillón que no pertenece al tenant del usuario autenticado
- **WHEN** el administrador intenta modificarlo mediante `PUT /api/v1/sillones/{id}`
- **THEN** el sistema responde con código HTTP 404 y código de error "SILLON_NO_ENCONTRADO"

### Requirement: Control de acceso RBAC estricto para administración de recursos
El sistema SHALL restringir las operaciones de alta y modificación de recursos exclusivamente al rol `Administrador`, rechazando a cualquier otro rol o peticiones anónimas.

#### Scenario: Acceso concedido a usuario con rol Administrador (Camino Feliz)
- **GIVEN** un usuario autenticado con rol `Administrador`
- **WHEN** invoca las rutas `POST` o `PUT` de profesionales o sillones
- **THEN** el sistema autoriza la operación y procesa la petición

#### Scenario: Denegación de acceso para roles Recepcionista y Profesional (Error de Negocio)
- **GIVEN** un usuario autenticado con rol `Recepcionista` o `Profesional`
- **WHEN** intenta invocar `POST /api/v1/profesionales`, `PUT /api/v1/profesionales/{id}`, `POST /api/v1/sillones` o `PUT /api/v1/sillones/{id}`
- **THEN** el sistema deniega la acción con código HTTP 403 y código de error "ACCESO_DENEGADO"

#### Scenario: Rechazo de peticiones sin autenticación (Error de Negocio)
- **WHEN** un cliente invoca las rutas administrativas de recursos sin token Bearer o con token inválido
- **THEN** el sistema responde con código HTTP 401 y código de error "NO_AUTENTICADO"

### Requirement: Registro de trazabilidad y auditoría de recursos
El sistema SHALL registrar un evento en la tabla de auditoría para cada alta o modificación exitosa de profesionales o sillones, documentando el usuario administrador actuante, la entidad afectada y el detalle de los datos.

#### Scenario: Auditoría inmutable de alta y modificación de recursos clínicos (Camino Feliz)
- **GIVEN** un administrador autenticado que crea o actualiza un profesional o sillón
- **WHEN** la operación de persistencia se completa con éxito
- **THEN** se almacena un registro en la tabla de auditoría con la acción correspondiente (`CREAR_PROFESIONAL`, `MODIFICAR_PROFESIONAL`, `CREAR_SILLON` o `MODIFICAR_SILLON`), asociando el id del recurso y el tenant del usuario

### Requirement: Validación de entrada y envelope uniforme de errores
El sistema SHALL validar que los campos obligatorios contengan texto no vacío y SHALL presentar todas las respuestas de error bajo el envelope estándar `{"error": {"code": "...", "message": "..."}}`.

#### Scenario: Rechazo de campos de texto vacíos o con solo espacios (Error de Negocio)
- **WHEN** se envía una petición de creación con nombre vacío o compuesto únicamente por espacios en blanco
- **THEN** el sistema responde con código HTTP 422 y cuerpo JSON bajo el formato estándar de error
