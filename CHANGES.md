# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Turnos Odontológicos (SaaS)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 cancelacion-y-estados-turno
  └── C-02 persistencia-sqlite
        └── C-03 capa-api-desacoplada
              └── C-04 auth-rbac-tenancy              ← cierra el MVP base
                    ├── C-05 endpoints-turnos
                    │     └── C-08 reprogramacion-turno
                    ├── C-06 endpoints-recursos
                    │     └── C-09 admin-recursos-crud
                    │           └── C-10 bloqueo-sillon
                    ├── C-07 gestion-pacientes
                    │
                    └── C-11 frontend-shell           (C-05 + C-06 + C-07)
                          └── C-12 agenda-turnos-ui   (C-08 + C-10)
                                ├── C-13 agenda-matricial          [segunda etapa]
                                ├── C-14 notificaciones-whatsapp   [segunda etapa, + C-05]
                                └── C-15 lista-espera              [segunda etapa, + C-14]
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 cancelacion-y-estados-turno        [Agente A]

GATE 1: C-01 ✓
  → C-02 persistencia-sqlite                [Agente A]

GATE 2: C-02 ✓
  → C-03 capa-api-desacoplada               [Agente A]

GATE 3: C-03 ✓
  → C-04 auth-rbac-tenancy                  [Agente A]   ← FIN DEL CAMINO CRÍTICO MVP BASE

GATE 4: C-04 ✓                             ← PRIMER FORK (3 paralelos)
  → C-05 endpoints-turnos                   [Agente A]
  → C-06 endpoints-recursos                 [Agente B]
  → C-07 gestion-pacientes                  [Agente C]

GATE 5: C-05 ✓
  → C-08 reprogramacion-turno               [Agente B]
  → C-09 admin-recursos-crud                [Agente A — si C-06 ✓]
  → C-11 frontend-shell                     [Agente C — si C-06 y C-07 ✓]

GATE 6: C-08 + C-09 ✓
  → C-10 bloqueo-sillon                     [Agente B — si C-09 ✓]
  → C-12 agenda-turnos-ui                   [Agente C — si C-11 ✓]

GATE 7: C-10 + C-12 ✓                      ← SEGUNDA ETAPA (3 paralelos)
  → C-13 agenda-matricial                   [Agente C — si C-12 ✓]
  → C-14 notificaciones-whatsapp            [Agente A — si C-05 ✓]
  → C-15 lista-espera                       [Agente B — si C-14 ✓]
```

### Camino crítico MVP (7 changes — mínimo irreducible)

> Cadena prioritaria definida para el MVP: **cancelación y estados de turnos → persistencia en BD → desacople de backend** (`C-01 → C-02 → C-03`), seguida del acceso y la UI mínima hasta poder operar la agenda.

```
C-01 → C-02 → C-03 → C-04 → C-05* → C-11 → C-12
```

\* `C-06` y `C-07` corren en paralelo con `C-05` y también alimentan `C-11`; cualquiera de los tres es válidos en la cadena.

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core)        │ Agente B (Backend Aux)      │ Agente C (Frontend/API)
─────┼────────────────────────────────┼─────────────────────────────┼──────────────────────────
  1  │ C-01 cancelacion-y-estados     │            —                │            —
  2  │ C-02 persistencia-sqlite       │            —                │            —
  3  │ C-03 capa-api-desacoplada      │            —                │            —
  4  │ C-04 auth-rbac-tenancy         │            —                │            —
  5  │ C-05 endpoints-turnos          │ C-06 endpoints-recursos     │ C-07 gestion-pacientes
  6  │ C-09 admin-recursos-crud       │ C-08 reprogramacion-turno   │ C-11 frontend-shell
  7  │ C-14 notificaciones-whatsapp   │ C-10 bloqueo-sillon         │ C-12 agenda-turnos-ui
  8  │            —                   │ C-15 lista-espera           │ C-13 agenda-matricial
```

---

## FASE 0 — Núcleo del dominio (MVP · camino crítico)

> Secuencia lineal estricta: `C-01 → C-02 → C-03`. No hay paralelismo en esta fase.

### [C-01] `cancelacion-y-estados-turno`
- **Estado**: `[x]` completado — archivado 2026-11-03 en `openspec/changes/archive/2026-11-03-c-01-cancelacion-y-estados-turno/`
- **Scope**: Ciclo de vida completo del turno (`RN-03`, `RN-04`) sobre el servicio de dominio existente
  - Máquina de estados: constantes `PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO` + matriz de transiciones válidas (Confirmar, Cancelar, Completar)
  - `ServicioTurnos`: nuevos métodos `confirmar()`, `cancelar()`, `completar()` que rechazan transiciones inválidas con la nueva excepción de dominio `TransicionInvalidaError`
  - Liberación por cancelación: el filtro de solapamiento solo considera turnos **activos** (`PENDIENTE`/`CONFIRMADO`); un turno `CANCELADO` o `COMPLETADO` no bloquea profesional ni sillón (`RN-04`)
  - Se conserva el estado inicial `CONFIRMADO` del alta (spec vigente, `PA-13` sigue abierta — no resolver en este change)
  - Tests: transiciones válidas e inválidas, cancelación libera ambos recursos (re-agendar en el mismo intervalo), estados finales no admiten transiciones, suite actual sigue verde (8 tests)
