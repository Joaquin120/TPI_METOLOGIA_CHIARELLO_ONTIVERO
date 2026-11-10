# Spec Delta

## Purpose

Provee la interfaz web interactiva (Single Page Application) para la plataforma odontológica, gestionando autenticación mediante JWT, control de acceso y navegación protegida según el rol RBAC, layout responsivo y comunicación tipada con la API REST.

## ADDED Requirements

### Requirement: Autenticación de usuario mediante formulario de inicio de sesión
El sistema SHALL presentar una vista de inicio de sesión en la ruta `/login` que solicite email y contraseña, enviando las credenciales a `POST /api/v1/auth/login`; ante respuesta exitosa SHALL almacenar el token JWT, persistir el contexto del usuario autenticado y redirigir a la vista principal; y ante credenciales inválidas SHALL mostrar un mensaje de error claro sin navegar.

#### Scenario: Inicio de sesión exitoso guarda token y redirige a la vista principal (Camino Feliz)
- **GIVEN** un usuario no autenticado en la pantalla de inicio de sesión
- **WHEN** ingresa "admin@ejemplo.com" y contraseña válida "secreto123" y presiona ingresar
- **THEN** el sistema autentica contra la API, almacena el token JWT y redirige al usuario a "/agenda"

#### Scenario: Credenciales incorrectas muestran mensaje de error en pantalla (Error de Negocio)
- **GIVEN** un usuario en la pantalla de inicio de sesión
- **WHEN** ingresa credenciales erróneas o cuenta inactiva
- **THEN** el sistema muestra un mensaje de error visible indicando credenciales inválidas y permanece en "/login"

### Requirement: Cierre de sesión y limpieza de estado
El sistema SHALL proveer una acción de cierre de sesión accesible en la barra superior que elimine el token JWT y los datos de usuario del almacenamiento local, finalice el estado de sesión y redirija de forma inmediata a la vista `/login`.

#### Scenario: Cierre de sesión voluntario elimina el token y redirige a login (Camino Feliz)
- **GIVEN** un usuario con sesión activa en cualquier vista protegida
- **WHEN** hace clic en el botón de cerrar sesión
- **THEN** el sistema purga el token del almacenamiento y redirige al usuario a "/login"

### Requirement: Control de acceso a rutas protegidas por rol (RBAC)
El sistema SHALL implementar un guardián de rutas (`ProtectedRoute`) que intercepte la navegación hacia vistas privadas: si no existe sesión activa SHALL redirigir a `/login`; y si el rol del usuario no está autorizado para la ruta solicitada SHALL mostrar un aviso de acceso denegado impidiendo la interacción.

#### Scenario: Intento de acceder a ruta protegida sin sesión redirige a login (Error de Negocio)
- **GIVEN** un visitante sin sesión activa
- **WHEN** intenta ingresar directamente por URL a "/agenda" o "/recursos"
- **THEN** el sistema intercepta la navegación y lo redirige automáticamente a "/login"

#### Scenario: Acceso permitido a ruta autorizada según rol del usuario (Camino Feliz)
- **GIVEN** una usuaria autenticada con rol "Recepcionista"
- **WHEN** navega hacia la ruta "/agenda" o "/pacientes"
- **THEN** el sistema permite el render de la vista correspondiente

#### Scenario: Acceso denegado a ruta no permitida por rol (Error de Negocio)
- **GIVEN** un usuario autenticado con rol "Recepcionista" o "Profesional"
- **WHEN** intenta navegar hacia la ruta restringida "/auditoria"
- **THEN** el sistema bloquea el acceso mostrando un mensaje de permiso denegado

### Requirement: Layout general y navegación contextual por rol
El sistema SHALL renderizar un marco visual compuesto por barra superior con identidad de clínica y usuario, y barra lateral con opciones de navegación contextuales según el rol autenticado: Administrador (Agenda, Pacientes, Recursos, Auditoría), Recepcionista (Agenda, Pacientes, Recursos), y Profesional (Agenda propia).

#### Scenario: Visualización de navegación completa para el rol Administrador (Camino Feliz)
- **GIVEN** un usuario autenticado con rol "Administrador"
- **WHEN** visualiza el layout de la aplicación
- **THEN** la barra de navegación presenta enlaces a Agenda, Pacientes, Recursos y Auditoría

#### Scenario: Navegación acotada para el rol Recepcionista (Camino Feliz)
- **GIVEN** una usuaria autenticada con rol "Recepcionista"
- **WHEN** visualiza el layout de la aplicación
- **THEN** la barra de navegación presenta enlaces a Agenda, Pacientes y Recursos, excluyendo opciones administrativas

### Requirement: Cliente HTTP centralizado con inyección de token y manejo de errores
El sistema SHALL canalizar todas las peticiones a la API REST a través de un cliente HTTP centralizado que inyecte automáticamente la cabecera `Authorization: Bearer <token>` cuando exista sesión, y que ante una respuesta HTTP 401 invalide automáticamente la sesión y redirija a `/login`.

#### Scenario: Inyección automática de token Bearer en peticiones autenticadas (Camino Feliz)
- **GIVEN** una sesión activa con token JWT
- **WHEN** la aplicación consulta cualquier recurso de la API
- **THEN** la petición HTTP incluye la cabecera "Authorization: Bearer <token>"

#### Scenario: Expiración de sesión ante respuesta HTTP 401 (Caso de Borde)
- **GIVEN** un usuario navegando en la aplicación cuyo token ha expirado
- **WHEN** la API responde con código HTTP 401
- **THEN** el cliente HTTP limpia la sesión almacenada y redirige inmediatamente a "/login"
