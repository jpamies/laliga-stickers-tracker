-- Guarda el identificador de LALIGA con el que se piden las estadísticas.
--
-- `slug` es lo que necesita `players/<slug>/stats`, así que sin él no se puede
-- relacionar una ficha con sus minutos jugados.

alter table public.laliga_plantilla
  add column if not exists slug text;

comment on column public.laliga_plantilla.slug is
  'Identificador del jugador en laliga.com, usado para pedir sus estadísticas.';

create index if not exists laliga_plantilla_slug_idx
  on public.laliga_plantilla (slug);
