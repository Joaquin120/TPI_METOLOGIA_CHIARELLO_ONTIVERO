# Design

## Context

`ServicioTurnos` (`backend/src/domain/services.py`) agrega turnos en memoria y valida solapamientos con `_hay_solapamiento()` — intervalos semiabiertos `[inicio, fin)` (D-07) — aplicando doble validación simultánea e independiente de profesional y sillón (regla dura 2). Pero no expone transiciones de estado: `Turno.estado` es un `str` con default `"CONFIRMADO"` (spec vigente `crear-turno`) y jamás cambia; `agendar_turno()` compara contra todos los turnos registrados, sin distinguir activos de finalizados. Las excepciones de dominio siguen el patrón de `backend/src/domain/exceptions.py` (`*Error(Exception)` con `__init__(self, mensaje: str = ...)` y docstring). La suite `backend/tests/test_turnos.py` tiene 8 tests que deben seguir verdes (regla dura 4). La motivación completa está en `proposal.md — Why`.

## Goals / Non-Goals

**Goals:**

- Exponer las transiciones de RN-03 en `ServicioTurnos` (`confirmar()`, `cancelar()`, `completar()`) rechazando las inválidas con la nueva `TransicionInvalidaError`.
- Hacer que el filtro de solapamiento solo considere turnos **activos** (`PENDIENTE`/`CONFIRMADO`), de modo que cancelar libere profesional y sillón en `[T_inicio, T_fin)` (RN-04) con criterio semiabierto (D-07).
- Mantener la suite existente en verde y cubrir con tests los 3 escenarios obligatorios de la skill `domain-state-matrix-validator`.

**Non-Goals:**

- Resolver `PA-13` (estado inicial del alta): se mantiene `CONFIRMADO` según la spec vigente `crear-turno`.
- Persistencia (`C-02`), API (`C-03`/`C-05`), auth/RBAC y roles (`C-04`), política de cancelación (`PA-06`, `RP-04`), reprogramación (`RP-03`) y concurrencia (`RP-06`).
- Modificar la spec `crear-turno`, renombrar o alterar las excepciones existentes, o tocar `CHANGES.md`.

## Decisions

### D1. Constantes de estado en `models.py`, no un `Enum`

Se definen cuatro constantes de módulo en `backend/src/domain/models.py` — `PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO` — y `Turno.estado` sigue siendo `str` con default `"CONFIRMADO"`.

- *Alternativa descartada*: `enum.Enum` / `StrEnum`. Rompería la igualdad literal `turno.estado == "CONFIRMADO"` que ya usan los 8 tests existentes (a menos que herede de `str`, lo que suma conversión sin beneficio en MVP), y `C-02` persistirá `estado` como texto en SQLite.
- *Alternativa descartada*: inlinear los literales en el servicio. Centraliza la fuente de verdad en un solo lugar y evita "strings mágicos" repetidos.

### D2. Matriz de transiciones como lista blanca en el servicio

Un único mapa `_TRANSICIONES: dict[tuple[str, str], str]` en `ServicioTurnos` relaciona `(estado_actual, acción) → estado_destino`; toda acción **no listada** es inválida (lista blanca, no lista negra — criterio de la skill `domain-state-matrix-validator`). Matriz validada contra RN-03:

| Estado actual | Acción | Estado destino | Válida | Efecto sobre recursos |
|---|---|---|---|---|
| `PENDIENTE` | Confirmar | `CONFIRMADO` | ✅ | Mantiene reservados profesional y sillón |
| `PENDIENTE` | Cancelar | `CANCELADO` | ✅ | Libera profesional y sillón |
| `CONFIRMADO` | Cancelar | `CANCELADO` | ✅ | Libera profesional y sillón |
| `CONFIRMADO` | Completar | `COMPLETADO` | ✅ | Libera profesional y sillón (cierra la atención) |
| `CANCELADO` | cualquiera | — | ❌ → `TransicionInvalidaError` | Estado final absorbente (cero transiciones salientes) |
| `COMPLETADO` | cualquiera | — | ❌ → `TransicionInvalidaError` | Estado final absorbente (cero transiciones salientes) |

No se agrega ni se omite ningún par respecto de RN-03; `confirmar()` desde `CONFIRMADO` también es inválida (no está listada).

### D3. Contrato de `TransicionInvalidaError`

Nueva excepción en `backend/src/domain/exceptions.py`, idéntica en forma a las existentes:

```python
class TransicionInvalidaError(Exception):
    """La transición solicitada no está permitida para el estado actual del turno."""

    def __init__(self, mensaje: str = "La transición no es válida para el estado del turno") -> None:
        super().__init__(mensaje)
```

- Hereda de `Exception` (no de otra excepción de dominio: no es un caso de solapamiento).
- Mensaje por defecto **en español**, sobreescribible con detalle (`estado actual`, `acción`) desde el servicio.
- Ninguna excepción existente se renombra ni se modifica.

