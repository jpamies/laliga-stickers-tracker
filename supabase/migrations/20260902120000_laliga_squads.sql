-- Plantillas reales de LALIGA EA SPORTS.
--
-- Tablas de sólo lectura pobladas por `generar_plantillas_laliga.py`, que
-- regenera `supabase/laliga_plantillas.sql` con un `delete` + `insert`
-- completo. No guardan datos personales del usuario: son el catálogo público
-- que publica laliga.com, así que cualquiera puede leerlas y sólo el rol de
-- servicio puede escribirlas.

create table if not exists public.laliga_equipo (
  slug text primary key,
  team_id integer not null,
  nombre text not null,
  nombre_corto text,
  abreviatura text,
  seccion_album text,
  color text,
  color_secundario text,
  escudo_url text,
  estadio text,
  temporada integer not null
);

create table if not exists public.laliga_plantilla (
  squad_id integer primary key,
  team_slug text not null references public.laliga_equipo (slug) on delete cascade,
  seccion_album text,
  equipo text,
  dorsal integer,
  posicion text,
  posicion_slug text,
  rol text,
  rol_slug text,
  nombre text not null,
  apodo text,
  nombre_pila text,
  apellidos text,
  fecha_nacimiento date,
  lugar_nacimiento text,
  pais text,
  altura_cm integer,
  peso_kg integer,
  internacional boolean not null default false,
  activo boolean not null default true,
  cedido boolean not null default false,
  cedido_fuera boolean not null default false,
  foto_url text,
  foto_grande_url text,
  foto_cuadrada_url text,
  person_id integer,
  opta_id text,
  temporada integer not null
);

create index if not exists laliga_plantilla_team_idx
  on public.laliga_plantilla (team_slug);
create index if not exists laliga_plantilla_seccion_idx
  on public.laliga_plantilla (seccion_album);

alter table public.laliga_equipo enable row level security;
alter table public.laliga_plantilla enable row level security;

drop policy if exists "Anyone can read laliga teams" on public.laliga_equipo;
create policy "Anyone can read laliga teams"
on public.laliga_equipo
for select
to anon, authenticated
using (true);

drop policy if exists "Anyone can read laliga squads" on public.laliga_plantilla;
create policy "Anyone can read laliga squads"
on public.laliga_plantilla
for select
to anon, authenticated
using (true);
