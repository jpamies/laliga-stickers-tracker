-- Social sharing, friendships, and trade proposals.
create table if not exists public.album_profiles (
  user_id text primary key default (auth.jwt() ->> 'sub'),
  display_name text not null,
  avatar_url text,
  invite_token uuid not null unique default gen_random_uuid(),
  updated_at timestamptz not null default now()
);

create table if not exists public.album_social_progress (
  user_id text primary key default (auth.jwt() ->> 'sub'),
  progress jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint album_social_progress_is_object check (jsonb_typeof(progress) = 'object')
);

create table if not exists public.album_shares (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  owner_name text not null,
  snapshot jsonb not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  constraint album_share_snapshot_is_object check (jsonb_typeof(snapshot) = 'object')
);

create table if not exists public.album_friendships (
  user_a text not null,
  user_b text not null,
  created_at timestamptz not null default now(),
  primary key (user_a, user_b),
  constraint album_friendship_order check (user_a < user_b)
);

create table if not exists public.album_trade_proposals (
  id uuid primary key default gen_random_uuid(),
  proposer_id text not null,
  recipient_id text not null,
  offered jsonb not null default '[]'::jsonb,
  requested jsonb not null default '[]'::jsonb,
  message text not null default '',
  status text not null default 'pending'
    check (status in ('pending', 'accepted', 'rejected', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint album_trade_offered_is_array check (jsonb_typeof(offered) = 'array'),
  constraint album_trade_requested_is_array check (jsonb_typeof(requested) = 'array'),
  constraint album_trade_has_items check (
    jsonb_array_length(offered) > 0 and jsonb_array_length(requested) > 0
  )
);

alter table public.album_profiles enable row level security;
alter table public.album_social_progress enable row level security;
alter table public.album_shares enable row level security;
alter table public.album_friendships enable row level security;
alter table public.album_trade_proposals enable row level security;

create policy "Users manage their own album profile"
on public.album_profiles for all to authenticated
using ((select auth.jwt() ->> 'sub') = user_id)
with check ((select auth.jwt() ->> 'sub') = user_id);

create policy "Users manage their own social progress"
on public.album_social_progress for all to authenticated
using ((select auth.jwt() ->> 'sub') = user_id)
with check ((select auth.jwt() ->> 'sub') = user_id);

create policy "Users manage their own album shares"
on public.album_shares for all to authenticated
using ((select auth.jwt() ->> 'sub') = owner_id)
with check ((select auth.jwt() ->> 'sub') = owner_id);

create policy "Friends can view their friendship"
on public.album_friendships for select to authenticated
using ((select auth.jwt() ->> 'sub') in (user_a, user_b));

create policy "Trade participants can view proposals"
on public.album_trade_proposals for select to authenticated
using ((select auth.jwt() ->> 'sub') in (proposer_id, recipient_id));

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
  where p.invite_token = p_token;
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
  select user_id into friend_id from album_profiles where invite_token = p_token;
  if friend_id is null then raise exception 'Invitation not found'; end if;
  if friend_id = current_user_id then raise exception 'You cannot add yourself'; end if;
  insert into album_friendships (user_a, user_b)
  values (least(current_user_id, friend_id), greatest(current_user_id, friend_id))
  on conflict do nothing;
  return friend_id;
end;
$$;

create or replace function public.get_album_friends()
returns table(user_id text, display_name text, avatar_url text, progress jsonb)
language sql
security definer
set search_path = public
as $$
  with mine as (select auth.jwt() ->> 'sub' as id),
  friend_ids as (
    select case when f.user_a = mine.id then f.user_b else f.user_a end as id
    from album_friendships f, mine
    where mine.id in (f.user_a, f.user_b)
  )
  select p.user_id, p.display_name, p.avatar_url, coalesce(s.progress, '{}'::jsonb)
  from friend_ids f
  join album_profiles p on p.user_id = f.id
  left join album_social_progress s on s.user_id = f.id
  order by lower(p.display_name);
$$;

create or replace function public.remove_album_friend(p_friend_id text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare current_user_id text := auth.jwt() ->> 'sub';
begin
  delete from album_friendships
  where user_a = least(current_user_id, p_friend_id)
    and user_b = greatest(current_user_id, p_friend_id);
end;
$$;

create or replace function public.create_album_share(p_snapshot jsonb)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  current_user_id text := auth.jwt() ->> 'sub';
  result uuid;
begin
  if current_user_id is null then raise exception 'Authentication required'; end if;
  if jsonb_typeof(p_snapshot) <> 'object' then raise exception 'Invalid snapshot'; end if;
  insert into album_shares (owner_id, owner_name, snapshot)
  select current_user_id, display_name, p_snapshot
  from album_profiles where user_id = current_user_id
  returning id into result;
  if result is null then raise exception 'Profile required'; end if;
  return result;
end;
$$;

create or replace function public.list_album_shares()
returns table(id uuid, created_at timestamptz)
language sql
security definer
set search_path = public
as $$
  select s.id, s.created_at
  from album_shares s
  where s.owner_id = (auth.jwt() ->> 'sub') and s.revoked_at is null
  order by s.created_at desc;
$$;

create or replace function public.revoke_album_share(p_id uuid)
returns void
language sql
security definer
set search_path = public
as $$
  update album_shares set revoked_at = now()
  where id = p_id and owner_id = (auth.jwt() ->> 'sub');
$$;

create or replace function public.get_shared_album(p_id uuid)
returns table(owner_name text, snapshot jsonb, created_at timestamptz)
language sql
security definer
set search_path = public
as $$
  select s.owner_name, s.snapshot, s.created_at
  from album_shares s
  where s.id = p_id and s.revoked_at is null;
$$;

create or replace function public.create_album_trade(
  p_recipient_id text,
  p_offered jsonb,
  p_requested jsonb,
  p_message text default ''
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
  if jsonb_typeof(p_offered) <> 'array' or jsonb_array_length(p_offered) = 0
    or jsonb_typeof(p_requested) <> 'array' or jsonb_array_length(p_requested) = 0
  then raise exception 'Both sides need stickers'; end if;
  if not exists (
    select 1 from album_friendships
    where user_a = least(current_user_id, p_recipient_id)
      and user_b = greatest(current_user_id, p_recipient_id)
  ) then raise exception 'Friendship required'; end if;
  insert into album_trade_proposals (
    proposer_id, recipient_id, offered, requested, message
  ) values (
    current_user_id, p_recipient_id, p_offered, p_requested,
    left(coalesce(p_message, ''), 500)
  ) returning id into result;
  return result;
end;
$$;

create or replace function public.list_album_trades()
returns table(
  id uuid,
  proposer_id text,
  proposer_name text,
  recipient_id text,
  recipient_name text,
  offered jsonb,
  requested jsonb,
  message text,
  status text,
  created_at timestamptz
)
language sql
security definer
set search_path = public
as $$
  select t.id, t.proposer_id, pp.display_name, t.recipient_id, rp.display_name,
         t.offered, t.requested, t.message, t.status, t.created_at
  from album_trade_proposals t
  join album_profiles pp on pp.user_id = t.proposer_id
  join album_profiles rp on rp.user_id = t.recipient_id
  where (auth.jwt() ->> 'sub') in (t.proposer_id, t.recipient_id)
  order by t.created_at desc;
$$;

create or replace function public.respond_album_trade(p_id uuid, p_status text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  current_user_id text := auth.jwt() ->> 'sub';
begin
  if p_status in ('accepted', 'rejected') then
    update album_trade_proposals
    set status = p_status, updated_at = now()
    where id = p_id and recipient_id = current_user_id and status = 'pending';
  elsif p_status = 'cancelled' then
    update album_trade_proposals
    set status = p_status, updated_at = now()
    where id = p_id and proposer_id = current_user_id and status = 'pending';
  else
    raise exception 'Invalid status';
  end if;
end;
$$;

grant execute on function public.get_album_invite(uuid) to anon, authenticated;
grant execute on function public.get_shared_album(uuid) to anon, authenticated;
grant execute on function public.ensure_album_profile(text, text) to authenticated;
grant execute on function public.accept_album_invite(uuid) to authenticated;
grant execute on function public.get_album_friends() to authenticated;
grant execute on function public.remove_album_friend(text) to authenticated;
grant execute on function public.create_album_share(jsonb) to authenticated;
grant execute on function public.list_album_shares() to authenticated;
grant execute on function public.revoke_album_share(uuid) to authenticated;
grant execute on function public.create_album_trade(text, jsonb, jsonb, text) to authenticated;
grant execute on function public.list_album_trades() to authenticated;
grant execute on function public.respond_album_trade(uuid, text) to authenticated;
