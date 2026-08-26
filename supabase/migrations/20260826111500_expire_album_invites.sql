-- Limit the lifetime of bearer invitation links.
alter table public.album_profiles
add column if not exists invite_token_created_at timestamptz not null default now();

-- Invalidate links issued before expiry was enforced.
update public.album_profiles
set invite_token = gen_random_uuid(),
    invite_token_created_at = now();

create or replace function public.ensure_album_profile(
  p_display_name text,
  p_avatar_url text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  current_user_id text := auth.jwt() ->> 'sub';
  result uuid;
begin
  if current_user_id is null then
    raise exception 'Authentication required';
  end if;

  insert into album_profiles (user_id, display_name, avatar_url, updated_at)
  values (
    current_user_id,
    left(coalesce(nullif(trim(p_display_name), ''), 'Coleccionista'), 80),
    nullif(p_avatar_url, ''),
    now()
  )
  on conflict (user_id) do update set
    display_name = excluded.display_name,
    avatar_url = excluded.avatar_url,
    invite_token = case
      when album_profiles.invite_token_created_at < now() - interval '30 days'
        then gen_random_uuid()
      else album_profiles.invite_token
    end,
    invite_token_created_at = case
      when album_profiles.invite_token_created_at < now() - interval '30 days'
        then now()
      else album_profiles.invite_token_created_at
    end,
    updated_at = now()
  returning invite_token into result;

  return result;
end;
$$;

create or replace function public.get_album_invite(p_token uuid)
returns table(display_name text, avatar_url text)
language sql
security definer
set search_path = public
as $$
  select p.display_name, p.avatar_url
  from album_profiles p
  where p.invite_token = p_token
    and p.invite_token_created_at >= now() - interval '30 days';
$$;

create or replace function public.accept_album_invite(p_token uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  current_user_id text := auth.jwt() ->> 'sub';
  friend_id text;
begin
  if current_user_id is null then
    raise exception 'Authentication required';
  end if;

  select user_id into friend_id
  from album_profiles
  where invite_token = p_token
    and invite_token_created_at >= now() - interval '30 days';

  if friend_id is null then raise exception 'Invitation not found or expired'; end if;
  if friend_id = current_user_id then raise exception 'You cannot add yourself'; end if;

  insert into album_friendships (user_a, user_b)
  values (least(current_user_id, friend_id), greatest(current_user_id, friend_id))
  on conflict do nothing;

  return friend_id;
end;
$$;
