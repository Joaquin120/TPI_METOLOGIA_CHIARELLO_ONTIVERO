# Design System — Consultorio Odontológico SaaS

- **Mode:** system-only
- **Revision:** 1
- **Approval:** approved (2026-11-10, by user)

## Propósito

Define la identidad visual sobria, accesible y clínica para la aplicación web SPA (`frontend/`). Bajo la modalidad **`system-only`**, este sistema de diseño gobierna las variables y componentes globales, y los cambios de interfaz subsiguientes (como la grilla operativa de turnos en `C-12`) se implementan respetando estos tokens sin requerir mockups aislados por change.

## Estructura de Archivos

- `tokens.css`: Variables CSS de colores, tipografía, espaciado, sombras y estados de turno (`PENDIENTE`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`).
- `brand.md`: Documento de identidad de marca, tono y paleta semántica.
- `brand.js`: Enlace para renderizar el nombre de marca en componentes locales.
- `components.html`: Catálogo de referencia HTML interactivo con insignias, tarjetas y botones clínicos.
- `assets/logo.svg`: Isotipo vectorial clínico del producto.

## Reemplazo y Mantenimiento

Para actualizar valores visuales o marcas:
1. Modificar los valores de color o tipografía en `tokens.css`.
2. Actualizar el isotipo en `assets/logo.svg`.
3. Para ajustar el nombre comercial visible, editar la constante `window.BRAND_NAME` en `brand.js`.