- **Dependencias**: ninguna (continúa el change archivado `2026-10-15-crear-turno-sin-solapamientos`)
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/business-rules.md` §RN-03, §RN-04
  - `knowledge-base/flows.md` §3 Flujo de cambio de estado, §4 Flujo de cancelación
  - `knowledge-base/features.md` §F-03
  - `knowledge-base/data-models.md` §4.1 Estado del turno

---

### [C-02] `persistencia-sqlite`
- **Estado**: `[x]` completado — archivado 2026-11-03 en `openspec/changes/archive/2026-11-03-c-02-persistencia-sqlite/`
- **Scope**: Salida de la lista en memoria (`ServicioTurnos._turnos`) y persistencia real con repositorios
  - Migración 001 (SQLite, `D-04`): tablas `tenant`, `profesional`, `sillon`, `paciente`, `turno` con `tenant_id`, FKs, `estado` como enum y campos `fecha_hora_inicio` / `fecha_hora_fin`
  - Repositorios: `RepositorioTurnos`, `RepositorioProfesionales`, `RepositorioSillones`, `RepositorioPacientes` — todos filtran por `tenant_id` (`RN-05`)
  - `ServicioTurnos` deja de guardar en `self._turnos`; recibe el repositorio por inyección (sin cambio de comportamiento del dominio)
  - Configuración de la ruta de la base por variables de entorno (`.env`, `D-05`); seed sintético: 1 tenant, 2 profesionales, 2 sillones (`RN-06`)
  - Tests de integración: alta → consulta persistida, aislamiento por tenant, turnos cancelados no bloquean vía BD; unitarias existentes sin cambios
- **Dependencias**: `C-01`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/data-models.md` §2 Entidades, §5 Invariantes
  - `knowledge-base/architecture.md` §7 Persistencia, §9 Estructura de directorios
  - `knowledge-base/decisions.md` §2 D-04, D-05, §3 DP-02, DP-06
  - `knowledge-base/business-rules.md` §RN-05, §RN-06

---

### [C-03] `capa-api-desacoplada`
- **Estado**: `[x]` completado — archivado 2026-11-04 en `openspec/changes/archive/2026-11-04-c-03-api-fastapi/`
- **Scope**: Capa de presentación desacoplada del dominio (puertos y adaptadores) — fin del "desacople de backend"
  - Estructura: `src/api/` (controladores + esquemas), `src/repositories/` (adaptadores), `src/infrastructure/` (config, DB), `src/domain/` intacto (`architecture.md` §9)
  - App FastAPI mínima (o framework según resolución de `DP-01`): factoría que ensambla controlador → servicio de dominio → repositorio
  - `GET /api/health` — health check
  - Mapeo de excepciones de dominio a HTTP: `SolapamientoProfesionalError` / `SolapamientoSillonError` → `409`, `TransicionInvalidaError` → `409`, validación de entrada → `422` (contrato de errores `features.md` §5.2)
  - Esquemas Pydantic de entrada/salida para turno (ejemplo de `features.md` §5.1); el dominio no importa HTTP ni SQLAlchemy
  - Tests de integración: cliente HTTP contra el servicio con SQLite en memoria; ninguna regla de solapamiento vive en la capa API
