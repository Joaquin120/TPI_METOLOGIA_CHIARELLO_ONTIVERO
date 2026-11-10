# Tasks

## 1. Esquema de persistencia y modelos de dominio

- [x] 1.1 Crear migración `backend/src/infrastructure/migrations/005_auditoria.sql` definiendo la tabla `auditoria` con claves foráneas a `tenant(id)` y `usuario(id)`, e índices `idx_auditoria_tenant_fecha` e `idx_auditoria_tenant_entidad`.
- [x] 1.2 Declarar la entidad `RegistroAuditoria` en `backend/src/domain/models.py` como `dataclass(frozen=True)` con campos `(id, tenant_id, usuario_id, accion, entidad, entidad_id, detalle, fecha_hora)`, verificando la pureza con `test_pureza_dominio.py`.
- [x] 1.3 Actualizar `backend/tests/test_persistencia_esquema.py` para incluir `005_auditoria.sql` en la lista esperada de migraciones.

## 2. Repositorio de persistencia en SQLite

- [x] 2.1 Implementar `RepositorioAuditoriaSqlite` en `backend/src/repositories/auditoria_sqlite.py` con métodos `registrar(registro: RegistroAuditoria) -> RegistroAuditoria` y `listar(tenant_id: int, fecha_desde=None, fecha_hasta=None, usuario_id=None, accion=None, entidad=None) -> list[RegistroAuditoria]` acotados incondicionalmente a `tenant_id`.
- [x] 2.2 Verificar mediante pruebas de persistencia en SQLite real el guardado y filtrado de registros sin colisiones inter-tenant.

## 3. Capa API y endpoints REST de auditoría

- [x] 3.1 Definir el esquema Pydantic `RegistroAuditoriaRespuesta` en `backend/src/api/esquemas.py`.
- [x] 3.2 Implementar el router `backend/src/api/routers/auditoria.py` con el endpoint `GET /api/v1/auditoria`, protegido por `ContextoUsuario` exclusivamente para el rol `Administrador`, soportando parámetros de query para filtrado.
- [x] 3.3 Configurar la dependencia `obtener_repositorio_auditoria` en `backend/src/api/dependencias.py` y registrar el router en `create_app()` de `backend/src/api/app.py`.

## 4. Suite de pruebas de integración y verificación

- [x] 4.1 Implementar la suite `backend/tests/test_api_auditoria.py` con fixtures sintéticos (RN-06), cubriendo:
  - Consulta general de auditoría (200).
  - Filtrado por rango de fechas (200) y validación de fechas invertidas (422 `RANGO_FECHAS_INVALIDO`).
  - Filtrado por entidad y acción (200).
  - Aislamiento multi-tenant estricto (Tenant A no puede ver auditoría de Tenant B).
  - Control de acceso RBAC: éxito con `Administrador` (200), denegado con `Recepcionista` y `Profesional` (403 `ACCESO_DENEGADO`), rechazo sin token (401 `NO_AUTENTICADO`).
  - Envelope uniforme de errores en respuestas 401, 403 y 422.
- [x] 4.2 Ejecutar la suite completa con `python3.12 -m pytest backend/tests` y verificar 100% de tests en verde con cobertura >= 97% en los nuevos módulos.
