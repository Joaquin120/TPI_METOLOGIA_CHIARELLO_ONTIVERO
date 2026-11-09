# Tasks

## 1. Migración de esquema y modelos de dominio

- [x] 1.1 Crear migración `backend/src/infrastructure/migrations/003_recursos.sql` añadiendo columnas `matricula`, `especialidad`, `activo` a `profesional` y `equipamiento`, `activo` a `sillon`; verificar su aplicación idempotente mediante `migrar(conexion)`.
- [x] 1.2 Extender entidades `Profesional` y `Sillon` en `backend/src/domain/models.py` con nuevos atributos y defaults retrocompatibles; verificar que los 155 tests existentes y los guard tests de pureza (`test_pureza_dominio.py`) permanezcan en verde.

## 2. Repositorios de recursos y semilla sintética

- [x] 2.1 Actualizar `RepositorioProfesionales` y `RepositorioSillones` en `backend/src/repositories/recursos.py` para leer los nuevos campos y soportar el parámetro `solo_activos: bool = True` acotado al tenant; verificar con tests de persistencia en SQLite real.
- [x] 2.2 Ampliar `sembrar_datos_iniciales()` en `backend/src/infrastructure/seed.py` con datos sintéticos completos (matrículas, especialidades, equipamiento y recursos inactivos de prueba); verificar idempotencia de la semilla.

## 3. Capa API y endpoints REST de recursos

- [x] 3.1 Crear esquemas Pydantic `ProfesionalRespuesta` y `SillonRespuesta` en `backend/src/api/esquemas.py` con soporte para mapeo desde modelos de dominio y validar serialización sin fugas de `tenant_id`.
- [x] 3.2 Implementar router `backend/src/api/routers/recursos.py` con los endpoints `GET /api/v1/profesionales` y `GET /api/v1/sillones` protegidos por autenticación JWT (`ContextoUsuario`), y registrarlo en `create_app()` de `backend/src/api/app.py`.
- [x] 3.3 Desarrollar pruebas funcionales e integrales para los endpoints de recursos: códigos 200 (éxito), 401 (sin token o token inválido), validación del query param `solo_activos` y prueba estricta de aislamiento multi-tenant.

## 4. Verificación integral y control de calidad

- [x] 4.1 Ejecutar la suite completa de pruebas de backend con pytest y coverage, verificando que todos los tests pasen (>= 155 tests base + nuevos tests de recursos) con cobertura >= 95% y 0 violaciones de pureza de dominio.