- **Dependencias**: `C-02`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/architecture.md` §2 Vista de capas, §3 Responsabilidades, §6 Flujo de una operación
  - `knowledge-base/decisions.md` §2 D-02, D-06, D-10, §3 DP-01
  - `knowledge-base/features.md` §5 Endpoints, §5.2 Errores de dominio
  - `AGENTS.md` (reglas duras: doble validación, privacidad, criterio verde)

---

## FASE 1 — Acceso y tenancy

### [C-04] `auth-rbac-tenancy`
- **Estado**: `[x]` completado — archivado 2026-11-05 en `openspec/changes/archive/2026-11-05-c-04-auth-rbac-tenancy/`
- **Scope completado**: Autenticación, control de acceso basado en roles (RBAC) y resolución determinista de tenant desde la sesión
  - Resoluciones arquitectónicas: `DP-03` resuelta confirmando el modelo de base compartida SQLite con discriminador `tenant_id` en todas las tablas y consultas; `DP-04` resuelta mediante autenticación stateless con JWT (HS256) y almacenamiento de contraseñas con PBKDF2-HMAC-SHA256 con salt aleatorio.
  - Migración 002: script `backend/src/infrastructure/migrations/002_auth.sql` con tabla `usuario` (`tenant_id`, `email`, `password_hash`, `rol`, `profesional_id`, `activo`) e índice único `(tenant_id, email)`.
  - Adaptador de persistencia: `RepositorioUsuariosSqlite` en `backend/src/repositories/usuarios_sqlite.py` con búsqueda por email/tenant y por identificador.
  - Semilla sintética actualizada: `backend/src/infrastructure/seed.py` siembra usuarios sintéticos para los 3 roles (`admin@ejemplo.com`, `recepcion@ejemplo.com`, `dr.ejemplo@ejemplo.com`) con credenciales conocidas (`RN-06`).
  - Endpoints de autenticación: `POST /api/v1/auth/login` (autentica credenciales y emite JWT con claims `sub`, `email`, `tenant_id`, `rol`, `profesional_id`) y `GET /api/v1/auth/me` (perfil del usuario autenticado).
  - Infraestructura de seguridad y dependencias FastAPI: `backend/src/api/seguridad.py` (hashing y JWT) y `backend/src/api/dependencias.py` con `obtener_usuario_actual` (Bearer token) y `requerir_rol(*roles)` (RBAC).
  - Resolución no falsificable de tenant: el seam provisorio de `contexto_turnos` fue reemplazado para derivar el `tenant_id` estrictamente del token verificado del usuario autenticado, anulando la manipulación de cabeceras arbitrarias.
  - Protección de endpoints de turnos: `POST /api/v1/turnos` restringido a roles `Recepcionista` y `Administrador`; `GET /api/v1/turnos` acotado al tenant del usuario; usuarios con rol `Profesional` reciben `403 ACCESO_DENEGADO` al intentar agendar.
  - Suite de pruebas y cobertura: 130 tests automatizados pasando al 100% en SQLite real con 97% de cobertura general y 100% en `src/domain/`.
- **Skill propia integrada**: `.atl/skills/validador-trazabilidad-openspec.md`
  - *Propósito*: Puerta de calidad y auditoría técnica Spec-Driven Development (SDD) para cambios en OpenSpec.
  - *Validaciones ejecutadas*:
    1. *Fidelidad normativa*: 14 escenarios de spec probados con pytest con cobertura exhaustiva de códigos HTTP (200, 201, 401, 403, 409, 422) y envelope estable `{"error": {"code": "...", "message": "..."}}`.
    2. *Pureza de dominio*: 0 dependencias de frameworks o infraestructura en `src/domain/` comprobadas mediante guard tests automatizados (`test_pureza_dominio.py` 5/5).
    3. *Seguridad y aislamiento*: `tenant_id` derivado obligatoriamente de `ContextoUsuario` y aislamiento inter-tenant demostrado en `test_rbac_tenancy.py`.
    4. *Sincronización de artefactos*: `tasks.md` (15/15 all_done), roadmap `CHANGES.md` y `.active-orchestrator-state.json`.
  - *Dictamen*: **APROBADO**.
- **Herramientas MCP utilizadas en este change**:
  - Servidor **`engram`**:
    - `mem_context`: Recuperación del contexto de sesiones previas y estado base del proyecto al iniciar la fase `propose`.
    - `mem_search`: Búsqueda de precedentes y decisiones en el proyecto (`tpi_metologia_chiarello_ontivero`).
    - `mem_save`: Persistencia proactiva de observaciones de arquitectura al finalizar `propose` (decisiones `DP-03`/`DP-04`, contratos de spec) y `apply` (evidencia de TDD, 15 tareas completadas, métricas de suite y cobertura).
    - `mem_judge`: Arbitraje y conciliación de relaciones (`compatible`) entre las observaciones de memoria históricas de C-03 y las nuevas observaciones de C-04.
- **Dependencias**: `C-03`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/actors.md` §2 Responsabilidades, §3 Matriz de permisos, §5 Restricciones
  - `knowledge-base/decisions.md` §3 DP-03, DP-04
  - `knowledge-base/architecture.md` §5 Modelo multi-tenant, §11 Seguridad
  - `knowledge-base/business-rules.md` §RN-05, §RN-06

---

## FASE 2 — Endpoints de agenda (PRIMER FORK)

> `C-05`, `C-06` y `C-07` pueden proponerse y ejecutarse en paralelo tras `C-04`.

### [C-05] `endpoints-turnos`
- **Estado**: `[x]` completado y archivado (`openspec/changes/archive/2026-11-08-c-05-endpoints-turnos/`)
- **Scope**: API REST completa del módulo Agenda (`F-01`, `F-02`, `F-03`)
  - `POST /api/v1/turnos` — alta con doble validación delegada al dominio (`RN-01`, `RN-09`), estado inicial `CONFIRMADO`
  - `GET /api/v1/turnos` — filtros opcionales combinables `fecha`, `profesional_id`, `sillon_id`; solo turnos del tenant (`RN-05`); el rol `Profesional` restringido a su propia agenda
  - `PATCH /api/v1/turnos/{id}/estado` — confirmar / cancelar / completar según `RN-03`; cancelación libera recursos (`RN-04`)
  - Tests: suite de 155 tests passing en SQLite real con 97% de cobertura global y 100% en dominio y persistencia
- **Auditoría de Trazabilidad OpenSpec (SDD)**:
  - Validado formalmente con la skill `.atl/skills/validador-trazabilidad-openspec.md`:
    1. *Fidelidad normativa*: 15 escenarios de spec verificados con pytest (200, 201, 401, 403, 404, 409, 422) con envelope estándar.
    2. *Pureza de dominio*: 0 dependencias externas en `src/domain/` (guard tests 5/5 passing).
    3. *Seguridad y aislamiento*: `tenant_id` derivado forzosamente desde JWT (`ContextoUsuario`), aislamiento inter-tenant demostrado en SQLite real.
    4. *Sincronización de artefactos*: `tasks.md` (9/9 all_done), roadmap `CHANGES.md` y `.active-orchestrator-state.json`.
  - *Dictamen*: **APROBADO**.
- **Herramientas MCP utilizadas en este change**:
  - Servidor **`engram`**:
    - `mem_context`: Recuperación del contexto de sesiones previas al iniciar propose y apply.
    - `mem_save`: Persistencia proactiva de arquitectura al completar propose, apply y archive.
    - `mem_judge`: Arbitraje de relaciones y precedencia de observaciones de arquitectura de C-05.
