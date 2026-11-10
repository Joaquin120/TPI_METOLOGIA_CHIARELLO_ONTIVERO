-- Migración 005: bitácora de auditoría y trazabilidad operativa (C-09, RN-05, RN-06).

CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenant(id),
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    accion TEXT NOT NULL,
    entidad TEXT NOT NULL,
    entidad_id INTEGER,
    detalle TEXT,
    fecha_hora TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auditoria_tenant_fecha
    ON auditoria (tenant_id, fecha_hora);

CREATE INDEX IF NOT EXISTS idx_auditoria_tenant_entidad
    ON auditoria (tenant_id, entidad, entidad_id);
