-- Migración 002: autenticación, usuarios y roles (C-04, DP-04, RN-05, RN-06).

CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL REFERENCES tenant(id),
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('Administrador', 'Recepcionista', 'Profesional')),
    profesional_id INTEGER REFERENCES profesional(id),
    activo INTEGER NOT NULL DEFAULT 1,
    UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_usuario_tenant_email
    ON usuario (tenant_id, email);

