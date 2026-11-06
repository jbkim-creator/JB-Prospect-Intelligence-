-- Jbro Capital Investor CRM v1. Run in Supabase SQL Editor.
-- Public site continues collecting leads via Netlify Forms.
-- CRM stores imported leads ONLY after authenticated admin login.
create extension if not exists pgcrypto;
create table if not exists public.dc_admin_users (
 user_id uuid primary key references auth.users(id) on delete cascade,
 created_at timestamptz not null default now()
);
create or replace function public.dc_is_admin() returns boolean language sql stable security definer
set search_path = '' as $$
 select exists(select 1 from public.dc_admin_users where user_id=auth.uid());
$$;
revoke all on function public.dc_is_admin() from public, anon;
grant execute on function public.dc_is_admin() to authenticated;
create table if not exists public.dc_buyers (
 id uuid primary key default gen_random_uuid(),
 institution text not null,
 contact_name text,
 email text not null,
 country text,
 investor_type text,
 ticket_range text,
 target_region text,
 strategy text,
 mandate_notes text,
 status text not null default 'new' check (status in ('new','qualifying','qualified','matched','closed','inactive')),
 grade text not null default 'C' check (grade in ('A','B','C')),
 qualification_notes text,
 source text not null default 'netlify_forms',
 last_contact_at date,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create unique index if not exists dc_buyers_unique_email_institution on public.dc_buyers (lower(email),lower(institution));
create table if not exists public.dc_deals (
 id uuid primary key default gen_random_uuid(),
 code text not null unique,
 deal_name text not null,
 geography text,
 structure text,
 min_ticket_usd_m numeric(14,2),
 max_ticket_usd_m numeric(14,2),
 stage text not null default 'sourcing' check(stage in ('sourcing','verified','paused')),
 commission_verified boolean not null default false,
 commission_verified_at date,
 fee_terms_note text,
 internal_notes text,
 created_at timestamptz not null default now()
);
create table if not exists public.dc_matches (
 id uuid primary key default gen_random_uuid(),
 buyer_id uuid not null references public.dc_buyers(id) on delete cascade,
 deal_id uuid not null references public.dc_deals(id) on delete cascade,
 status text not null default 'candidate' check(status in ('candidate','approved','teaser_sent','nda','diligence','closed','declined')),
 notes text,
 created_at timestamptz not null default now(),
 unique (buyer_id,deal_id)
);
create or replace function public.dc_match_guard() returns trigger language plpgsql security definer
set search_path = '' as $$
begin
 if new.status in ('approved','teaser_sent','nda','diligence','closed')
 and not exists(select 1 from public.dc_deals where id=new.deal_id and commission_verified=true and stage='verified')
 then raise exception 'Deal must be verified with commission agreement before approval'; end if;
 return new;
end $$;
drop trigger if exists dc_match_guard_trigger on public.dc_matches;
create trigger dc_match_guard_trigger before insert or update on public.dc_matches
for each row execute function public.dc_match_guard();
create or replace function public.dc_touch_buyer() returns trigger language plpgsql
set search_path = '' as $$ begin new.updated_at=now();return new;end $$;
drop trigger if exists dc_buyer_updated on public.dc_buyers;
create trigger dc_buyer_updated before update on public.dc_buyers
for each row execute function public.dc_touch_buyer();
alter table public.dc_admin_users enable row level security;
alter table public.dc_buyers enable row level security;
alter table public.dc_deals enable row level security;
alter table public.dc_matches enable row level security;
revoke all on public.dc_admin_users,public.dc_buyers,public.dc_deals,public.dc_matches from anon;
grant select on public.dc_admin_users to authenticated;
grant select,insert,update,delete on public.dc_buyers,public.dc_deals,public.dc_matches to authenticated;
drop policy if exists "admin reads own access" on public.dc_admin_users;
create policy "admin reads own access" on public.dc_admin_users for select to authenticated using (user_id=auth.uid());
drop policy if exists "admin only buyer data" on public.dc_buyers;
create policy "admin only buyer data" on public.dc_buyers for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
drop policy if exists "admin only deal data" on public.dc_deals;
create policy "admin only deal data" on public.dc_deals for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
drop policy if exists "admin only match data" on public.dc_matches;
create policy "admin only match data" on public.dc_matches for all to authenticated using (public.dc_is_admin()) with check (public.dc_is_admin());
