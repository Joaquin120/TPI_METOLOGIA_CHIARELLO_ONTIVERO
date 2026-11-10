# Design

## Context

El sistema turnos-odontologia cuenta con persistencia relacional en SQLite, autenticación JWT, RBAC, gestión de turnos, recursos clínicos, pacientes y reportes de métricas (C-01 a C-08). Sin embargo, carece de una bitácora centralizada e inmutable de eventos que permita a la dirección y administración auditar quién realizó cada acción en el sistema (trazabilidad y no repudio).

Consultar `proposal.md` para la motivación general y `specs/auditoria-trazabilidad/spec.md` para los requisitos normativos y escenarios Given/When/Then.

## Goals / Non-Goals

**Goals:**
- Exponer el endpoint REST `GET /api/v1/auditoria` protegido por Bearer JWT y control de acceso exclusivo para el rol `Administrador`.
- Definir la migración relacional `005_auditoria.sql` creando la tabla `auditoria` con claves foráneas a `tenant(id)` y `usuario(id)`, y sus índices correspondientes.
- Modelar la entidad `RegistroAuditoria` en `backend/src/domain/models.py` como `dataclass(frozen=True)` preservando 0 dependencias externas.
- Implementar el adaptador `RepositorioAuditoriaSqlite` en `backend/src/repositories/auditoria_sqlite.py` con métodos `registrar` y `listar` acotados incondicionalmente al `tenant_id`.
- Soportar filtrado por rango de fechas (`fecha_desde`, `fecha_hasta`), usuario (`usuario_id`), acción (`accion`) y entidad (`entidad`).
- Preservar el envelope uniforme de errores `{"error": {"code": "...", "message": "..."}}`.
- Proveer suite de pruebas `backend/tests/test_api_auditoria.py` con cobertura >= 97% y datos puramente sintéticos (RN-06).

**Non-Goals:**
- Modificación o borrado de eventos de auditoría (la bitácora es estrictamente append-only e inmutable).
- Exportación asíncrona de reportes a PDF o formatos externos (fuera de alcance del MVP).
- Middleware de intercepción automática de todas las rutas HTTP (en el MVP los eventos se registran explícitamente vía repositorio o servicios).

## Decisions

### D1: Migración `005_auditoria.sql` y esquema append-only
- **Decisión**: Crear `backend/src/infrastructure/migrations/005_auditoria.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS auditoria (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tenant_id INTEGER NOT NULL REFERENCES tenant(id),
      usuario_id INTEGER NOT NULL REFERENCES usuario(id),
      accion TEXT NOT NULL,
      entidad TEXT NOT NULL,
      entidad_id INTEGER,
      detalle TEXT,
      fecha_hora TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_auditoria_tenant_fecha ON auditoria (tenant_id, fecha_hora);
  CREATE INDEX IF NOT EXISTS idx_auditoria_tenant_entidad ON auditoria (tenant_id, entidad, entidad_id);
  ```
- **Razón**: Permite consultas cronológicas y por entidad de alta performance, asegurando integridad referencial con las tablas de usuarios y tenants.

### D2: Pureza del modelo de dominio `RegistroAuditoria`
- **Decisión**: Declarar `RegistroAuditoria` en `backend/src/domain/models.py` como `dataclass(frozen=True)` con campos `id: int | None`, `tenant_id: int`, `usuario_id: int`, `accion: str`, `entidad: str`, `entidad_id: int | None`, `detalle: str | None`, `fecha_hora: str`.
- **Razón**: El dominio no debe depender de librerías web ni drivers de bases de datos, garantizando cumplimiento con `test_pureza_dominio.py`.

### D3: Repositorio analítico y de registro `RepositorioAuditoriaSqlite`
- **Decisión**: Implementar `backend/src/repositories/auditoria_sqlite.py` recibiendo `sqlite3.Connection`, filtrando siempre `WHERE tenant_id = ?` y ordenando `ORDER BY id DESC`.
- **Razón**: Garantiza que un tenant jamás pueda acceder a las pistas de auditoría de otra clínica (Regla Dura 8).

### D4: Control de acceso RBAC estricto
- **Decisión**: El endpoint `GET /api/v1/auditoria` requiere rol `Administrador`.
  - Roles `Recepcionista` y `Profesional` reciben HTTP 403 `{"error": {"code": "ACCESO_DENEGADO", "message": "..."}}`.
  - Peticiones sin token reciben HTTP 401 `{"error": {"code": "NO_AUTENTICADO", "message": "..."}}`.
- **Razón**: Las pistas de auditoría contienen información sensible de supervisión operativa y seguridad que solo compete al perfil administrador de la clínica.

### D5: Validación de fechas y envelope unificado
- **Decisión**: Validación de formato `YYYY-MM-DD` mediante `PATRON_FECHA` y chequeo de que `fecha_desde <= fecha_hasta`. Si se invierte el orden, se lanza `ErrorRangoFechasInvalido` (HTTP 422).
- **Razón**: Mantiene coherencia con el estándar establecido en C-08.

## Risks / Trade-offs

- **[Riesgo: Volumen creciente de registros de auditoría]** → *Mitigación:* Se añaden índices compuestos `idx_auditoria_tenant_fecha` e `idx_auditoria_tenant_entidad` para mantener tiempos de respuesta constantes.
- **[Riesgo: Fuga de registros entre clínicas]** → *Mitigación:* Cláusula `WHERE tenant_id = ?` forzada e inmutable en todas las consultas del repositorio.

## Migration Plan

1. Se incorpora `005_auditoria.sql` que se ejecuta de forma automática e idempotente vía `migrar(conexion)`.
2. Se actualiza `backend/tests/test_persistencia_esquema.py` para incluir `005_auditoria.sql` en la lista de migraciones registradas.
