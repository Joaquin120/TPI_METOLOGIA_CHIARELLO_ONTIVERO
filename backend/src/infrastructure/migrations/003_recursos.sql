-- Migración 003: atributos operativos de profesionales y sillones (C-06, F-04, F-05, PA-01).

ALTER TABLE profesional ADD COLUMN matricula TEXT;
ALTER TABLE profesional ADD COLUMN especialidad TEXT;
ALTER TABLE profesional ADD COLUMN activo INTEGER NOT NULL DEFAULT 1;

ALTER TABLE sillon ADD COLUMN equipamiento TEXT;
ALTER TABLE sillon ADD COLUMN activo INTEGER NOT NULL DEFAULT 1;

