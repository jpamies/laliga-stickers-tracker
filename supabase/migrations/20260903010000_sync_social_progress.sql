-- Deriva la copia social del progreso en la propia base de datos.
--
-- `album_social_progress` es lo que ven los amigos y hasta ahora la mantenía
-- el navegador, escribiéndola a la vez que `album_progress`. Cualquier cambio
-- que no pasara por el cliente —reiniciar el álbum desde el panel de Supabase,
-- por ejemplo— dejaba la copia obsoleta y los amigos seguían viendo cromos que
-- su dueño ya no tiene.
--
-- Ahora la copia se recalcula con un disparador, así que no puede divergir.

-- Sólo se comparte posesión y número de copias: la decisión personal de pegar
-- o no pegar, y las marcas de tiempo, se quedan en `album_progress`.
create or replace function public.album_social_snapshot(p_progress jsonb)
returns jsonb
language sql
immutable
set search_path = public
as $$
  select coalesce(
    jsonb_object_agg(
      item.key,
      jsonb_build_object(
        'state', 'owned',
        'copies', greatest(
          1,
          least(99, coalesce((item.value ->> 'copies')::integer, 1))
        )
      )
    ) filter (where item.value ->> 'state' = 'owned'),
    '{}'::jsonb
  )
  from jsonb_each(coalesce(p_progress, '{}'::jsonb)) item;
$$;

create or replace function public.sync_album_social_progress()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'DELETE' then
    delete from public.album_social_progress where user_id = old.user_id;
    return old;
  end if;

  insert into public.album_social_progress (user_id, progress, updated_at)
  values (
    new.user_id,
    public.album_social_snapshot(new.progress),
    coalesce(new.updated_at, now())
  )
  on conflict (user_id) do update
    set progress = excluded.progress,
        updated_at = excluded.updated_at;
  return new;
end;
$$;

drop trigger if exists album_progress_social_sync on public.album_progress;
create trigger album_progress_social_sync
after insert or update or delete on public.album_progress
for each row execute function public.sync_album_social_progress();

revoke execute on function public.album_social_snapshot(jsonb) from public, anon;
revoke execute on function public.sync_album_social_progress() from public, anon;

-- Repara las copias que ya estaban desincronizadas.
insert into public.album_social_progress (user_id, progress, updated_at)
select p.user_id, public.album_social_snapshot(p.progress), p.updated_at
from public.album_progress p
on conflict (user_id) do update
  set progress = excluded.progress,
      updated_at = excluded.updated_at;

-- Y borra las de álbumes que ya no existen.
delete from public.album_social_progress s
where not exists (
  select 1 from public.album_progress p where p.user_id = s.user_id
);
