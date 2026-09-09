-- Añade a las plantillas el cromo del álbum que representa a cada ficha.
--
-- Estas columnas se escribieron por error dentro de
-- `20260902120000_laliga_squads.sql` después de que esa migración ya se
-- hubiera aplicado, así que las bases de datos existentes nunca las
-- recibieron: una migración aplicada es inmutable. Esta las añade aparte.
--
-- Es idempotente, de modo que también es inofensiva en una base creada desde
-- cero con la versión corregida de aquella migración.

alter table public.laliga_plantilla
  add column if not exists cromo_id text,
  add column if not exists cromo_seccion text,
  add column if not exists cromo_numero text,
  add column if not exists cromo_nombre text,
  add column if not exists cromos text;

comment on column public.laliga_plantilla.cromo_id is
  'Cromo del álbum Panini que representa a esta ficha. Sólo se cruzan las secciones de equipo y Últimos Fichajes.';

create index if not exists laliga_plantilla_cromo_idx
  on public.laliga_plantilla (cromo_id);