- **Dependencias**: `C-04`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/features.md` §F-01, §F-02, §F-03, §5 Endpoints
  - `knowledge-base/flows.md` §2 Flujo de creación, §3 Flujo de cambio de estado
  - `knowledge-base/business-rules.md` §RN-01, §RN-03, §RN-09
  - `knowledge-base/actors.md` §3 Matriz de permisos

---

### [C-06] `endpoints-recursos`
- **Estado**: `[x]` completado y archivado (`openspec/changes/archive/2026-11-09-c-06-endpoints-recursos/`)
- **Scope**: Consulta de recursos para asignar turnos (`F-04`, `F-05`)
  - `GET /api/v1/profesionales` — lista del tenant, con `matricula`, `especialidad`, `activo`
  - `GET /api/v1/sillones` — lista del tenant, con `equipamiento` y `activo`
  - Seed sintético ampliado (datos ficticios: `Dr. Ejemplo`, `Sillón 1`, `Dr. Inactivo`, `Sillón 3`)
  - Tests: listados acotados al tenant, inclusión/exclusión de recursos inactivos según decisión de `PA-01` (`solo_activos: bool = True`)
  - Tests: suite de 170 tests passing en SQLite real con 97% de cobertura global y 100% en dominio, repositorios y router de recursos
- **Auditoría de Trazabilidad OpenSpec (SDD)**:
  - Validado formalmente con la skill `.atl/skills/validador-trazabilidad-openspec.md`:
    1. *Fidelidad normativa*: 9 escenarios de spec verificados con pytest (200, 401) con envelope estándar y filtrado `solo_activos`.
    2. *Pureza de dominio*: 0 dependencias externas en `src/domain/` (guard tests 5/5 passing).
    3. *Seguridad y aislamiento*: `tenant_id` derivado forzosamente desde JWT (`ContextoUsuario`), aislamiento inter-tenant demostrado en SQLite real.
    4. *Sincronización de artefactos*: `tasks.md` (8/8 all_done), roadmap `CHANGES.md` y `.active-orchestrator-state.json`.
  - *Dictamen*: **APROBADO**.
- **Herramientas MCP utilizadas en este change**:
  - Servidor **`engram`**:
    - `mem_context`: Recuperación del contexto de sesiones previas al iniciar propose y apply.
    - `mem_save`: Persistencia proactiva de arquitectura al completar propose, apply y archive.
    - `mem_judge`: Arbitraje de relaciones y conciliación de observaciones de memoria de C-06.
- **Dependencias**: `C-04`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/features.md` §F-04, §F-05, §5 Endpoints
  - `knowledge-base/data-models.md` §2.2 Profesional, §2.3 Sillón
  - `knowledge-base/business-rules.md` §RN-05

---

### [C-07] `gestion-pacientes`
- **Estado**: `[x]` completado — archivado en `openspec/changes/archive/2026-11-09-c-07-gestion-pacientes/` (specs en `openspec/specs/gestionar-pacientes/spec.md`)
- **Scope**: Alta y consulta de pacientes (`F-11`)
  - Definir contrato (figura como "pendiente de definición" en `features.md` §5): `POST /api/v1/pacientes`, `GET /api/v1/pacientes` con filtro `dni` o `nombre`
  - Campos: `dni`, `nombre`, `telefono`, `tenant_id` (`data-models.md` §2.4); validación de datos mínimos
  - Alta de paciente habilitada solo para roles autorizados según `actors.md` §7 (resolver en el proposal quién gestiona pacientes)
  - Tests: alta → asociación a un turno del mismo tenant, listado filtrado, aislamiento por tenant, solo datos sintéticos (`RN-06`)
- **Dependencias**: `C-04`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/features.md` §F-11, §5 Endpoints
  - `knowledge-base/data-models.md` §2.4 Paciente
  - `knowledge-base/actors.md` §3 Matriz de permisos, §7 Permisos pendientes
  - `knowledge-base/open-questions.md` PA-05

---

## FASE 3 — Operación y Analítica de la Agenda

### [C-08] `reportes-metricas`
- **Estado**: `[x]` completado — archivado 2026-11-09 en `openspec/changes/archive/2026-11-09-c-08-reportes-metricas/` (specs en `openspec/specs/reportes-metricas/spec.md`)
- **Scope**: Consulta analítica de indicadores operativos y métricas de turnos y recursos clínicos (ocupación, estados y tasas de cancelación) acotada al tenant autenticado, con RBAC y envelope uniforme.
  - Endpoints: `GET /api/v1/metricas/turnos` y `GET /api/v1/metricas/recursos`
  - Métricas: total de turnos, conteo por estado, cálculo seguro de tasa de cancelación (0.0% cuando total=0)
  - Desglose por recurso (profesionales y sillones) mediante LEFT JOIN preservando recursos sin asignaciones
  - Filtrado opcional por rango de fechas (`fecha_desde`, `fecha_hasta`) y validación de rango (422 `RANGO_FECHAS_INVALIDO`)
  - RBAC: permitido para `Administrador` y `Recepcionista`; denegado para `Profesional` (403 `ACCESO_DENEGADO`); sin token (401 `NO_AUTENTICADO`)
  - Tests: suite de 201 tests passing con 98% de cobertura general y 100% en routers y repositorios de métricas
- **Auditoría de Trazabilidad OpenSpec (SDD)**:
  - Validado formalmente con la skill `.atl/skills/validador-trazabilidad-openspec.md`:
    1. *Fidelidad normativa*: 10 escenarios de spec verificados con pytest (200, 401, 403, 422) con envelope estándar.
    2. *Pureza de dominio*: 0 dependencias externas en `src/domain/` (guard tests 5/5 passing).
    3. *Seguridad y aislamiento*: `tenant_id` derivado forzosamente desde JWT (`ContextoUsuario`), aislamiento inter-tenant demostrado en SQLite real.
    4. *Sincronización de artefactos*: `tasks.md` (9/9 all_done), roadmap `CHANGES.md` y `.active-orchestrator-state.json`.
  - *Dictamen*: **APROBADO**.
- **Herramientas MCP utilizadas en este change**:
  - Servidor **`engram`**:
    - `mem_save`: Registro del hito de implementación técnica (`opsx/c-08-reportes-metricas/apply`).
    - `mem_search`: Verificación de la persistencia de la observación en memoria semántica.
- **Dependencias**: `C-04`, `C-05`, `C-06`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/features.md`
  - `knowledge-base/data-models.md`
  - `knowledge-base/business-rules.md` §RN-05, §RN-06

