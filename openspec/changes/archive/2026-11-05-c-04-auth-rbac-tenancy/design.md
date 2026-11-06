# Design

## Context

El sistema cuenta actualmente con un núcleo de dominio puro (`src/domain/`), adaptadores de repositorio en SQLite (`src/repositories/`), migraciones iniciales (`001_init.sql`) y una capa API con FastAPI (`src/api/`) introducida en C-03.

En C-03 se dejó explícitamente preparado el seam `_resolver_tenant` dentro de `src/api/dependencias.py` para ser sustituido por la resolución desde la sesión autenticada. Hasta el momento, las peticiones HTTP a `/api/v1/turnos` podían enviar la cabecera `X-Tenant-ID` de forma libre o depender de un tenant por defecto. Esta arquitectura requiere cerrarse formalmente con autenticación criptográfica y control de acceso por rol (RBAC) conforme a `knowledge-base/actors.md` y `knowledge-base/architecture.md` §5 y §11.

## Goals / Non-Goals

**Goals:**
- Implementar la migración `002_auth.sql` con la tabla `usuario` asociada a `tenant` y `profesional`.
- Resolver las decisiones de arquitectura `DP-03` (aislamiento multi-tenant en SQLite con discriminador) y `DP-04` (autenticación JWT stateless + PBKDF2).
- Crear el repositorio `RepositorioUsuariosSqlite` para autenticar y recuperar usuarios.
- Implementar los endpoints de autenticación `POST /api/v1/auth/login` y `GET /api/v1/auth/me` con esquemas Pydantic v2.
- Proveer dependencias FastAPI reutilizables (`obtener_usuario_actual`, `requerir_rol`) para validar tokens bearer y restringir accesos según rol (`Administrador`, `Recepcionista`, `Profesional`).
- Reemplazar el seam provisorio `_resolver_tenant` para que el `tenant_id` se derive obligatoriamente del token JWT del usuario autenticado.
- Proteger los endpoints de turnos (`POST /api/v1/turnos` restringido a recepción/administración; `GET /api/v1/turnos` acotado al tenant del usuario).
- Validar mediante suite completa con SQLite real (regla dura 5) el login feliz, rechazo de credenciales, expiración de tokens, control de roles y prevención estricta de fugas entre tenants.

**Non-Goals:**
- No implementar vistas, formularios ni interfaz gráfica (el frontend corresponde a la Fase 4, `C-11` y `C-12`).
- No implementar mecanismos complejos de rotación de refresh tokens ni listas de revocación distribuida en Redis para este MVP.
- No alterar las entidades ni los servicios del dominio: `src/domain/` permanece 100% puro y ajeno a tokens, HTTP y contraseñas.
- No implementar registro público de usuarios ni autoservicio de pacientes (`PA-05` permanece fuera de este change).

## Decisions

### D1: Resolución de DP-03 — Base compartida con discriminador `tenant_id`
- **Decisión**: Para el MVP, se confirma el modelo de base de datos compartida en SQLite donde cada entidad (`tenant`, `usuario`, `profesional`, `sillon`, `paciente`, `turno`) contiene una columna `tenant_id` con clave foránea a `tenant(id)`.
- **Racionalidad**: SQLite es la base de desarrollo y pruebas acordada (`D-04`). Este enfoque satisface el aislamiento estricto exigido por `RN-05` garantizando que toda consulta filtre por `tenant_id`, sin introducir la sobrecarga operativa de gestionar múltiples archivos de base de datos o migraciones dinámicas concurrentes.
- **Alternativas consideradas**:
  - *Base de datos separada por tenant*: Añade complejidad en la gestión de conexiones y pool en SQLite sin aportar beneficios inmediatos en el volumen actual del MVP.

### D2: Resolución de DP-04 — Autenticación stateless con JWT (HS256) y Hashing PBKDF2
- **Decisión**:
  - Autenticación mediante tokens JWT firmados con clave secreta (`SECRET_KEY`) utilizando el algoritmo `HS256` provisto por `pyjwt`.
  - Claims del token: `sub` (identificador del usuario en formato string), `email`, `tenant_id`, `rol`, y `profesional_id` (opcional).
  - Almacenamiento seguro de contraseñas utilizando `hashlib.pbkdf2_hmac` (`sha256`) con salt criptográfico aleatorio de 16 bytes y 100.000 iteraciones, serializado como `salt$hash`.
- **Racionalidad**: PBKDF2 forma parte de la biblioteca estándar de Python, garantizando portabilidad absoluta en cualquier sistema operativo sin dependencias binarias C problemáticas. JWT permite una verificación rápida e independiente del estado del servidor para cada petición.
- **Alternativas consideradas**:
  - *Bcrypt / Argon2*: Requieren compiladores C o ruedas precompiladas que pueden presentar fricción en entornos Windows restrictivos.
  - *Sesiones con cookies y estado en servidor*: Exige almacenamiento de sesiones persistente o en memoria compartida, complicando los tests y el desacople de la API.

