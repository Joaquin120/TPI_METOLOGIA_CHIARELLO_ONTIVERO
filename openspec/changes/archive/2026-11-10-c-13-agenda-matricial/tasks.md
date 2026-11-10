# Tasks

## 1. Componentes de Matriz y Mapeo Horario

- [x] 1.1 Implementar utilidades de cálculo de franjas horarias y proyección de turnos en `frontend/src/utils/matrizHoraria.ts` y verificar su lógica con pruebas unitarias en Vitest.
- [x] 1.2 Implementar el componente `GrillaMatricial.tsx` con soporte para agrupación por sillón o por profesional y código de colores de turnos, verificando su renderizado con pruebas en Vitest.
- [x] 1.3 Integrar la visualización de franjas de bloqueo por mantenimiento en `GrillaMatricial.tsx` y verificar la inhabilitación visual mediante pruebas unitarias.

## 2. Integración en Vista Agenda y Acciones Rápidas

- [x] 2.1 Incorporar selector de modo de vista (Lista / Matriz) y consulta de bloqueos en `frontend/src/pages/Agenda.tsx`, verificando la alternancia fluida con pruebas en `frontend/tests/agenda.test.tsx`.
- [x] 2.2 Habilitar interacciones directas sobre celdas (apertura de alta con preselección en celdas libres y gestión de turnos existentes), verificando los flujos en `frontend/tests/agenda.test.tsx`.

## 3. Verificación de Suite Completa y Compilación

- [x] 3.1 Ejecutar la suite completa de pruebas frontend mediante `npm test` en `frontend/` y verificar que todos los tests pasen sin errores.
- [x] 3.2 Verificar la compilación estricta del proyecto mediante `npm run build` confirmando ausencia de errores de tipado en TypeScript.

## Workflow follow-up

- Auditar el cumplimiento con la skill de trazabilidad OpenSpec.
- Archivar el change mediante `/opsx:archive c-13-agenda-matricial`.

