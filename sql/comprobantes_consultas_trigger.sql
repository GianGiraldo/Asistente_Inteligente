-- ============================================================
-- veloX — Trigger defensivo: comprobantes → consultas
-- Ejecutar en Supabase SQL Editor (Query Editor)
-- Garantiza notificación al alumno aunque falle el INSERT en Python.
-- ============================================================

-- Columnas recomendadas en consultas (idempotente)
ALTER TABLE public.consultas
    ADD COLUMN IF NOT EXISTS asunto TEXT,
    ADD COLUMN IF NOT EXISTS seccion TEXT,
    ADD COLUMN IF NOT EXISTS leido BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS leido_master BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS respondido BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS comprobante_id UUID,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS fecha TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fecha_respuesta TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS usuario_email TEXT,
    ADD COLUMN IF NOT EXISTS respondido_por TEXT,
    ADD COLUMN IF NOT EXISTS nombre_usuario TEXT,
    ADD COLUMN IF NOT EXISTS estado TEXT;

CREATE INDEX IF NOT EXISTS idx_consultas_email_leido
    ON public.consultas (email, leido);

CREATE INDEX IF NOT EXISTS idx_consultas_comprobante_id
    ON public.consultas (comprobante_id)
    WHERE comprobante_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_consultas_comprobante_id_unique
    ON public.consultas (comprobante_id)
    WHERE comprobante_id IS NOT NULL;

-- Función: INSERT en consultas al aprobar/rechazar comprobante
CREATE OR REPLACE FUNCTION public.fn_comprobante_notificar_consulta()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_estado TEXT;
    v_respuesta TEXT;
BEGIN
    v_estado := LOWER(COALESCE(NEW.estado, ''));

    -- Solo cuando el estado cambia a aprobado o rechazado
    IF TG_OP = 'UPDATE'
       AND v_estado IN ('aprobado', 'rechazado')
       AND LOWER(COALESCE(OLD.estado, '')) IS DISTINCT FROM v_estado THEN

        -- Evitar duplicados (Python + trigger)
        IF NEW.id IS NOT NULL AND EXISTS (
            SELECT 1 FROM public.consultas c WHERE c.comprobante_id = NEW.id
        ) THEN
            RETURN NEW;
        END IF;

        v_respuesta := COALESCE(
            NULLIF(TRIM(NEW.motivo_rechazo), ''),
            'Tu pago ha sido verificado y aprobado con éxito.'
        );

        INSERT INTO public.consultas (
            id,
            email,
            usuario_email,
            asunto,
            mensaje,
            respuesta,
            seccion,
            respondido,
            leido,
            leido_master,
            estado,
            comprobante_id,
            fecha,
            created_at,
            fecha_respuesta,
            respondido_por,
            nombre_usuario
        ) VALUES (
            gen_random_uuid(),
            LOWER(TRIM(NEW.usuario_email)),
            LOWER(TRIM(NEW.usuario_email)),
            'Estado de Solicitud: ' || UPPER(v_estado),
            'Revisión de comprobante de pago para el plan/curso seleccionado.',
            v_respuesta,
            'cobranzas',
            true,
            false,
            true,
            CASE WHEN v_estado = 'aprobado' THEN 'Atendido' ELSE 'Observado' END,
            NEW.id,
            COALESCE(NEW.fecha_revision, NOW()),
            NOW(),
            COALESCE(NEW.fecha_revision, NOW()),
            NEW.revisado_por,
            SPLIT_PART(LOWER(TRIM(NEW.usuario_email)), '@', 1)
        );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_comprobante_notificar_consulta ON public.comprobantes;

CREATE TRIGGER trg_comprobante_notificar_consulta
    AFTER UPDATE OF estado, motivo_rechazo ON public.comprobantes
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_comprobante_notificar_consulta();

-- Verificación rápida (opcional):
-- UPDATE comprobantes SET estado = 'rechazado', motivo_rechazo = 'Prueba trigger'
-- WHERE id = '<uuid-pendiente>';
