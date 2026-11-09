-- Migración 004: formalización de pacientes y unicidad por tenant (C-07, RN-05, RN-06).

ALTER TABLE paciente ADD COLUMN telefono TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_paciente_tenant_dni ON paciente (tenant_id, dni);
