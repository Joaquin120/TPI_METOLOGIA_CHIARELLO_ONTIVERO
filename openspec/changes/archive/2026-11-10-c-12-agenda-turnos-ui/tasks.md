# Tasks

## 1. Clientes de API y Subcomponentes de UI

- [x] 1.1 Extender los métodos del cliente `frontend/src/api/turnos.ts` (listado con filtros, transiciones de estado y reprogramación) y verificar la tipificación y compilación mediante `npm run build`.
- [x] 1.2 Implementar el componente `FiltrosAgenda.tsx` con selectores de fecha, profesional, sillón y soporte para bloqueo de rol, verificando su renderizado y emisión de eventos con pruebas en Vitest.
- [x] 1.3 Implementar el componente `TarjetaTurno.tsx` con código de colores según tokens de diseño y acciones contextuales por estado (confirmar, cancelar, completar, reprogramar), verificando su renderizado condicional con pruebas en Vitest.

## 2. Modales de Gestión de Turnos

- [x] 2.1 Implementar `ModalNuevoTurno.tsx` con selección de recursos, validación de franjas horarias y panel de alerta para respuestas 409 de solapamiento, verificando su comportamiento con pruebas en Vitest.
- [x] 2.2 Implementar `ModalReprogramarTurno.tsx` para ajustar fecha y franja horaria respetando la retroalimentación de conflictos, verificando su funcionamiento con pruebas en Vitest.

## 3. Integración en Vista Principal y Pruebas Funcionales

- [x] 3.1 Refactorizar `frontend/src/pages/Agenda.tsx` integrando los filtros, la grilla cronológica, el control de roles RBAC y la apertura de modales, verificando los flujos completos en `frontend/src/test/agenda.test.tsx`.
- [x] 3.2 Ejecutar la suite completa de pruebas frontend con `npm test` en el directorio `frontend/` y verificar que el 100% de los tests pasen sin errores ni advertencias.

## Workflow follow-up

- Auditar el cumplimiento con la skill de trazabilidad OpenSpec.
- Archivar el change mediante `/opsx:archive c-12-agenda-turnos-ui`.