---

### [C-08b] `reprogramacion-turno`
- **Estado**: `[x]` completado — archivado 2026-11-09 en `openspec/changes/archive/2026-11-09-c-08b-reprogramacion-turno/` (specs en `openspec/specs/reprogramar-turno/spec.md`)
- **Scope completado**: Reprogramación in-place de turnos existentes preservando su identificador, paciente y estado activo (`F-09`, resolución de `RP-03`).
  - Dominio: método `reprogramar` en `ServicioTurnos` con validación de estados terminales (`TransicionInvalidaError` ante `CANCELADO`/`COMPLETADO`), doble validación simultánea e independiente con precedencia `RN-09` (`SolapamientoProfesionalError` prioritario), y soporte para desplazamientos parciales en la misma franja sin auto-solapamiento (`excluir_turno_id`).
  - Persistencia: `PuertoTurnos` y `RepositorioTurnosSqlite` con soporte para `excluir_turno_id` en `buscar_activos_solapables` y método `actualizar_reprogramacion` atómico en SQLite.
  - API REST: endpoint `PATCH /api/v1/turnos/{id}/reprogramar` con esquema Pydantic `ReprogramarTurnoPeticion` y validación cronológica (`hora_inicio < hora_fin`).
  - RBAC: restringido a `Recepcionista` y `Administrador`; `Profesional` recibe 403 `ACCESO_DENEGADO`. Aislamiento multi-tenant con 404 ante turnos de otro tenant.
  - Auditoría: registro inmutable del evento `REPROGRAMAR_TURNO` en la bitácora de auditoría (C-09) con detalle de estado previo y nuevo intervalo asignado.
  - Tests: suite de 243 tests pasando al 100% con 98% de cobertura general y 100% en el paquete de dominio (`src/domain/`).
- **Dependencias**: `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/features.md` §F-09
  - `knowledge-base/flows.md` §5 Flujo de reprogramación
  - `knowledge-base/business-rules.md` §RP-03, §RN-01
  - `knowledge-base/open-questions.md` PA-06

---

### [C-09] `auditoria-trazabilidad`
- **Estado**: `[x]` completado — archivado 2026-11-09 en `openspec/changes/archive/2026-11-09-c-09-auditoria-trazabilidad/` (specs en `openspec/specs/auditoria-trazabilidad/spec.md`)
- **Scope**: Bitácora inmutable de eventos clínicos y administrativos (acciones sobre turnos, pacientes, recursos y accesos) acotada por tenant y restringida a administradores.
  - Migración 005: tabla `auditoria` con FKs a `tenant` y `usuario`, índices `idx_auditoria_tenant_fecha` e `idx_auditoria_tenant_entidad`
  - Modelo de dominio puro: `RegistroAuditoria` en `src/domain/models.py` (0 dependencias externas)
  - Persistencia: `RepositorioAuditoriaSqlite` con métodos `registrar` y `listar` acotados incondicionalmente a `tenant_id`
  - Endpoint: `GET /api/v1/auditoria` con filtrado por `fecha_desde`, `fecha_hasta`, `usuario_id`, `accion` y `entidad`
  - RBAC: exclusivo para `Administrador` (403 `ACCESO_DENEGADO`); sin token (401 `NO_AUTENTICADO`)
  - Tests: suite de 211 tests passing en SQLite real con 98% de cobertura general y 100% en routers y repositorios de auditoría