### D3: Diseño de la tabla `usuario` y Migración 002
- **Decisión**: Crear `backend/src/infrastructure/migrations/002_auth.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS usuario (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tenant_id INTEGER NOT NULL REFERENCES tenant(id),
      email TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      rol TEXT NOT NULL CHECK (rol IN ('Administrador', 'Recepcionista', 'Profesional')),
      profesional_id INTEGER REFERENCES profesional(id),
      activo INTEGER NOT NULL DEFAULT 1,
      UNIQUE (tenant_id, email)
  );
  CREATE INDEX IF NOT EXISTS idx_usuario_tenant_email ON usuario (tenant_id, email);
  ```
- **Racionalidad**: `UNIQUE (tenant_id, email)` permite que un mismo email hipotético pueda existir en clínicas distintas sin colisión, garantizando el aislamiento multi-tenant. El campo `profesional_id` vincula al usuario de rol `Profesional` con su registro en la tabla `profesional` para facilitar la consulta de su agenda propia en `C-05`.

### D4: Inyección y Seams de FastAPI (`dependencias.py`)
- **Decisión**:
  - Crear dependencia `obtener_usuario_actual(request: Request, credenciales: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> ContextoUsuario`.
  - `ContextoUsuario` es un dataclass inmutable: `id: int`, `email: str`, `tenant_id: int`, `rol: str`, `profesional_id: int | None`.
  - Crear fábrica de dependencias `requerir_rol(*roles_permitidos: str)`: verifica `usuario.rol in roles_permitidos`, devolviendo `403 ACCESO_DENEGADO` en caso contrario.
  - Actualizar `contexto_turnos`: ahora depende de `usuario: ContextoUsuario = Depends(obtener_usuario_actual)`. El `tenant_id` se toma indefectiblemente de `usuario.tenant_id`.
- **Racionalidad**: Elimina cualquier posibilidad de que un usuario autenticado envíe un `X-Tenant-ID` y acceda a los turnos de otra clínica.

### D5: UI Mockups
- **Decisión**: `Decision: no (no UI)` — Este change es puramente de backend (autenticación, migraciones SQL, tokens JWT, middleware y dependencias HTTP). No incorpora ni altera componentes de interfaz gráfica.

## 6. Consideraciones de Ingeniería y Trazabilidad (TPI)

- **Model Context Protocol (MCP):** Integrado mediante las herramientas del servidor `engram` (`mem_search`, `mem_context`, `mem_save` , `mem_judge` ) para la persistencia de contexto, recuperación de decisiones históricas y validación cruzada de las reglas de control de acceso (RBAC) y multitenencia (`tenant_id`).
- **Skill Propia:** Uso del framework de desarrollo guiado por especificaciones (Spec-Driven Development) a través de OpenSpec para garantizar la trazabilidad estricta entre contratos y pruebas.

## Risks / Trade-offs

- **[Riesgo] Expiración de tokens y desincronización de sesiones** → *Mitigación*: Tiempo de expiración configurable vía variable de entorno `ACCESS_TOKEN_EXPIRE_MINUTES` (por defecto 60 minutos en dev/test; configurable en `.env` conforme a `D-05`).
- **[Riesgo] Ruptura de tests de integración de API existentes (`test_turnos_api.py`)** → *Mitigación*: La suite existente se actualiza incorporando un helper o fixture `token_recepcionista` generado contra el tenant sembrado en SQLite real, verificando explícitamente tanto el flujo con token válido como los nuevos casos de rechazo sin token (`401`) o con rol incorrecto (`403`).
- **[Riesgo] Credenciales o secretos expuestos en el código fuente** → *Mitigación*: La variable `SECRET_KEY` se gestiona a través de `config.py` y `.env` (`D-05`, regla dura 6). En tests se utiliza una clave sintética fija aislada en memoria.
- **[Riesgo] Desalineación con datos reales** → *Mitigación*: Se utilizan estrictamente usuarios sintéticos en la semilla (`RN-06`): `admin@ejemplo.com`, `recepcion@ejemplo.com`, `dr.ejemplo@ejemplo.com`.

## Migration Plan

1. El módulo `src/infrastructure/database.py` continuará ejecutando secuencialmente todas las migraciones contenidas en `src/infrastructure/migrations/` ordenadas alfabéticamente (`001_init.sql`, `002_auth.sql`).
2. La migración `002_auth.sql` utiliza sentencias idempotentes `CREATE TABLE IF NOT EXISTS` e índices condicionales.
3. La función `sembrar_datos_iniciales` de `src/infrastructure/seed.py` se actualiza para sembrar los usuarios sintéticos por defecto solo si no existen (`INSERT OR IGNORE INTO usuario ...`).

