-- JBRO Monitor: additive migration for an existing Supabase project.
-- Prerequisite: apply datacenter-investors/schema.sql first if this is a NEW project.
-- Existing dc_admin_users and dc_* CRM tables are NOT dropped or modified.
create extension if not exists pgcrypto;
create table if not exists public.dc_opportunities (
 id uuid primary key default gen_random_uuid(),
 title text not null,
 asset_name text,
 country text,
 category text not null default 'data_center' check (category in ('data_center','power','energy','other')),
 transaction_type text not null default 'asset_sale' check (transaction_type in ('asset_sale','development_site','equity_ma','auction','other')),
 announcement_date date,
 deadline date,
 disclosed_value text,
 source_url text not null,
 source_name text,
 source_verified boolean not null default false,
 verification_status text not null default 'needs_review' check(verification_status in ('needs_review','verified','rejected')),
 brokerage_score smallint not null default 0 check (brokerage_score between 0 and 100),
 fee_estimate_note text,
 contact_public text,
 next_action text,
 next_action_due date,
 internal_notes text,
 status text not null default 'new' check (status in ('new','reviewing','contact_ready','contacted','closed','archived')),
 linked_deal_id uuid references public.dc_deals(id) on delete set null,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create unique index if not exists dc_opportunities_unique_source on public.dc_opportunities ((lower(btrim(source_url))));
create table if not exists public.dc_opportunity_sources (
 id uuid primary key default gen_random_uuid(),
 opportunity_id uuid not null references public.dc_opportunities(id) on delete cascade,
 url text not null,
 source_type text not null default 'official',
 evidence_note text,
 checked_at timestamptz,
 created_at timestamptz not null default now(),
 unique(opportunity_id,url)
);
create table if not exists public.dc_opportunity_actions (
 id uuid primary key default gen_random_uuid(),
 opportunity_id uuid not null references public.dc_opportunities(id) on delete cascade,
 action_type text not null default 'research',
 note text not null,
 due_at timestamptz,
 completed_at timestamptz,
 created_at timestamptz not null default now()
);
create table if not exists public.dc_monitor_runs (
 id uuid primary key default gen_random_uuid(),
 mode text not null default 'manual',
 new_count integer not null default 0,
 duplicate_count integer not null default 0,
 notes text,
 started_at timestamptz not null default now(),
 completed_at timestamptz
);
create or replace function public.dc_monitor_touch() returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at=now(); return new; end $$;
drop trigger if exists dc_monitor_touch_trg on public.dc_opportunities;
create trigger dc_monitor_touch_trg before update on public.dc_opportunities for each row execute function public.dc_monitor_touch();
alter table public.dc_opportunities enable row level security;
alter table public.dc_opportunity_sources enable row level security;
alter table public.dc_opportunity_actions enable row level security;
alter table public.dc_monitor_runs enable row level security;
revoke all on public.dc_opportunities, public.dc_opportunity_sources, public.dc_opportunity_actions, public.dc_monitor_runs from anon;
grant select,insert,update,delete on public.dc_opportunities, public.dc_opportunity_sources, public.dc_opportunity_actions, public.dc_monitor_runs to authenticated;
drop policy if exists "dc_monitor_admin_opportunities" on public.dc_opportunities;
create policy "dc_monitor_admin_opportunities" on public.dc_opportunities for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
drop policy if exists "dc_monitor_admin_sources" on public.dc_opportunity_sources;
create policy "dc_monitor_admin_sources" on public.dc_opportunity_sources for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
drop policy if exists "dc_monitor_admin_actions" on public.dc_opportunity_actions;
create policy "dc_monitor_admin_actions" on public.dc_opportunity_actions for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
drop policy if exists "dc_monitor_admin_runs" on public.dc_monitor_runs;
create policy "dc_monitor_admin_runs" on public.dc_monitor_runs for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
