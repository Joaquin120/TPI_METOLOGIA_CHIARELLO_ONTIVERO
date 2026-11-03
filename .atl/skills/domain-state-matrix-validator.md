---
name: domain-state-matrix-validator
description: Valida que la máquina de estados de turnos respete RN-03 (matriz de transiciones) y RN-04 (liberación por cancelación) antes de redactar o revisar proposal.md, design.md o specs/ de un change que defina o modifique estados y transiciones de turnos o recursos. Triggers: "validar estados", "matriz de transiciones", "máquina de estados del turno", "validar RN-03", "validar RN-04", "estados terminales", "liberación de recursos al cancelar", o al escribir/probar transiciones `confirmar`/`cancelar`/`completar`.
---

# Domain State Matrix Validator

Valida formalmente la máquina de estados del turno contra la matriz de transiciones
(RN-03) y la regla de liberación de recursos (RN-04), antes de que se escriba código o
tests de estados. Es una **puerta de calidad de especificación**, no un test runner.

## Cuándo invocarla

- Al redactar o revisar `proposal.md`, `design.md` o `specs/` de cualquier change que
  defina o modifique **estados y transiciones de turnos o recursos**
  (en especial `C-01 cancelacion-y-estados-turno`).
- Nunca escribir la máquina de estados ni sus tests sin pasar antes por esta skill.

## Insumos a consultar ANTES de usarla

- `knowledge-base/business-rules.md` → §RN-03 (matriz de transiciones),
  §RN-04 (liberación por cancelación), §RN-02/§RN-09 (solapamiento y precedencia).
- `knowledge-base/data-models.md` → §4.1 Estado del turno.
- `knowledge-base/decisions.md` → `D-07` (intervalos semiabiertos `[inicio, fin)`).
- `openspec/specs/crear-turno/spec.md` → spec vigente del alta
  (`PA-13` abierta: el estado inicial del alta **no** se resuelve en el change).

---

## 1. Matriz clasificada de estados

### Estados y efecto sobre recursos (data-models §4.1)

| Estado | Significado | Bloquea recursos | Clase |
|---|---|---|---|
| `PENDIENTE` | Registrado a la espera de confirmación | **Sí** | Activo |
| `CONFIRMADO` | Confirmado para la atención | **Sí** | Activo |
| `CANCELADO` | Anulado por paciente o clínica | No | **Terminal** |
| `COMPLETADO` | Atención finalizada | No | **Terminal** |

`ESTADOS_ACTIVOS = frozenset({PENDIENTE, CONFIRMADO})` — solo estos dos participan de
la validación de solapamiento.

### Transiciones PERMITIDAS (RN-03) — lista blanca

| Estado actual | Acción | Estado destino | Efecto sobre recursos |
|---|---|---|---|
| `PENDIENTE` | `confirmar()` | `CONFIRMADO` | Mantiene reservados profesional y sillón |
| `PENDIENTE` | `cancelar()` | `CANCELADO` | **Libera** profesional y sillón |
| `CONFIRMADO` | `cancelar()` | `CANCELADO` | **Libera** profesional y sillón |
| `CONFIRMADO` | `completar()` | `COMPLETADO` | **Libera** profesional y sillón (cierra la atención) |

### Transiciones PROHIBIDAS — todo lo que NO está arriba

Criterio de **lista blanca, no lista negra**: si el par `(estado, acción)` no figura en
la tabla anterior, la transición es inválida. Prohibiciones explícitas:

| Estado actual | Acción | Resultado |
|---|---|---|
| `CANCELADO` | `confirmar()` / `cancelar()` / `completar()` | ❌ → `TransicionInvalidaError` |
| `COMPLETADO` | `confirmar()` / `cancelar()` / `completar()` | ❌ → `TransicionInvalidaError` |
| `CONFIRMADO` | `confirmar()` | ❌ → `TransicionInvalidaError` (no está en RN-03) |
| `PENDIENTE` | `completar()` | ❌ → `TransicionInvalidaError` (no está en RN-03) |

**Estados terminales absorbentes:** `CANCELADO` y `COMPLETADO` tienen **cero
transiciones salientes**. Toda acción originada en ellos se rechaza con
`TransicionInvalidaError` y el turno **permanece sin modificación alguna**.

### Contrato de la excepción

```python
class TransicionInvalidaError(Exception):
    """La transición solicitada no está permitida para el estado actual del turno."""

    def __init__(self, mensaje: str = "La transición no es válida para el estado del turno") -> None:
        super().__init__(mensaje)
```

