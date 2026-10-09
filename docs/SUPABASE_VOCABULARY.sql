-- AI Daily Intelligence V1: Supabase vocabulary event ledger.
-- Run once in Supabase > SQL Editor. Never expose a service_role key in the website.
-- Clients cannot update/erase other people's events. Each mutation is append-only.
create table if not exists public.vocabulary_events (
  event_id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  word text not null check (word ~ '^[a-z][a-z''-]{0,45}$'),
  payload jsonb not null default '{}'::jsonb,
  deleted boolean not null default false,
  created_at timestamptz not null default now(),
  batch_order smallint not null default 0 check (batch_order between 0 and 99),
  constraint vocabulary_payload_is_object check (jsonb_typeof(payload) = 'object'),
  constraint vocabulary_payload_length check (length(payload::text) <= 4096)
);
-- Repeatable migration for tables created with an earlier copy of V1 SQL.
alter table public.vocabulary_events
  add column if not exists batch_order smallint not null default 0
  check (batch_order between 0 and 99);
-- Index previously ordered by random event_id on timestamp ties.
drop index if exists public.vocabulary_events_owner_order_idx;
create index vocabulary_events_owner_order_idx
  on public.vocabulary_events(user_id, created_at, batch_order, event_id);

alter table public.vocabulary_events enable row level security;
-- Clients must not supply/alter created_at: server timestamps decide cross-device order.
revoke all on public.vocabulary_events from public, anon, authenticated;
grant select, delete on public.vocabulary_events to authenticated;
grant insert (event_id, user_id, word, payload, deleted, batch_order)
  on public.vocabulary_events to authenticated;

drop policy if exists "owner select vocabulary events" on public.vocabulary_events;
create policy "owner select vocabulary events"
  on public.vocabulary_events for select to authenticated
  using ((select auth.uid()) = user_id);
drop policy if exists "owner append vocabulary events" on public.vocabulary_events;
create policy "owner append vocabulary events"
  on public.vocabulary_events for insert to authenticated
  with check ((select auth.uid()) = user_id);
drop policy if exists "owner delete vocabulary events" on public.vocabulary_events;
create policy "owner delete vocabulary events"
  on public.vocabulary_events for delete to authenticated
  using ((select auth.uid()) = user_id);

-- Within one server insert request, batch_order (0..99) preserves client edit order.
-- No UPDATE policy: old events cannot be silently altered by clients.
-- Deleting one saved word creates a tombstone (old history remains).
-- To erase an entire account's cloud vocabulary history, execute as that
-- authenticated user: DELETE /rest/v1/vocabulary_events?user_id=eq.<self-id>.