- **Dependencias**: `C-04`, `C-05`, `C-07`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/architecture.md`
  - `knowledge-base/actors.md`
  - `knowledge-base/business-rules.md` §RN-05, §RN-06

---

### [C-09b] `admin-recursos-crud`
- **Estado**: `[x]` completado — archivado 2026-11-10 en `openspec/changes/archive/2026-11-10-c-09b-admin-recursos-crud/` (specs en `openspec/specs/administrar-recursos/spec.md`)
- **Scope completado**: Administración de recursos por el Administrador (`F-10`).
  - Dominio: excepción `RecursoDuplicadoError` en `src/domain/exceptions.py`.
  - Persistencia: métodos `crear` y `actualizar` en `RepositorioProfesionales` y `RepositorioSillones` con validación de unicidad por tenant y aislamiento multi-tenant.
  - API REST: endpoints `POST /api/v1/profesionales`, `PUT /api/v1/profesionales/{id}`, `POST /api/v1/sillones` y `PUT /api/v1/sillones/{id}` con esquemas Pydantic `ProfesionalCrear`, `ProfesionalActualizar`, `SillonCrear` y `SillonActualizar`.
  - RBAC: exclusivo para el rol `Administrador` (`403 ACCESO_DENEGADO` para otros roles; `401 NO_AUTENTICADO` sin credenciales; `404` ante recursos inexistentes o ajenos al tenant).
  - Auditoría: registro inmutable de eventos (`CREAR_PROFESIONAL`, `MODIFICAR_PROFESIONAL`, `CREAR_SILLON`, `MODIFICAR_SILLON`) en `auditoria` (C-09).
  - Tests: suite de 273 tests pasando al 100% con 98% de cobertura general y 100% en el paquete de dominio (`src/domain/`).
- **Dependencias**: `C-06`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/features.md` §F-10, §5 Endpoints
  - `knowledge-base/actors.md` §2.1 Administrador, §3 Matriz de permisos
  - `knowledge-base/data-models.md` §2.2, §2.3
  - `knowledge-base/open-questions.md` PA-16

---

### [C-10] `bloqueo-sillon`
- **Estado**: `[x]` completado — archivado 2026-11-10 en `openspec/changes/archive/2026-11-10-c-10-bloqueo-sillon/` (specs en `openspec/specs/bloquear-sillon/spec.md`)
- **Scope completado**: Bloqueo de sillón por mantenimiento (`F-12`, `RN-07`, `RP-07`, `PA-15`).
  - Resoluciones normativas: `PA-15` resuelta modelando `BloqueoSillon` como entidad independiente desacoplada de `Turno` para no viciar la semántica médica de pacientes ni métricas de atención asistencial; `RP-07` resuelta impidiendo el registro de bloqueos si existen turnos activos (`PENDIENTE`/`CONFIRMADO`) en el intervalo semiabierto solapado (`ConflictoTurnosExistentesError` / HTTP 409 `CONFLICTO_TURNOS_EXISTENTES`).
  - Dominio puro: modelo `BloqueoSillon`, excepciones `SillonBloqueadoError`, `ConflictoTurnosExistentesError`, `BloqueoSolapadoError`, `BloqueoNoEncontradoError`, puerto `PuertoBloqueos` y métodos en `ServicioTurnos` (`agendar_turno`, `reprogramar`, `crear_bloqueo`, `listar_bloqueos`, `eliminar_bloqueo`).
  - Persistencia: migración `006_bloqueos.sql` con tabla `bloqueo_sillon` e índices por tenant e intervalo; repositorio `RepositorioBloqueosSqlite` con soporte de intervalos semiabiertos `[inicio, fin)` y aislamiento multi-tenant.
  - API REST: router `backend/src/api/routers/bloqueos.py` con endpoints `POST /api/v1/bloqueos` (Admin), `GET /api/v1/bloqueos` (Admin/Recep) y `DELETE /api/v1/bloqueos/{id}` (Admin).
  - Auditoría inmutable: eventos `CREAR_BLOQUEO_SILLON` y `ELIMINAR_BLOQUEO_SILLON` registrados en la bitácora inmutable (C-09).
  - Tests: suite completa de 303 tests pasando al 100% con 97% de cobertura general y 100% en el paquete de dominio (`src/domain/`).
- **Dependencias**: `C-09`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/features.md` §F-12
  - `knowledge-base/flows.md` §8 Flujo de bloqueo de sillón
  - `knowledge-base/business-rules.md` §RN-07, §RP-07
  - `knowledge-base/open-questions.md` PA-01, PA-15, PA-16

---

## FASE 4 — Frontend web (MVP)

### [C-11] `frontend-shell`
- **Estado**: `[x]` completado — archivado 2026-11-10 en `openspec/changes/archive/2026-11-10-c-11-frontend-shell/` (specs en `openspec/specs/cliente-web-shell/spec.md`)
- **Scope**: Scaffolding del cliente web (producto web-first, `actors.md` §4)
  - Elegir stack frontend en el proposal (`DP-01`): SPA + cliente HTTP tipado contra `src/api`
  - Login + rutas protegidas por rol (consume `C-04`)
  - Layout con navegación: Agenda, Pacientes, Recursos, Configuración
  - `.env.example` del cliente, proxy/CORS hacia la API
  - Tests: smoke de rutas, redirect a login sin sesión
- **Dependencias**: `C-05, C-06, C-07`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/architecture.md` §1 Principios (web-first), §9 Estructura de directorios
  - `knowledge-base/actors.md` §4 Superficies de acceso
  - `knowledge-base/decisions.md` §3 DP-01, DP-10

---