- Hereda de `Exception` (no de una excepción de solapamiento: no es un caso de solape).
- Mensaje por defecto **en español**, sobreescribible con `estado actual` y `acción`.
- Ninguna excepción existente se renombra ni se modifica.

---

## 2. Los 3 escenarios Spec-Driven obligatorios

Toda spec o change que toque estados y transiciones DEBE contener estos 3 escenarios,
en formato **Given/When/Then** con los keywords literales en inglés
(`openspec validate` rechaza `Dado/Cuando/Entonces`):

### Escenario A — Esperado (camino feliz de liberación)

**GIVEN** un turno en estado `CONFIRMADO` que ocupa el intervalo `[T_inicio, T_fin)`
del profesional **P** y el sillón **S**
**WHEN** se ejecuta la acción `cancelar()` sobre ese turno
**THEN** el turno pasa a estado `CANCELADO` y **ni el profesional ni el sillón**
quedan bloqueados en `[T_inicio, T_fin)`

*Criterio de aceptación:* ambos recursos quedan disponibles **de forma simultánea e
independiente** (regla dura 2 — doble validación).

### Escenario B — Error de negocio (estados terminales)

**GIVEN** un turno en estado terminal `CANCELADO` (o `COMPLETADO`)
**WHEN** se intenta una transición saliente, p. ej. `completar()` de `CANCELADO`
a `COMPLETADO`
**THEN** el sistema rechaza la operación lanzando `TransicionInvalidaError` y el
turno **permanece en su estado actual** sin modificación alguna

*Criterio de aceptación:* la excepción sigue el patrón de
`backend/src/domain/exceptions.py` y el estado registrado no cambió.

### Escenario C — Caso de borde (liberación en intervalo semiabierto)

**GIVEN** que un turno del profesional **P** en el sillón **S** de `[T_inicio, T_fin)`
acaba de ser cancelado
**WHEN** se solicita un nuevo turno para **ese mismo profesional y ese mismo sillón**
dentro del intervalo liberado (p. ej. que empieza en `T_inicio` y termina después de
`T_fin`, o que comienza exactamente en `T_fin`)
**THEN** la creación es exitosa: el turno cancelado no bloquea (RN-04) y el
solapamiento se evalúa con el criterio semiabierto `inicio_a < fin_b AND fin_a > inicio_b`
(D-07)

*Criterio de aceptación:* dos variantes deben probarse —
(a) re-reserva **dentro** del intervalo liberado → exitosa;
(b) re-reserva **contigua** que empieza exactamente en `T_fin` → exitosa, porque
`fin_del_turno_cancelado == inicio_del_nuevo` **no** constituye solapamiento.

---

## 3. Criterio verde (regla dura 4)

La skill **no** da por terminada la tarea si la suite falla. Verificación obligatoria:

```bash
cd backend && pytest                    # 100% en verde
cd backend && pytest --cov=src          # cubriendo exceptions.py, models.py, services.py
cd backend && pytest tests/test_estados_turno.py -v   # trazabilidad escenario → test
```

Los tests existentes de cualquier change previo deben seguir verdes **sin modificarse**
(red de seguridad).

## 4. Checklist de validación

- [ ] Los 4 estados están definidos como constantes en `src/domain/models.py`
      (fuente de verdad de `Turno.estado`), sin alterar el default vigente del alta.
- [ ] La matriz de transiciones es una **lista blanca** única y centralizada.
- [ ] `CANCELADO` y `COMPLETADO` son absorbentes: cero transiciones salientes.
- [ ] `TransicionInvalidaError` existe, hereda de `Exception`, con default en español.
- [ ] El filtro de bloqueo usa `ESTADOS_ACTIVOS` y gobierna **ambas** ramas
      (profesional **y** sillón) con un solo guard.
- [ ] `_hay_solapamiento()` sigue siendo semiabierto: `inicio_a < fin_b AND fin_a > inicio_b`.
- [ ] El turno cancelado **se conserva como historial** (no se borra de la lista).
- [ ] Los 3 escenarios A/B/C están presentes en la spec, en `GIVEN/WHEN/THEN`.
- [ ] La suite completa está en verde al 100%.

## 5. Fuera de alcance de esta skill

- `PA-13` — estado inicial del alta (`PENDIENTE` vs `CONFIRMADO`): change propio.
- `PA-06` / `RP-04` — política de cancelación y roles autorizados (`C-04`).
- `RP-03` — reprogramación. `RP-06` — concurrencia.
- Persistencia del filtro en SQL: alcance de `C-02`.
