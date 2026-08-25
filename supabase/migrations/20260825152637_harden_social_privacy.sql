revoke execute on function public.ensure_album_profile(text, text) from public, anon;
revoke execute on function public.accept_album_invite(uuid) from public, anon;
revoke execute on function public.get_album_friends() from public, anon;
revoke execute on function public.remove_album_friend(text) from public, anon;
revoke execute on function public.create_album_share(jsonb) from public, anon;
revoke execute on function public.list_album_shares() from public, anon;
revoke execute on function public.revoke_album_share(uuid) from public, anon;
revoke execute on function public.create_album_trade(text, jsonb, jsonb, text) from public, anon;
revoke execute on function public.list_album_trades() from public, anon;
revoke execute on function public.respond_album_trade(uuid, text) from public, anon;
revoke execute on function public.get_album_invite(uuid) from public;
revoke execute on function public.get_shared_album(uuid) from public;

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

create or replace function public.create_album_share(p_snapshot jsonb)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  current_user_id text := auth.jwt() ->> 'sub';
  result uuid;
  clean_snapshot jsonb;
begin
  if current_user_id is null then raise exception 'Authentication required'; end if;
  if jsonb_typeof(p_snapshot) <> 'object' then raise exception 'Invalid snapshot'; end if;

  select coalesce(
    jsonb_object_agg(
      item.key,
      jsonb_build_object(
        'state', 'owned',
        'copies', greatest(1, least(99, coalesce((item.value ->> 'copies')::integer, 1)))
      )
    ),
    '{}'::jsonb
  )
  into clean_snapshot
  from jsonb_each(p_snapshot) item
  where item.value ->> 'state' = 'owned';

  insert into album_shares (owner_id, owner_name, snapshot)
  select current_user_id, display_name, clean_snapshot
  from album_profiles where user_id = current_user_id
  returning id into result;
  if result is null then raise exception 'Profile required'; end if;
  return result;
end;
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
  proposer_progress jsonb;
  recipient_progress jsonb;
  result uuid;
begin
  if current_user_id is null then raise exception 'Authentication required'; end if;
  if jsonb_typeof(p_offered) <> 'array' or jsonb_array_length(p_offered) = 0
    or jsonb_typeof(p_requested) <> 'array' or jsonb_array_length(p_requested) = 0
  then raise exception 'Both sides need stickers'; end if;
  if not exists (
    select 1 from album_friendships
    where user_a = least(current_user_id, p_recipient_id)
      and user_b = greatest(current_user_id, p_recipient_id)
  ) then raise exception 'Friendship required'; end if;

  select progress into proposer_progress
  from album_social_progress where user_id = current_user_id;
  select progress into recipient_progress
  from album_social_progress where user_id = p_recipient_id;

  if exists (
    select 1 from jsonb_array_elements(p_offered) item
    where coalesce((proposer_progress -> (item ->> 'id') ->> 'copies')::integer, 0) < 2
  ) then raise exception 'Offered sticker is not a duplicate'; end if;
  if exists (
    select 1 from jsonb_array_elements(p_requested) item
    where coalesce((recipient_progress -> (item ->> 'id') ->> 'copies')::integer, 0) < 2
  ) then raise exception 'Requested sticker is not a duplicate'; end if;

  insert into album_trade_proposals (
    proposer_id, recipient_id, offered, requested, message
  ) values (
    current_user_id, p_recipient_id, p_offered, p_requested,
    left(coalesce(p_message, ''), 500)
  ) returning id into result;
  return result;
end;
$$;