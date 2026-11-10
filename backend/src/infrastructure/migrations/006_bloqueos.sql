-- Migración 006: tabla de bloqueos de sillones por mantenimiento (C-10, F-12, RN-07, RP-07).

CREATE TABLE IF NOT EXISTS bloqueo_sillon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    sillon_id INTEGER NOT NULL,
    fecha_hora_inicio TEXT NOT NULL,
    fecha_hora_fin TEXT NOT NULL,
    motivo TEXT NOT NULL,
    creado_por INTEGER,
    creado_en TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE CASCADE,
    FOREIGN KEY (sillon_id) REFERENCES sillon(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuario(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_bloqueo_sillon_tenant_intervalo
    ON bloqueo_sillon (tenant_id, sillon_id, fecha_hora_inicio, fecha_hora_fin);