### [C-12] `agenda-turnos-ui`
- **Estado**: `[x]` completado — archivado 2026-11-10 en `openspec/changes/archive/2026-11-10-c-12-agenda-turnos-ui/` (specs en `openspec/specs/cliente-agenda-turnos/spec.md`)
- **Scope**: UI operativa de la agenda sobre la API existente
  - Lista de turnos con filtros por fecha, profesional y sillón (F-02)
  - Formulario de alta de turno: selección de paciente, profesional, sillón, fecha y horario; muestra `SolapamientoProfesionalError` / `SolapamientoSillonError` como mensajes de negocio (F-01)
  - Acciones sobre un turno: confirmar, cancelar, completar (F-03) + reprogramar (F-08/C-08)
  - Estados diferenciados por color según `data-models.md` §4.1
  - Tests E2E mínimos: alta con conflicto visible, cancelación libera el horario en la grilla
- **Dependencias**: `C-11` (usa `C-08` y `C-10` si ya están archivados)
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/flows.md` §2, §3, §4, §7
  - `knowledge-base/features.md` §F-01, §F-02, §F-03, §F-09
  - `knowledge-base/actors.md` §2.2 Recepcionista
  - `knowledge-base/architecture.md` §6 Flujo de una operación

---

## FASE 5 — Segunda etapa (post-MVP)

### [C-13] `agenda-matricial`
- **Estado**: `[ ]` pendiente
- **Scope**: Vista matricial profesionales × sillones por franja horaria (`F-06`)
  - Grilla con estados por color e indicación explícita de intentos de solapamiento
  - Filtros por fecha y recurso; resolución de granularidad de la grilla (abierta en `flows.md` §7.2)
  - Tests: render por profesional/sillón, turnos contiguos visibles, permisos del profesional (agenda propia)
- **Dependencias**: `C-12`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/flows.md` §7 Flujo de agenda y visualización
  - `knowledge-base/features.md` §F-06
  - `knowledge-base/actors.md` §2.3 Profesional

---

### [C-14] `notificaciones-whatsapp`
- **Estado**: `[ ]` pendiente
- **Scope**: Recordatorios y confirmación/cancelación por WhatsApp (`F-07`)
  - Resolver `DP-09` (proveedor) y `PA-11` (momentos de envío, plantillas, opt-in) en el proposal
  - Módulo `Notificaciones`: eventos internos de dominio (alta, confirmación, proximidad) → cola/worker de envío
  - Endpoint de webhook para confirmación/cancelación del paciente que aplica el flujo de cancelación (`RN-04`)
  - La integración externa no bloquea el alta de turnos (`architecture.md` §8)
  - Tests: evento genera envío, error de proveedor no rompe la reserva, confirmación/cancelación desde el mensaje
- **Dependencias**: `C-05`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/flows.md` §6 Flujo de notificaciones y recordatorios
  - `knowledge-base/features.md` §F-07
  - `knowledge-base/decisions.md` §3 DP-09, §4 S-03
  - `knowledge-base/open-questions.md` PA-11

---

### [C-15] `lista-espera`
- **Estado**: `[ ]` pendiente
- **Scope**: Lista de espera y reasignación ante cancelaciones (`F-08`)
  - Modelo de registro de interés por horario ocupado; reglas de prioridad (resolver `PA-14`)
  - Al cancelar un turno (`C-01`/`C-05`), notificar al primero de la lista; reasignación aceptada valida el doble candado
  - Tests: cancelación dispara notificación, reasignación sin solapamiento, prioridad respetada
- **Dependencias**: `C-14`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/features.md` §F-08
  - `knowledge-base/open-questions.md` PA-14
  - `knowledge-base/business-rules.md` §RN-04

---

## Historial de versiones

### [Unreleased] — Roadmap MVP (prioridad: camino crítico)

Orden de ejecución planificado (pendiente):

1. ~~`C-01` **cancelacion-y-estados-turno**~~ ✔ completado (2026-11-03)
2. ~~`C-02` **persistencia-sqlite**~~ ✔ completado (2026-11-03)
3. ~~`C-03` **capa-api-desacoplada**~~ ✔ completado (2026-11-05)
4. ~~`C-04` auth-rbac-tenancy~~ ✔ completado (2026-11-05)
5. ~~`C-05` endpoints-turnos~~ ✔ completado · ~~`C-06` endpoints-recursos~~ ✔ completado · ~~`C-07` gestion-pacientes~~ ✔ completado (2026-11-09)
6. `C-08` reprogramacion-turno · `C-09` admin-recursos-crud · `C-11` frontend-shell
7. `C-10` bloqueo-sillon · `C-12` agenda-turnos-ui — **cierre del MVP**

> Cadena prioritaria: **cancelación y estados de turnos → persistencia en BD → desacouple de backend** (`C-01 → C-02 → C-03`).
> Segunda etapa (post-MVP): `C-13` agenda-matricial, `C-14` notificaciones-whatsapp, `C-15` lista-espera.

### [0.7.0] — 2026-11-09 — Gestión de pacientes ✔ COMPLETADO

- **Patient Management & Isolation (F-11, RN-05, RN-06):** Migración `004_pacientes.sql` con columna `telefono` e índice compuesto `idx_paciente_tenant_dni` (`UNIQUE(tenant_id, dni)`).
- **Core Domain & Persistence:** Entidad pura `Paciente` en `src/domain/models.py` y adaptador `RepositorioPacientesSqlite` en `src/repositories/pacientes_sqlite.py` con aislamiento estricto por `tenant_id`.
- **API & Error Envelope:** Endpoints `POST /api/v1/pacientes` (201) y `GET /api/v1/pacientes` (200) con RBAC (Recepcionista/Admin para alta; Profesional para consulta), validación regex `^\d{8}$` en `dni`, y envelope unificado ante conflictos `PACIENTE_DUPLICADO` (409) y validaciones (422).
- **`2026-11-09-c-07-gestion-pacientes`** — ✔️ Archivado. Spec creada en `openspec/specs/gestionar-pacientes/spec.md` (4 requirements ADDED) y cambio archivado. Suite verde: 189 tests pasados, 100% de cobertura en módulos de pacientes.
- **Skill propia integrada:** `.atl/skills/generador-datos-pacientes-sinteticos.md` — validación formal de privacidad y fixtures sintéticos.

