-- ============================================================
-- Esquema de pagos veloX — tabla comprobantes + columnas users
-- Ejecutar en Supabase SQL Editor
-- ============================================================

-- Acceso en tabla users (sin metodo_pago en comprobantes Yape)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS pago_confirmado BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS perfil JSONB DEFAULT '{}'::jsonb;

-- Tabla independiente de comprobantes / transacciones Yape·Plim
CREATE TABLE IF NOT EXISTS comprobantes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_email TEXT NOT NULL,
    celular TEXT,
    metodo_pago TEXT NOT NULL DEFAULT 'yape_plim',
    archivo_url TEXT,
    archivo_ruta TEXT,
    monto NUMERIC(10, 2) DEFAULT 9.90,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    motivo_rechazo TEXT,
    revisado_por TEXT,
    creado TIMESTAMPTZ DEFAULT NOW(),
    fecha_revision TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_comprobantes_email_estado
    ON comprobantes (usuario_email, estado);

CREATE INDEX IF NOT EXISTS idx_comprobantes_estado
    ON comprobantes (estado);

-- Si la tabla ya existía con columnas incompletas, añade las faltantes:
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS usuario_email TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS celular TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS metodo_pago TEXT DEFAULT 'yape_plim';
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS archivo_url TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS archivo_ruta TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS monto NUMERIC(10, 2) DEFAULT 9.90;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS estado TEXT DEFAULT 'pendiente';
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS motivo_rechazo TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS revisado_por TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS creado TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS fecha_revision TIMESTAMPTZ;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS plan_seleccionado TEXT;
ALTER TABLE comprobantes ADD COLUMN IF NOT EXISTS cursos_solicitados JSONB DEFAULT '[]'::jsonb;

-- Master y usuarios activos conservan acceso
UPDATE users
SET pago_confirmado = true
WHERE activo = true
  AND rol IN ('usuario', 'master');

UPDATE users
SET pago_confirmado = true, activo = true
WHERE rol = 'master';

-- Master principal veloX (ejecutar una vez al migrar administración)
UPDATE users
SET rol = 'master', activo = true, pago_confirmado = true
WHERE email = 'gianpiergiraldo@gmail.com';

-- permisos_admin (JSON dentro de users.perfil) ejemplo:
-- {"modulos": ["🏠 Inicio", "📁 Mis Documentos"], "secciones": ["excel", "word"], "puede_publicar": true}

UPDATE users
SET rol = 'usuario'
WHERE email = 'master@optimizo.com';
