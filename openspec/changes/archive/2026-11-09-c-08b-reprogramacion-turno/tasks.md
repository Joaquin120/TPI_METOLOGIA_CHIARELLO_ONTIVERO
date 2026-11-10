# Tasks

## 1. Dominio y Reglas de Negocio de Reprogramación

- [x] 1.1 Extender `PuertoTurnos` en `backend/src/domain/puertos.py` añadiendo el parámetro opcional `excluir_turno_id: int | None = None` en `buscar_activos_solapables` y declarando el método `actualizar_reprogramacion(turno: Turno) -> Turno`.
- [x] 1.2 Implementar en `ServicioTurnos` (`backend/src/domain/services.py`) el método `reprogramar(turno_id, nueva_fecha, nueva_hora_inicio, nueva_hora_fin, nuevo_profesional=None, nuevo_sillon=None)` validando que el turno esté en estado activo (`PENDIENTE` o `CONFIRMADO`), rechazando estados terminales con `TransicionInvalidaError`, ejecutando la doble validación simultánea e independiente (`RN-01`, `RN-02`, `RN-09`) y excluyendo el turno actual del chequeo de solapamiento.
- [x] 1.3 Implementar pruebas unitarias de dominio en `backend/tests/test_reprogramacion_dominio.py` verificando: reprogramación exitosa, liberación del horario previo, rechazo ante profesional o sillón ocupado con precedencia RN-09, rechazo de turnos cancelados o completados, y desplazamiento parcial en la misma franja sin auto-solapamiento.

## 2. Persistencia en SQLite y Repositorios

- [x] 2.1 Actualizar `RepositorioTurnosSqlite` en `backend/src/repositories/turnos_sqlite.py` incorporando el filtrado por `excluir_turno_id` en `buscar_activos_solapables` e implementando `actualizar_reprogramacion(turno: Turno) -> Turno` para persistir los nuevos valores de `fecha_hora_inicio`, `fecha_hora_fin`, `profesional_id` y `sillon_id` de forma atómica dentro del tenant.
- [x] 2.2 Implementar pruebas de persistencia en `backend/tests/test_persistencia_reprogramacion.py` comprobando sobre SQLite real que la reprogramación persiste los cambios, libera inmediatamente los recursos anteriores y mantiene el aislamiento inter-tenant estricto.

## 3. Capa API REST, Esquemas y Control RBAC

- [x] 3.1 Definir el esquema Pydantic `ReprogramarTurnoPeticion` en `backend/src/api/esquemas.py` con validaciones de formato de fecha, horas y consistencia cronológica (`hora_inicio < hora_fin`).
- [x] 3.2 Implementar el endpoint `PATCH /api/v1/turnos/{id}/reprogramar` en `backend/src/api/routers/turnos.py`, restringiendo el acceso mediante RBAC a roles `Recepcionista` y `Administrador` (denegando rol `Profesional` con 403 `ACCESO_DENEGADO`), resolviendo el tenant desde `ContextoUsuario` y devolviendo 404 ante turnos inexistentes o de otra clínica.
- [x] 3.3 Integrar el registro del evento `REPROGRAMAR_TURNO` en la bitácora de auditoría (C-09) dentro del controlador para garantizar trazabilidad inmutable y no repudio.

## 4. Pruebas de Integración y Verificación Global

- [x] 4.1 Implementar la suite `backend/tests/test_api_reprogramacion.py` con datos sintéticos (RN-06), cubriendo exhaustivamente todos los escenarios de spec: éxito (200), solapamientos (409 `SOLAPAMIENTO_PROFESIONAL` / `SOLAPAMIENTO_SILLON`), estado terminal (409 `TRANSICION_INVALIDA`), errores de autenticación y roles (401 / 403), turno no encontrado (404), validación temporal (422) y envelope uniforme.
- [x] 4.2 Ejecutar la suite completa con `python3.12 -m pytest backend/tests` y verificar 100% de tests passing con cobertura >= 97% y pureza de dominio intacta (`test_pureza_dominio.py`).