### [0.2.0] — 2026-10-15 — Crear turno sin solapamientos ✔ COMPLETADO

- **Core Domain Entities:** Modelado de `Profesional`, `Sillon`, `Paciente` y `Turno`.
- **Overlap Validation Engine:** Algoritmo de validación bidireccional que previene reservas duplicadas para el mismo profesional o el mismo sillón odontológico en intervalos semiabiertos `[T_inicio, T_fin)`.
- **Automated Test Suite:** Pruebas unitarias e integrales que aseguran el cumplimiento del "doble candado" sin excepciones.
- **`2026-10-15-crear-turno-sin-solapamientos`** — ✔️ Archivado. Specs sincronizados en `openspec/specs/crear-turno/spec.md` (2 requirements ADDED) y cambio movido a `openspec/changes/archive/2026-10-15-crear-turno-sin-solapamientos/`. Suite verde: 8 tests pasados, 100% cobertura.

### [0.3.0] — 2026-11-03 — Cancelación y estados del turno ✔ COMPLETADO

- **State Machine (RN-03):** Constantes `PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO` en `src/domain/models.py` y lista blanca `_TRANSICIONES` en `ServicioTurnos`, con `confirmar()`, `cancelar()` y `completar()` que rechazan cualquier transición no listada con la nueva `TransicionInvalidaError`. Estados `CANCELADO`/`COMPLETADO` absorbentes.
- **Resource Release (RN-04):** Filtro único `ESTADOS_ACTIVOS` en `agendar_turno()` gobierna ambas ramas de validación (profesional **y** sillón), de modo que un turno cancelado o completado deja de bloquear recursos en el intervalo semiabierto `[T_inicio, T_fin)` (D-07) sin perderse del historial.
- **`2026-11-03-c-01-cancelacion-y-estados-turno`** — ✔️ Archivado. Spec creada en `openspec/specs/gestionar-estados-turno/spec.md` (3 requirements ADDED, escenarios en `GIVEN/WHEN/THEN`) y cambio movido a `openspec/changes/archive/2026-11-03-c-01-cancelacion-y-estados-turno/`. Suite verde: 25 tests pasados, 100% cobertura. `openspec validate --all`: 2 passed, 0 failed.
- **Skill propia creada:** `.atl/skills/domain-state-matrix-validator.md` — matriz clasificada de transiciones RN-03/RN-04 y los 3 escenarios Spec-Driven obligatorios.

### [0.1.0] — Discovery & Foundation Phase

- Complete Discovery report with 15 analyzed competitors.
- Manual verification of 5 real market sources.
- Domain knowledge base initialization (`knowledge-base/`).

---

## Resumen

| ID | Change | FASE | Dependencias | Governance | Estado |
|----|--------|------|--------------|------------|--------|
| C-01 | cancelacion-y-estados-turno | 0 · Núcleo del dominio | ninguna | MEDIO | `[x]` |
| C-02 | persistencia-sqlite | 0 · Núcleo del dominio | C-01 | CRITICO | `[x]` |
| C-03 | capa-api-desacoplada | 0 · Núcleo del dominio | C-02 | ALTO | `[ ]` |
| C-04 | auth-rbac-tenancy | 1 · Acceso y tenancy | C-03 | CRITICO | `[ ]` |
| C-05 | endpoints-turnos | 2 · Endpoints de agenda | C-04 | MEDIO | `[ ]` |
| C-06 | endpoints-recursos | 2 · Endpoints de agenda | C-04 | BAJO | `[ ]` |
| C-07 | gestion-pacientes | 2 · Endpoints de agenda | C-04 | BAJO | `[x]` |
| C-08 | reprogramacion-turno | 3 · Operación de la agenda | C-05 | MEDIO | `[ ]` |
| C-09 | admin-recursos-crud | 3 · Operación de la agenda | C-06 | BAJO | `[ ]` |
| C-10 | bloqueo-sillon | 3 · Operación de la agenda | C-09 | ALTO | `[ ]` |
| C-11 | frontend-shell | 4 · Frontend web | C-05, C-06, C-07 | BAJO | `[x]` |
| C-12 | agenda-turnos-ui | 4 · Frontend web | C-11 | MEDIO | `[x]` |
| C-13 | agenda-matricial | 5 · Segunda etapa | C-12 | MEDIO | `[ ]` |
| C-14 | notificaciones-whatsapp | 5 · Segunda etapa | C-05 | ALTO | `[ ]` |
| C-15 | lista-espera | 5 · Segunda etapa | C-14 | MEDIO | `[ ]` |

**Primer change recomendado**: `C-01` (`cancelacion-y-estados-turno`) — inicia el camino crítico MVP con la máquina de estados y la liberación de recursos por cancelación.

Para arrancar: `/opsx:propose C-01-cancelacion-y-estados-turno`
