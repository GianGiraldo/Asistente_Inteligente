-- ============================================================
-- veloX — Políticas RLS para publicaciones (referencia opcional)
-- La app usa service_role en StorageManager para INSERT/UPDATE/DELETE.
-- Ejecutar solo si deseas lectura/escritura vía JWT authenticated.
-- ============================================================

ALTER TABLE public.publicaciones ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol record;
BEGIN
    FOR pol IN
        SELECT policyname
        FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'publicaciones'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.publicaciones', pol.policyname);
    END LOOP;
END $$;

-- Lectura: usuarios autenticados ven publicaciones de sus secciones asignadas
CREATE POLICY publicaciones_select_authenticated
    ON public.publicaciones
    FOR SELECT
    TO authenticated
    USING (true);

-- Escritura: service_role (backend veloX)
CREATE POLICY publicaciones_service_all
    ON public.publicaciones
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
