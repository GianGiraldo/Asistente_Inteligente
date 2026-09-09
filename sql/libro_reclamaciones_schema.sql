-- Tabla Libro de Reclamaciones Virtual (Ley N° 29571)
-- Ejecutar en Supabase SQL Editor si la tabla aún no existe.

create table if not exists public.libro_reclamaciones (
    id bigint generated always as identity primary key,
    codigo_seguimiento text not null unique,
    nombres_apellidos text not null,
    documento_identidad text not null,
    correo text not null,
    telefono text not null,
    tipo_bien text not null check (tipo_bien in ('Producto', 'Servicio')),
    tipo text not null check (tipo in ('Reclamo', 'Queja')),
    detalle text not null,
    pedido text not null,
    creado_en timestamptz not null default now()
);

create index if not exists idx_libro_reclamaciones_correo
    on public.libro_reclamaciones (correo);

create index if not exists idx_libro_reclamaciones_codigo
    on public.libro_reclamaciones (codigo_seguimiento);

alter table public.libro_reclamaciones enable row level security;

-- La app inserta con service_role (get_supabase_admin) tras validar el formulario.
drop policy if exists "libro_reclamaciones_insert_anon" on public.libro_reclamaciones;
drop policy if exists "libro_reclamaciones_insert_service" on public.libro_reclamaciones;

create policy "libro_reclamaciones_insert_service"
    on public.libro_reclamaciones
    for insert
    to service_role
    with check (true);

create policy "libro_reclamaciones_select_service"
    on public.libro_reclamaciones
    for select
    to service_role
    using (true);
