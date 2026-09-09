-- ============================================================
-- veloX — Corregir RLS recursivo en users + permitir comprobantes
-- Ejecutar en Supabase → SQL Editor si persiste error 42P17
-- ============================================================

-- 1) Políticas seguras en users (sin subconsultas recursivas a users)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol record;
BEGIN
    FOR pol IN
        SELECT policyname
        FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'users'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.users', pol.policyname);
    END LOOP;
END $$;

-- Lectura: el usuario autenticado solo ve su fila por email del JWT
CREATE POLICY users_select_own
    ON public.users
    FOR SELECT
    TO authenticated
    USING (lower(email) = lower(coalesce(auth.jwt() ->> 'email', '')));

-- Master/service_role gestiona usuarios (PostgREST bypass con service_role)
CREATE POLICY users_service_all
    ON public.users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 2) Comprobantes: insertar sin consultar users (evita 42P17)
ALTER TABLE public.comprobantes ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol record;
BEGIN
    FOR pol IN
        SELECT policyname
        FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'comprobantes'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.comprobantes', pol.policyname);
    END LOOP;
END $$;

CREATE POLICY comprobantes_insert_authenticated
    ON public.comprobantes
    FOR INSERT
    TO authenticated
    WITH CHECK (
        lower(usuario_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
    );

CREATE POLICY comprobantes_select_own
    ON public.comprobantes
    FOR SELECT
    TO authenticated
    USING (
        lower(usuario_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
    );

CREATE POLICY comprobantes_service_all
    ON public.comprobantes
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
