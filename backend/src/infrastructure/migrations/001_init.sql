-- Migración 001: esquema inicial de persistencia (design D4, D-04).
--
-- Identificadores y timestamps PROVISORIOS (DP-06, aprobado 2026-11-03):
--   INTEGER PRIMARY KEY AUTOINCREMENT + fechas ISO-8601 en TEXT.
-- Sin columnas de auditoría ni borrado lógico: cancelar conserva la fila
-- (= historial, RN-04). Sin usuario_id (pendiente DP-04 / DP-06).
-- Sin datos reales: la semilla usa exclusivamente nombres sintéticos (RN-06).

CREATE TABLE IF NOT EXISTS tenant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS profesional (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenant(id),
    nombre TEXT NOT NULL,
    UNIQUE (tenant_id, nombre)
);

CREATE TABLE IF NOT EXISTS sillon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenant(id),
    nombre TEXT NOT NULL,
    UNIQUE (tenant_id, nombre)
);

CREATE TABLE IF NOT EXISTS paciente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenant(id),
    nombre TEXT NOT NULL,
    dni TEXT, -- nullable: alta de pacientes pendiente (PA-05)
    UNIQUE (tenant_id, nombre)
);

CREATE TABLE IF NOT EXISTS turno (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenant(id),
    paciente_id INTEGER NOT NULL REFERENCES paciente(id),
    profesional_id INTEGER NOT NULL REFERENCES profesional(id),
    sillon_id INTEGER NOT NULL REFERENCES sillon(id),
    -- ISO-8601 'YYYY-MM-DD HH:MM': la comparación lexicográfica de SQLite
    -- coincide con la cronológica (intervalo semiabierto [inicio, fin), D-07).
    fecha_hora_inicio TEXT NOT NULL,
    fecha_hora_fin TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (
        estado IN ('PENDIENTE', 'CONFIRMADO', 'CANCELADO', 'COMPLETADO')
    )
);

CREATE INDEX IF NOT EXISTS idx_turno_tenant_inicio
    ON turno (tenant_id, fecha_hora_inicio);
