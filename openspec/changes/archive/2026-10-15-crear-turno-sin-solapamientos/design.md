# Design: Algoritmo de Detección de Solapamientos

## Lógica Matemática de Intervalos
Dos intervalos $A = [A_{inicio}, A_{fin})$ y $B = [B_{inicio}, B_{fin})$ se solapan si y solo si:
$$A_{inicio} < B_{fin} \quad \text{and} \quad A_{fin} > B_{inicio}$$

Si $A_{fin} == B_{inicio}$, **NO hay solapamiento** (es un caso contiguo válido).

## Excepciones de Dominio
- `SolapamientoProfesionalError`: Cuando el profesional ya tiene un turno asignado que colisiona en horario.
- `SolapamientoSillonError`: Cuando el sillón/box ya está ocupado en ese rango horario.