# Proposal: Crear Turno Evitando Solapamientos por Profesional y por Sillón/Box

## Motivación
En un consultorio odontológico, la atención requiere obligatoriamente dos recursos finitos en simultáneo: el profesional de la salud y el sillón/box equipado. El sistema debe evitar reservas duplicadas en el mismo intervalo de tiempo semiabierto $[Inicio, Fin)$.

## Alcance
- Registro de turnos validando solapamientos temporales.
- Lanzamiento de excepciones de dominio específicas ante colisiones.
- Tratamiento formal de intervalos contiguos (turnos seguidos sin solapamiento).