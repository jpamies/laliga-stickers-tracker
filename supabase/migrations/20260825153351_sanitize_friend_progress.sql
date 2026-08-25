create or replace function public.get_album_friends()
returns table(user_id text, display_name text, avatar_url text, progress jsonb)
language sql
security definer
set search_path = public
as $$
  with mine as (
    select auth.jwt() ->> 'sub' as id
  ),
  friend_ids as (
    select case when f.user_a = mine.id then f.user_b else f.user_a end as id
    from album_friendships f, mine
    where mine.id in (f.user_a, f.user_b)
  ),
  sanitized as (
    select
      s.user_id,
      coalesce(
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
      ) as progress
    from album_social_progress s
    left join lateral jsonb_each(s.progress) item on true
    group by s.user_id
  )
  select p.user_id, p.display_name, p.avatar_url, coalesce(s.progress, '{}'::jsonb)
  from friend_ids f
  join album_profiles p on p.user_id = f.id
  left join sanitized s on s.user_id = f.id
  order by lower(p.display_name);
$$;

revoke execute on function public.get_album_friends() from public, anon;
grant execute on function public.get_album_friends() to authenticated;