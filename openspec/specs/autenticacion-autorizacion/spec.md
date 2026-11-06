# autenticacion-autorizacion Specification

## Purpose

Proveer autenticación sin estado mediante JSON Web Tokens (JWT), control de acceso basado en roles (RBAC) y resolución no falsificable del contexto de tenant, garantizando el aislamiento de datos y el cumplimiento de la matriz de responsabilidades de la clínica.

## Requirements

### Requirement: Autenticación de usuarios mediante credenciales y emisión de JWT

La API SHALL exponer `POST /api/v1/auth/login` para autenticar usuarios con `email` y `password` contra la tabla `usuario` de su tenant. Si las credenciales coinciden y el usuario está activo, la API SHALL responder `200` con un token JWT firmado (`HS256`) con los claims `sub`, `email`, `tenant_id`, `rol` y opcionalmente `profesional_id`. Si las credenciales son incorrectas o el usuario no existe, la API SHALL responder `401` con código `CREDENCIALES_INVALIDAS`.

#### Scenario: Login exitoso devuelve token JWT y claims requeridos (Camino Feliz)
- **GIVEN** un usuario registrado con email "recepcion@ejemplo.com", rol "Recepcionista" y tenant activo
- **WHEN** se envía `POST /api/v1/auth/login` con email y contraseña correctos
- **THEN** la respuesta es `200` conteniendo `access_token` JWT con tipo "bearer", y el token decodificado contiene `tenant_id`, `sub`, `email` y `rol` "Recepcionista"

#### Scenario: Login con contraseña incorrecta se rechaza (Error de Negocio)
- **GIVEN** un usuario registrado con email "admin@ejemplo.com"
- **WHEN** se envía `POST /api/v1/auth/login` con email correcto pero contraseña equivocada
- **THEN** la respuesta es `401` con código de error "CREDENCIALES_INVALIDAS" y no se emite ningún token

#### Scenario: Login con usuario inexistente se rechaza (Error de Negocio)
- **GIVEN** ningún usuario registrado con email "fantasma@ejemplo.com"
- **WHEN** se envía `POST /api/v1/auth/login` con ese email
- **THEN** la respuesta es `401` con código de error "CREDENCIALES_INVALIDAS"

#### Scenario: Login con usuario inactivo se rechaza (Caso de Borde)
- **GIVEN** un usuario con estado activo igual a 0 en la base de datos
- **WHEN** se envía `POST /api/v1/auth/login` con credenciales válidas
- **THEN** la respuesta es `401` con código de error "CREDENCIALES_INVALIDAS"

### Requirement: Consulta de perfil de usuario autenticado

La API SHALL exponer `GET /api/v1/auth/me` requiriendo una cabecera `Authorization: Bearer <token>`. La API SHALL validar la firma criptográfica y la vigencia temporal del token. Si es válido, responderá `200` con el perfil del usuario autenticado (`id`, `email`, `tenant_id`, `rol`, `profesional_id`). Si el token está ausente, vencido o adulterado, responderá `401` con el código de error correspondiente sin revelar información interna.

#### Scenario: Consulta de perfil con token válido (Camino Feliz)
- **GIVEN** un usuario autenticado con un token JWT vigente
- **WHEN** se realiza una petición `GET /api/v1/auth/me` con la cabecera `Authorization: Bearer <token>`
- **THEN** la respuesta es `200` con los datos del usuario correspondientes a los claims del token

#### Scenario: Petición sin cabecera de autorización se rechaza (Error de Negocio)
- **GIVEN** una petición sin cabecera `Authorization`
- **WHEN** se solicita `GET /api/v1/auth/me`
- **THEN** la respuesta es `401` con código de error "NO_AUTENTICADO"

#### Scenario: Petición con token expirado se rechaza (Error de Negocio)
- **GIVEN** un token JWT cuya fecha de expiración `exp` es anterior al momento actual
- **WHEN** se solicita `GET /api/v1/auth/me` con ese token
- **THEN** la respuesta es `401` con código de error "TOKEN_EXPIRADO"

#### Scenario: Petición con firma o formato inválido se rechaza (Caso de Borde)
- **GIVEN** un token con firma no coincidente o cadena malformada
- **WHEN** se solicita `GET /api/v1/auth/me` con ese token
- **THEN** la respuesta es `401` con código de error "TOKEN_INVALIDO"

### Requirement: Control de acceso basado en roles (RBAC)

Los endpoints protegidos de la API SHALL exigir que el usuario autenticado cuente con un rol habilitado para la operación según la matriz de permisos de `actors.md`. Si el rol no pertenece a los autorizados para el recurso o acción, la API SHALL responder `403` con código `ACCESO_DENEGADO` y envelope estable, interrumpiendo el procesamiento sin alterar el estado del sistema.

#### Scenario: Usuario con rol autorizado accede a la operación (Camino Feliz)
- **GIVEN** un endpoint configurado para admitir rol "Recepcionista" o "Administrador"
- **WHEN** un usuario con rol "Recepcionista" autenticado realiza la petición
- **THEN** la verificación de autorización es exitosa y se procede a la ejecución del endpoint

#### Scenario: Usuario con rol no autorizado es rechazado con 403 (Error de Negocio)
- **GIVEN** un endpoint restringido a "Recepcionista" o "Administrador"
- **WHEN** un usuario autenticado con rol "Profesional" intenta ejecutar la acción
- **THEN** la respuesta es `403` con código de error "ACCESO_DENEGADO" y el sistema no ejecuta la operación

### Requirement: Hashing criptográfico de contraseñas

La persistencia de usuarios SHALL almacenar las contraseñas exclusivamente en forma de hash criptográfico seguro (PBKDF2-HMAC-SHA256 o bcrypt con salt aleatorio). La API SHALL NOT almacenar ni registrar contraseñas en texto plano en ningún componente de persistencia, caché o log.

#### Scenario: Contraseña se almacena hasheada y nunca en plano (Camino Feliz)
- **GIVEN** el registro o sembrado de un usuario con contraseña sintética
- **WHEN** se consulta la fila en la tabla de base de datos
- **THEN** la columna `password_hash` contiene una cadena hasheada con formato estándar y nunca el valor de la contraseña en texto plano

