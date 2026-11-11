-- Migración 008: tabla de lista de espera ante vacantes o sobreturnos (C-15, F-08, PA-14).

CREATE TABLE IF NOT EXISTS lista_espera (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    paciente_nombre TEXT NOT NULL,
    paciente_telefono TEXT NOT NULL,
    fecha_deseada TEXT NOT NULL,
    motivo TEXT NOT NULL,
    profesional_nombre TEXT,
    franja_horaria TEXT,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
    creado_en TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lista_espera_tenant_estado_fecha
    ON lista_espera (tenant_id, estado, fecha_deseada);

