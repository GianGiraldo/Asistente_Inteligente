-- Puente de contraseña veloX (opcional, no modifica filas existentes)
-- Permite NULL en password para cuentas OAuth hasta que el usuario configure su clave.
-- Ejecutar solo si las columnas password/password_salt son NOT NULL hoy.

ALTER TABLE users ALTER COLUMN password DROP NOT NULL;
ALTER TABLE users ALTER COLUMN password_salt DROP NOT NULL;

-- No ejecutar UPDATE masivo sobre usuarios existentes.
-- La app marca perfil.velox_password_configured = true al configurar la contraseña.
