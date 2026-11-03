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
- **Estado**: `[ ]` pendiente
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
- **Estado**: `[ ]` pendiente
- **Scope**: Autenticación, roles y resolución de tenant desde la sesión
  - Resolver en el proposal las decisiones `DP-04` (auth/sesiones) y `DP-03` (aislamiento multi-tenant)
  - Migración 002: tabla `usuario` con `tenant_id`, `email`, `rol` (`Administrador`, `Recepcionista`, `Profesional`), `profesional_id` opcional
  - `POST /api/v1/auth/login` — JWT con claims `sub`, `tenant_id`, `rol`; `GET /api/v1/auth/me`
  - Dependency/mediddleware que resuelve el tenant de la sesión e inyecta el contexto en los repositorios (`RN-05`)
  - RBAC mínimo según matriz de permisos: recepción opera agenda, admin configura recursos, profesional solo consulta agenda propia
  - Tests: login OK, token inválido/expirado, fuga de datos entre tenants bloqueada, permisos por rol
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
- **Estado**: `[ ]` pendiente
- **Scope**: API REST completa del módulo Agenda (`F-01`, `F-02`, `F-03`)
  - `POST /api/v1/turnos` — alta con doble validación delegada al dominio (`RN-01`, `RN-09`), estado inicial `CONFIRMADO`
  - `GET /api/v1/turnos` — filtros `profesional_id`, `sillon_id`, `fecha`; solo turnos del tenant (`RN-05`); el `Profesional` solo ve los propios
  - `PATCH /api/v1/turnos/{id}/estado` — confirmar / cancelar / completar según `RN-03`; cancelación libera recursos (`RN-04`)
  - Tests: camino feliz, conflicto de profesional, conflicto de sillón, contiguos, filtros, transiciones inválidas rechazadas, aislamiento por tenant
- **Dependencias**: `C-04`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/features.md` §F-01, §F-02, §F-03, §5 Endpoints
  - `knowledge-base/flows.md` §2 Flujo de creación, §3 Flujo de cambio de estado
  - `knowledge-base/business-rules.md` §RN-01, §RN-03, §RN-09
  - `knowledge-base/actors.md` §3 Matriz de permisos

---

### [C-06] `endpoints-recursos`
- **Estado**: `[ ]` pendiente
- **Scope**: Consulta de recursos para asignar turnos (`F-04`, `F-05`)
  - `GET /api/v1/profesionales` — lista del tenant, con `matricula`, `especialidad`, `activo`
  - `GET /api/v1/sillones` — lista del tenant, con `equipamiento` y `activo`
  - Seed sintético ampliado (datos ficticios: `Dr. Ejemplo`, `Sillón 1`)
  - Tests: listados acotados al tenant, inclusión/exclusión de recursos inactivos según decisión de `PA-01` adoptada en el proposal
- **Dependencias**: `C-04`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/features.md` §F-04, §F-05, §5 Endpoints
  - `knowledge-base/data-models.md` §2.2 Profesional, §2.3 Sillón
  - `knowledge-base/business-rules.md` §RN-05

---

### [C-07] `gestion-pacientes`
- **Estado**: `[ ]` pendiente
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

## FASE 3 — Operación de la agenda

### [C-08] `reprogramacion-turno`
- **Estado**: `[ ]` pendiente
- **Scope**: Reprogramar un turno existente (`F-09`)
  - Resolver en el proposal `RP-03`: cancelación + alta, o modificación in-place del turno
  - Endpoint de reprogramación (contrato por definir: `PATCH /api/v1/turnos/{id}` o equivalente)
  - Validar el nuevo intervalo con el doble candado (`RN-01`, `RN-02`); liberar el horario anterior; conservar trazabilidad del cambio
  - Tests: nuevo horario sin solapamiento, liberación del horario anterior, conflicto en el destino rechazado, trazo del cambio
- **Dependencias**: `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/features.md` §F-09
  - `knowledge-base/flows.md` §5 Flujo de reprogramación
  - `knowledge-base/business-rules.md` §RP-03, §RN-01
  - `knowledge-base/open-questions.md` PA-06

