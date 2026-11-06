# Tasks

## 1. Persistencia y Modelo de Usuarios

- [x] 1.1 Agregar `pyjwt` en `backend/requirements.txt` y verificar que los imports en el entorno sean válidos.
- [x] 1.2 Crear migración `backend/src/infrastructure/migrations/002_auth.sql` con la tabla `usuario` (`tenant_id`, `email`, `password_hash`, `rol`, `profesional_id`, `activo`) e índices, y verificar que `aplicar_migraciones` en `src/infrastructure/database.py` la aplique correctamente en SQLite.
- [x] 1.3 Implementar adaptador `RepositorioUsuariosSqlite` en `backend/src/repositories/usuarios_sqlite.py` con búsqueda por email y tenant, y búsqueda por id, verificando su funcionamiento con tests en `tests/integration/test_usuarios_repositorio.py`.
- [x] 1.4 Actualizar `backend/src/infrastructure/seed.py` para sembrar de forma idempotente usuarios sintéticos de prueba (`admin@ejemplo.com`, `recepcion@ejemplo.com`, `dr.ejemplo@ejemplo.com`) con credenciales conocidas (`RN-06`), verificando su persistencia en la base de datos de prueba.

## 2. Seguridad Criptográfica y Manejo de JWT

- [x] 2.1 Implementar `backend/src/api/seguridad.py` con hashing y verificación de contraseñas mediante `PBKDF2-HMAC-SHA256` y funciones de creación y decodificación de tokens JWT (`HS256`), configurando clave secreta y expiración vía `config.py`.
- [x] 2.2 Crear tests unitarios en `tests/unit/test_seguridad.py` verificando verificación correcta de hash, rechazo de password incorrecta, generación de token con claims (`sub`, `email`, `tenant_id`, `rol`, `profesional_id`), expiración temporal y rechazo de firma inválida.

## 3. Endpoints de Autenticación y Esquemas

- [x] 3.1 Definir esquemas Pydantic v2 en `backend/src/api/esquemas.py` (`LoginSolicitud`, `TokenRespuesta`, `UsuarioPerfilRespuesta`) y excepciones HTTP en `backend/src/api/errores.py` (`CREDENCIALES_INVALIDAS`, `NO_AUTENTICADO`, `TOKEN_EXPIRADO`, `TOKEN_INVALIDO`, `ACCESO_DENEGADO`).
- [x] 3.2 Implementar router de autenticación en `backend/src/api/routers/auth.py` con los endpoints `POST /api/v1/auth/login` y `GET /api/v1/auth/me`, incorporándolo en la factoría de aplicación `app.py`.
- [x] 3.3 Crear tests de integración en `tests/integration/test_auth_api.py` verificando login exitoso (200), login con contraseña errónea (401), login de usuario inexistente (401), login de usuario inactivo (401) y consulta de `/me` autenticada.

## 4. Dependencias FastAPI, RBAC y Resolución de Tenant

- [x] 4.1 Implementar las dependencias `obtener_usuario_actual` y la fábrica de autorización `requerir_rol(*roles)` en `backend/src/api/dependencias.py` extrayendo el Bearer token y mapeando adecuadamente errores 401 y 403.
- [x] 4.2 Reemplazar la resolución provisoria de `_resolver_tenant` y actualizar `contexto_turnos` en `backend/src/api/dependencias.py` para derivar el `tenant_id` directamente del usuario autenticado, impidiendo inyecciones libres de tenant.
- [x] 4.3 Crear tests de integración en `tests/integration/test_rbac_tenancy.py` verificando el acceso para roles habilitados, el rechazo con 403 para roles sin permiso, y el bloqueo estricto de acceso cruzado entre tenants distintos.

## 5. Protección de Turnos y Verificación Integral

- [x] 5.1 Proteger `POST /api/v1/turnos` en `backend/src/api/routers/turnos.py` exigiendo rol `Recepcionista` o `Administrador`, y asegurar `GET /api/v1/turnos` con usuario autenticado.
- [x] 5.2 Actualizar los tests de integración en `tests/integration/test_turnos_api.py` para utilizar fixtures de usuario autenticado con token JWT sobre SQLite real, verificando además el rechazo 401 para peticiones anónimas y 403 para usuarios con rol `Profesional`.
- [x] 5.3 Ejecutar la suite completa de pruebas con `pytest` comprobando que el 100% de los tests pasan sin fallas, con SQLite real y preservando la pureza del dominio (`src/domain/`).

## Workflow follow-up

- Presentar la propuesta y diseño al usuario para aprobación antes de escribir código de implementación (Governance: CRÍTICO).
- Tras aprobación, ejecutar el ciclo de implementación TDD estricto mediante `/openspec-apply c-04-auth-rbac-tenancy`.
- Sincronizar delta specs y archivar mediante `/openspec-archive c-04-auth-rbac-tenancy`.

