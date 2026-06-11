-- ============================================================
-- Esquema de pagos y control de acceso — ejecutar en Supabase SQL Editor
-- ============================================================

-- 1) Campos de control en users
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS pago_confirmado BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS metodo_pago TEXT,
    ADD COLUMN IF NOT EXISTS codigo_operacion TEXT;

-- Usuarios ya activos antes de la migración conservan acceso
UPDATE users
SET pago_confirmado = true
WHERE activo = true
  AND rol IN ('usuario', 'master');

-- Master siempre con acceso confirmado
UPDATE users
SET pago_confirmado = true, activo = true
WHERE rol = 'master';

-- 2) Tabla de pagos manuales Yape / Plim
CREATE TABLE IF NOT EXISTS pagos_pendientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    celular TEXT NOT NULL,
    codigo_operacion TEXT NOT NULL,
    monto NUMERIC(10, 2) NOT NULL DEFAULT 9.90,
    fecha TIMESTAMPTZ NOT NULL DEFAULT now(),
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    motivo_rechazo TEXT,
    revisado_por TEXT,
    fecha_revision TIMESTAMPTZ,
    nombre TEXT,
    metodo_pago TEXT NOT NULL DEFAULT 'yape',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Evita duplicar códigos de operación (incluye aprobados/rechazados)
CREATE UNIQUE INDEX IF NOT EXISTS idx_pagos_codigo_operacion_unico
    ON pagos_pendientes (codigo_operacion);

CREATE INDEX IF NOT EXISTS idx_pagos_pendientes_estado
    ON pagos_pendientes (estado);

CREATE INDEX IF NOT EXISTS idx_pagos_pendientes_email
    ON pagos_pendientes (email);

-- 3) RLS (ajusta según tu política; service role bypass)
-- ALTER TABLE pagos_pendientes ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE pagos_pendientes IS 'Solicitudes de pago manual Yape/Plim pendientes de revisión por Master';