---

### [C-09] `admin-recursos-crud`
- **Estado**: `[ ]` pendiente
- **Scope**: Administración de recursos por el Administrador (`F-10`, endpoints que figuran pendientes)
  - `POST /api/v1/profesionales`, `PUT /api/v1/profesionales/{id}` — alta/edición con `matricula`, `especialidad`, `activo`
  - `POST /api/v1/sillones`, `PUT /api/v1/sillones/{id}` — alta/edición con `equipamiento`, `activo`
  - RBAC: solo `Administrador` (matriz de permisos); un recurso creado queda disponible para asignar turnos
  - Sin modelo de horarios aún (`DP-08` sigue abierto — no resolver aquí)
  - Tests: alta → recurso utilizable en un turno, permisos por rol, aislamiento por tenant
- **Dependencias**: `C-06`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/features.md` §F-10, §5 Endpoints
  - `knowledge-base/actors.md` §2.1 Administrador, §3 Matriz de permisos
  - `knowledge-base/data-models.md` §2.2, §2.3
  - `knowledge-base/open-questions.md` PA-16

---

### [C-10] `bloqueo-sillon`
- **Estado**: `[ ]` pendiente
- **Scope**: Bloqueo de sillón por mantenimiento (`F-12`, `RN-07`)
  - Resolver en el proposal `PA-15` / `PA-16` / `RP-07`: turno de bloqueo vs. inactivación del recurso
  - Implementar el mecanismo elegido: si es turno de bloqueo, participa en la validación de solapamiento junto a los turnos activos
  - Endpoint de autorización del bloqueo (Administrador), alta/edición de `activo` en sillones
  - Tests: sillón bloqueado no recibe turnos en el intervalo, turnos existentes según `RP-07`, inactivación impide nuevas reservas, integración con doble candado
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
- **Estado**: `[ ]` pendiente
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
- **Estado**: `[ ]` pendiente
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
3. `C-03` **capa-api-desacoplada**
4. `C-04` auth-rbac-tenancy
5. `C-05` endpoints-turnos · `C-06` endpoints-recursos · `C-07` gestion-pacientes (paralelo)
6. `C-08` reprogramacion-turno · `C-09` admin-recursos-crud · `C-11` frontend-shell
7. `C-10` bloqueo-sillon · `C-12` agenda-turnos-ui — **cierre del MVP**

> Cadena prioritaria: **cancelación y estados de turnos → persistencia en BD → desacouple de backend** (`C-01 → C-02 → C-03`).
> Segunda etapa (post-MVP): `C-13` agenda-matricial, `C-14` notificaciones-whatsapp, `C-15` lista-espera.

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
| C-07 | gestion-pacientes | 2 · Endpoints de agenda | C-04 | BAJO | `[ ]` |
| C-08 | reprogramacion-turno | 3 · Operación de la agenda | C-05 | MEDIO | `[ ]` |
| C-09 | admin-recursos-crud | 3 · Operación de la agenda | C-06 | BAJO | `[ ]` |
| C-10 | bloqueo-sillon | 3 · Operación de la agenda | C-09 | ALTO | `[ ]` |
| C-11 | frontend-shell | 4 · Frontend web | C-05, C-06, C-07 | BAJO | `[ ]` |
| C-12 | agenda-turnos-ui | 4 · Frontend web | C-11 | MEDIO | `[ ]` |
| C-13 | agenda-matricial | 5 · Segunda etapa | C-12 | MEDIO | `[ ]` |
| C-14 | notificaciones-whatsapp | 5 · Segunda etapa | C-05 | ALTO | `[ ]` |
| C-15 | lista-espera | 5 · Segunda etapa | C-14 | MEDIO | `[ ]` |

**Primer change recomendado**: `C-01` (`cancelacion-y-estados-turno`) — inicia el camino crítico MVP con la máquina de estados y la liberación de recursos por cancelación.

Para arrancar: `/opsx:propose C-01-cancelacion-y-estados-turno`
