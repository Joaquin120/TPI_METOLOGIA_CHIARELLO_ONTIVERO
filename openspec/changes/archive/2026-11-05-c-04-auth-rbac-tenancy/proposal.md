# Proposal

> **Trazabilidad de nombre**: `c-04-auth-rbac-tenancy` ≡ roadmap **C-04 `auth-rbac-tenancy`** (`CHANGES.md`, FASE 1, GATE 3). Nivel de Governance: **CRÍTICO**.

## Why

Actualmente la API de turnos opera sin mecanismos de autenticación ni autorización: cualquier cliente HTTP puede invocar endpoints de negocio especificando arbitrariamente la cabecera provisoria `X-Tenant-ID` o recurriendo a un tenant por defecto. Esto viola el principio de aislamiento estricto multi-tenant (`RN-05`, `D-01`) y deja expuesto el sistema a accesos indebidos y potenciales fugas de información.

`C-04` introduce la capa formal de seguridad, autenticación, control de acceso basado en roles (RBAC) y resolución determinista de tenant a partir de la sesión autenticada. Esto resuelve las decisiones pendientes `DP-03` y `DP-04`, garantizando que únicamente usuarios autenticados con credenciales válidas puedan operar la API, acotando sus acciones estrictamente a su clínica y a su perfil según la matriz de permisos de `actors.md`, desbloqueando los endpoints de agenda de `C-05`.

## What Changes

1. **Resolución de Decisiones Pendientes de Arquitectura**:
   - **`DP-03` (Estrategia de aislamiento multi-tenant)**: Se confirma para el MVP el modelo de **base de datos compartida con discriminador `tenant_id`**. El aislamiento se garantiza en tiempo de ejecución: el `tenant_id` se extrae de forma no falsificable del token de sesión (JWT) y se inyecta en los repositorios. Ningún endpoint de negocio permite inyectar o sobreescribir el tenant mediante parámetros o cabeceras libres.
   - **`DP-04` (Autenticación, autorización y sesiones)**: Se adopta un esquema **stateless con JSON Web Tokens (JWT, RFC 7519)** firmado con HMAC-SHA256 (`HS256`). Contraseñas hasheadas de forma segura con algoritmo `PBKDF2-HMAC-SHA256` con salt aleatorio. Los tokens contienen los claims mínimos requeridos: `sub` (identificador único de usuario), `email`, `tenant_id`, `rol`, y `profesional_id` (opcional, aplicable a odontólogos).

2. **Persistencia: Migración 002 y Modelo de Usuarios**:
   - Creación de migración `002_auth.sql`:
     - Tabla `usuario` con columnas: `id` (INTEGER PRIMARY KEY AUTOINCREMENT), `tenant_id` (INTEGER REFERENCES tenant(id)), `email` (TEXT NOT NULL), `password_hash` (TEXT NOT NULL), `rol` (TEXT NOT NULL CHECK (rol IN ('Administrador', 'Recepcionista', 'Profesional'))), `profesional_id` (INTEGER REFERENCES profesional(id), nullable), `activo` (INTEGER NOT NULL DEFAULT 1), y restricción `UNIQUE (tenant_id, email)`.
     - Índice sobre `(tenant_id, email)`.
   - Repositorio `RepositorioUsuariosSqlite` para buscar usuarios por email y tenant, y por identificador.
   - Semilla sintética (`seed.py`) actualizada con usuarios de prueba con contraseñas fijas para pruebas, estrictamente con datos ficticios (`RN-06`): Administrador, Recepcionista y Profesional.

3. **Endpoints de Autenticación (`/api/v1/auth`)**:
   - `POST /api/v1/auth/login`: Recibe credenciales (`email`, `password`), autentica al usuario contra la base de datos de su tenant y retorna un token JWT bearer con tiempo de expiración (`access_token`, `token_type="bearer"`, `expires_in`). En caso de credenciales inválidas o usuario inactivo, responde `401` con código `CREDENCIALES_INVALIDAS`.
   - `GET /api/v1/auth/me`: Endpoint autenticado que retorna la información del usuario actual (`id`, `email`, `tenant_id`, `rol`, `profesional_id`).