### D4. Liberación por filtro de estados activos sobre profesional Y sillón

`agendar_turno()` suma, **antes** de las dos ramas de validación, un único guard: `if turno_existente.estado not in ESTADOS_ACTIVOS: continue`, con `ESTADOS_ACTIVOS = frozenset({PENDIENTE, CONFIRMADO})`.

- El mismo filtro gobierna ambas ramas (profesional y sillón): un turno `CANCELADO`/`COMPLETADO` no bloquea **ni el profesional ni el sillón** — liberación simultánea e independiente (regla dura 2, RN-04).
- `_hay_solapamiento()` no cambia: sigue `inicio_a < fin_b AND fin_a > inicio_b` (D-07), por lo que un turno nuevo que empieza exactamente en `T_fin` del cancelado es contiguo, no solapado (RN-02).
- *Alternativa descartada*: eliminar de la lista el turno cancelado. Violenta RN-04/flows §4: el turno cancelado se conserva como historial.
- *Alternativa descartada*: duplicar el chequeo de estado dentro de cada rama. Multiplica puntos de fallo y arriesga que un recurso se libere y el otro no.

### D5. Transiciones inmutables sobre `Turno` con `dataclasses.replace`

`Turno` es un `@dataclass(frozen=True)`; no admite asignación directa a `estado`. Cada método de transición calcula el turno nuevo con `dataclasses.replace(turno, estado=NUEVO_ESTADO)`, **reemplaza la entrada en `self._turnos`** y devuelve la instancia actualizada.

- *Alternativa descartada*: quitar `frozen=True`. Pierde la semántica de valor inmutable del dominio y habilita estados seteados desde cualquier lado, saltándose la matriz.
- *Alternativa descartada*: `object.__setattr__` como workaround. Rompe el contrato del dataclass congelado de forma opaca.
- **Contrato documentado**: el estado canónico es el del turno devuelto por el método y el almacenado en `turnos_registrados()`; la referencia anterior queda como snapshot del estado previo. Los tests y consumidores usan siempre la instancia devuelta.

### D6. Alta en `CONFIRMADO` preservada (`PA-13` abierta)

`Turno.estado` conserva default `"CONFIRMADO"` y la spec `crear-turno` no se modifica. `PENDIENTE` existe en la máquina de estados y es alcanzable explícitamente (los tests lo instancian directamente), pero cambiar el estado inicial del alta requiere resolver `PA-13` en un change propio.

### D7. Tests nuevos en archivo aparte

Los tests del ciclo de vida van en `backend/tests/test_estados_turno.py` (nuevo); `backend/tests/test_turnos.py` no se toca, así los 8 tests existentes quedan como red de seguridad intacta del cambio (regla dura 4).

## Risks / Trade-offs

- [Un punto de validación futuro olvide filtrar por estado activo y un turno cancelado vuelva a bloquear] → Mitigación: el filtro se centraliza en la constante `ESTADOS_ACTIVOS` y en un solo guard de `agendar_turno()`; `C-02` deberá replicar el criterio en SQL (ya previsto en su scope: "turnos cancelados no bloquean vía BD").
- [`dataclasses.replace` devuelve instancias nuevas: una referencia vieja al turno conserva su estado anterior] → Mitigación: contrato documentado en D5; los tests leen el estado vía el valor devuelto o `turnos_registrados()`.
- [Firma de `agendar_turno()` intacta, pero su comportamiento se estrecha (ignora turnos finalizados): una regresión aquí afecta también a la capability `crear-turno`] → Mitigación: los 8 tests de `test_turnos.py` siguen corriendo sin cambios y validan el comportamiento previo.
- [`PENDIENTE` no es alcanzable desde el alta en este change: `confirmar()` sobre `PENDIENTE` queda probado solo con estados construidos en test] → Mitigación: aceptado y acotado; la decisión del alta es `PA-13`, fuera de alcance.
- [Concurrencia (`RP-06`) fuera de alcance: dos acciones simultáneas sobre el mismo turno no están protegidas] → Mitigación: el servicio es monohilo en memoria en el MVP; queda documentado como pendiente, sin impacto en este diseño.

## Migration Plan

No aplica: sin despliegue, sin persistencia ni datos externos. El cambio es backwards-compatible en memoria (la firma pública no cambia; solo se agregan métodos y constantes). Rollback = revertir el commit del change; no hay datos que migrar. `C-02` heredará el filtro de estados activos al llevar la validación a SQLite.

## Open Questions

- **`PA-13` — estado inicial del alta**: diferida fuera de este change a propósito (spec vigente manda `CONFIRMADO`). Resolverla cambiaría la spec `crear-turno`, no este diseño mientras se preserve ese valor.
- **Rol autorizado para `completar()`** (F-03: "la finalización queda pendiente de asignación de rol"): diferida a `C-04` (auth-rbac-tenancy). El dominio no valida roles; la validación de permisos vive en la capa de API.
