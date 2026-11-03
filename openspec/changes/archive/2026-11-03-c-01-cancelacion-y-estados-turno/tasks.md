# Tasks

## 1. Constantes de estado del dominio (TDD: rojo → verde)

- [x] 1.1 Escribir el test rojo `test_constantes_de_estado_disponibles` en `backend/tests/test_estados_turno.py`: importar `PENDIENTE`, `CONFIRMADO`, `CANCELADO` y `COMPLETADO` desde `src.domain.models`, verificar que son cuatro valores distintos y que un `Turno` sigue naciendo en `CONFIRMADO` — verificación: `cd backend && pytest tests/test_estados_turno.py -k constantes` **falla con ImportError/AttributeError (rojo)**
- [x] 1.2 Implementar las cuatro constantes de estado en `backend/src/domain/models.py` (fuente de verdad de `Turno.estado`, sin alterar el default `"CONFIRMADO"`) — verificación: `cd backend && pytest tests/test_estados_turno.py -k constantes` pasa (verde)

## 2. Excepción de dominio `TransicionInvalidaError` (TDD: rojo → verde)

- [x] 2.1 Escribir el test rojo `test_transicion_invalida_sigue_el_patron_de_excepciones`: `issubclass(TransicionInvalidaError, Exception)`, `str(TransicionInvalidaError())` contiene el mensaje por defecto en español y `TransicionInvalidaError("detalle propio")` lo propaga — verificación: `cd backend && pytest tests/test_estados_turno.py -k transicion_invalida` **falla con ImportError (rojo)**
- [x] 2.2 Implementar `TransicionInvalidaError` en `backend/src/domain/exceptions.py` con el contrato de las excepciones existentes (design D3: hereda de `Exception`, `__init__(self, mensaje: str = "<defecto en español>")`, docstring), sin renombrar ni modificar ninguna excepción actual — verificación: `cd backend && pytest tests/test_estados_turno.py -k transicion_invalida` pasa (verde) y `cd backend && pytest tests/test_turnos.py` sigue en 8 verdes

## 3. Transiciones válidas en `ServicioTurnos` (TDD: rojo → verde)

- [x] 3.1 Escribir los tests rojos del camino feliz de la spec (`#### Scenario: Confirmación de un turno pendiente` y `#### Scenario: Finalización de un turno confirmado`): `test_confirmar_pendiente_pasa_a_confirmado`, `test_cancelar_confirmado_pasa_a_cancelado` y `test_completar_confirmado_pasa_a_completado`, asertiando sobre la instancia devuelta por el servicio (design D5) — verificación: `cd backend && pytest tests/test_estados_turno.py -k "confirmar or cancelar or completar"` **falla con AttributeError: métodos inexistentes (rojo)**
- [x] 3.2 Implementar `confirmar()`, `cancelar()` y `completar()` en `ServicioTurnos` (`backend/src/domain/services.py`) con la lista blanca `_TRANSICIONES (estado, acción) → estado_destino` (design D2, matriz de RN-03) y `dataclasses.replace` para actualizar el estado del turno congelado, reemplazando la entrada en `self._turnos` — verificación: `cd backend && pytest tests/test_estados_turno.py -k "confirmar or cancelar or completar"` pasa (verde) y `cd backend && pytest tests/test_turnos.py` sigue en 8 verdes

## 4. Estados finales absorbentes (TDD: rojo → verde) — Escenario de Error de Negocio

- [x] 4.1 Escribir los tests rojos `test_estado_final_cancelado_no_admite_completar`, `test_estado_final_cancelado_no_admite_cancelar` y `test_estado_final_completado_no_admite_cancelar`, cada uno con `pytest.raises(TransicionInvalidaError)` y aserción de que el estado no cambió (spec: `#### Scenario: Completar un turno cancelado se rechaza`) — verificación: `cd backend && pytest tests/test_estados_turno.py -k estado_final` **falla (rojo)**
- [x] 4.2 Implementar el rechazo en los tres métodos: par `(estado, acción)` ausente de `_TRANSICIONES` → `TransicionInvalidaError` con el estado actual y la acción en el mensaje, sin mutar el turno (design D2/D3) — verificación: `cd backend && pytest tests/test_estados_turno.py -k estado_final` pasa (verde)

## 5. Liberación de recursos por cancelación (RN-04 + D-07, TDD: rojo → verde) — Escenarios Esperado y de Borde

- [x] 5.1 Escribir los tests rojos `test_liberacion_cancelar_libera_profesional_y_sillon` (escenario Esperado de la spec: turno `CONFIRMADO` 10:00–10:30 cancelado → re-agendar el mismo profesional **y** el mismo sillón dentro de `["10:00", "10:30")` sin excepción, más sus variantes de doble validación: otro profesional con el mismo sillón y otro sillón con el mismo profesional) y `test_liberacion_turno_completado_no_bloquea` — verificación: `cd backend && pytest tests/test_estados_turno.py -k liberacion` **falla con `SolapamientoProfesionalError` (rojo)**
- [x] 5.2 Escribir el test de regresión del caso de borde `test_liberacion_re_reserva_contigua_en_t_fin` (spec: re-reserva que empieza exactamente en `T_fin` del turno cancelado → registrada en `CONFIRMADO`); ya debe pasar por D-07 antes del cambio y actuar como red de seguridad — verificación: `cd backend && pytest tests/test_estados_turno.py -k re_reserva_contigua` pasa (verde, regresión)
- [x] 5.3 Implementar el filtro `ESTADOS_ACTIVOS = frozenset({PENDIENTE, CONFIRMADO})` en `agendar_turno()`, antes de las ramas de validación de profesional y de sillón, de modo que `CANCELADO`/`COMPLETADO` no bloqueen ninguno de los dos recursos con el mismo guard (design D4; `_hay_solapamiento` sin cambios) — verificación: `cd backend && pytest tests/test_estados_turno.py -k "liberacion or re_reserva_contigua"` pasa (verde) y `cd backend && pytest tests/test_turnos.py` sigue en 8 verdes

## 6. Verificación integral de la suite

- [x] 6.1 Correr la suite completa: `cd backend && pytest` — todos los tests en verde: los 8 existentes de `tests/test_turnos.py` sin modificar + los nuevos de `tests/test_estados_turno.py` (regla dura 4: suite verde al 100%)
- [x] 6.2 Correr la suite con cobertura: `cd backend && pytest --cov=src` — sin fallas y cubriendo `src/domain/exceptions.py`, `src/domain/models.py` y `src/domain/services.py` (regla dura 4)
- [x] 6.3 Verificar la trazabilidad spec → tests de los 3 escenarios obligatorios de la skill `domain-state-matrix-validator`: `cd backend && pytest tests/test_estados_turno.py -v` muestra activos los tests del escenario Esperado (`-k liberacion`), del Error de Negocio (`-k estado_final`) y del Caso de Borde (`-k re_reserva_contigua`), todos contra `specs/gestionar-estados-turno/spec.md`

## Workflow follow-up

- Corregir `proposal.md`, `design.md`, `specs/` o `tasks.md` si `openspec validate c-01-cancelacion-y-estados-turno` (o `--strict`) reporta errores, antes de tocar `backend/`.
- Ejecutar `openspec archive c-01-cancelacion-y-estados-turno` solo una vez que el change esté implementado y revisado (prohibido en la fase de planificación actual).
- Marcar `[x]` en `CHANGES.md` §C-01 recién al archivar el change (no en esta fase).