4. **Infraestructura de Seguridad y Middleware/Dependencias de FastAPI**:
   - Servicio de seguridad (`seguridad.py`): hashing y verificación de contraseñas, codificación y decodificación de tokens JWT con validación de expiración (`exp`) y firma secreta externalizada por variable de entorno (`SECRET_KEY`, `D-05`).
   - Dependencia `obtener_usuario_actual`: Extrae el token del header `Authorization: Bearer <token>`, valida firma y tiempo de expiración, y obtiene el contexto de usuario. Retorna `401` (`NO_AUTENTICADO`, `TOKEN_INVALIDO`, `TOKEN_EXPIRADO`).
   - Dependencia de autorización RBAC `requerir_rol(*roles)`: Verifica que el rol del usuario esté dentro de los roles autorizados para el endpoint. Si no lo está, responde `403` con código `ACCESO_DENEGADO`.
   - Refactor de `_resolver_tenant` y `contexto_turnos`: Se reemplaza el seam provisorio de cabecera `X-Tenant-ID` por el `tenant_id` proveniente del token JWT verificado.

5. **Protección de Endpoints Existentes y Aislamiento por Rol**:
   - `POST /api/v1/turnos` exige rol `Recepcionista` o `Administrador` (la recepcionista opera la agenda según `actors.md`).
   - `GET /api/v1/turnos` exige usuario autenticado y filtra estrictamente por el `tenant_id` de la sesión.
   - Si un profesional intenta crear un turno, la API responderá `403 ACCESO_DENEGADO`.

## Capabilities

### New Capabilities

- `autenticacion-autorizacion`: Autenticación stateless mediante JWT, gestión y hashing seguro de contraseñas de usuarios por tenant, endpoints `POST /api/v1/auth/login` y `GET /api/v1/auth/me`, control de acceso basado en roles (RBAC: Administrador, Recepcionista, Profesional) y resolución de contexto de tenant desde la sesión autenticada.

### Modified Capabilities

- `exponer-api-turnos`: La resolución de tenant deja de depender de cabeceras HTTP arbitrarias (`X-Tenant-ID`) y pasa a ser resuelta de manera obligatoria y segura desde el token JWT de la sesión autenticada. Las operaciones de agenda requieren autenticación (respondiendo `401` ante tokens ausentes o inválidos) y autorización por rol (respondiendo `403` si el rol no tiene permisos para la acción).

## Impact

- **Código afectado**:
  - `backend/src/infrastructure/migrations/002_auth.sql` (nuevo).
  - `backend/src/infrastructure/seed.py` (ampliado con usuarios sintéticos).
  - `backend/src/infrastructure/config.py` (variables `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`).
  - `backend/src/repositories/usuarios_sqlite.py` (nuevo adaptador).
  - `backend/src/api/seguridad.py` (nuevo: hashing y JWT).
  - `backend/src/api/routers/auth.py` (nuevo router `/api/v1/auth`).
  - `backend/src/api/dependencias.py` (resolución de usuario actual, RBAC y tenant desde JWT).
  - `backend/src/api/routers/turnos.py` (protección con dependencias de auth y roles).
  - `backend/src/api/esquemas.py` (esquemas de login, token y perfil de usuario).
  - `backend/src/api/errores.py` (códigos de error 401 y 403).
- **Dependencias**: Se incorpora `pyjwt` en `backend/requirements.txt` para manejo de JWT. Para hashing se utiliza `hashlib.pbkdf2_hmac` de la biblioteca estándar de Python (o `bcrypt` / `passlib`).
- **Compatibilidad**: **BREAKING en API HTTP de turnos**: las peticiones a `/api/v1/turnos` ya no aceptan llamadas anónimas con `X-Tenant-ID`; deben incluir `Authorization: Bearer <token>`. Los tests de `test_turnos_api.py` deben actualizarse para autenticarse o usar tokens válidos de fixture.
- **Gobernanza**: Cambio clasificado como **CRÍTICO** por involucrar seguridad, autenticación, control de acceso y separación criptográfica de identidades multi-tenant.

