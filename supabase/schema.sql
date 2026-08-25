create table if not exists public.album_progress (
  user_id text primary key default (auth.jwt() ->> 'sub'),
  progress jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint album_progress_is_object check (jsonb_typeof(progress) = 'object')
);

alter table public.album_progress enable row level security;

create policy "Users can read their own album"
on public.album_progress
for select
to authenticated
using ((select auth.jwt() ->> 'sub') = user_id);

create policy "Users can create their own album"
on public.album_progress
for insert
to authenticated
with check ((select auth.jwt() ->> 'sub') = user_id);

create policy "Users can update their own album"
on public.album_progress
for update
to authenticated
using ((select auth.jwt() ->> 'sub') = user_id)
with check ((select auth.jwt() ->> 'sub') = user_id);
