# Spec Delta

## MODIFIED Requirements

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
