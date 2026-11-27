-- Additive MONEY FINDER schema. Does not alter existing JBRO tables.
create extension if not exists pgcrypto;

create table if not exists public.mf_system_state (
  id boolean primary key default true check (id),
  protection_seeded boolean not null default false,
  updated_at timestamptz not null default now()
);
insert into public.mf_system_state (id, protection_seeded) values (true, false) on conflict (id) do nothing;

create table if not exists public.mf_protected_entities (
  id uuid primary key default gen_random_uuid(),
  entity_name text not null,
  normalized_domain text,
  normalized_email text,
  protection_type text not null check (protection_type in ('customer','dnc','existing_contact','active_deal')),
  source_ref text,
  created_at timestamptz not null default now()
);
create index if not exists mf_protected_domain_idx on public.mf_protected_entities(normalized_domain);
create index if not exists mf_protected_email_idx on public.mf_protected_entities(normalized_email);

create table if not exists public.mf_leads (
  id uuid primary key default gen_random_uuid(),
  company text not null,
  normalized_domain text,
  normalized_email text,
  contact_email text,
  website text,
  country text,
  program text not null check (program in ('Visual Factories','Indeavor','Dev Partners')),
  fit_reason text not null,
  source text,
  reward_terms text,
  review_status text not null check (review_status in ('eligible','duplicate','protected','dnc','needs_review')),
  stage text not null default 'registration_draft' check (stage in ('identified','qualified','registration_draft','submitted','accepted','rejected','closed')),
  registration_data jsonb not null default '{}'::jsonb,
  approval_required boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists mf_lead_domain_idx on public.mf_leads(normalized_domain);
create index if not exists mf_lead_email_idx on public.mf_leads(normalized_email);

create table if not exists public.mf_rewards (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid not null references public.mf_leads(id) on delete restrict,
  status text not null check (status in ('potential','qualified','earned','payable','paid','disputed')),
  amount numeric(18,2), currency char(3) not null default 'USD', evidence text,
  approval_required boolean not null default true,
  created_at timestamptz not null default now()
);
create index if not exists mf_reward_lead_idx on public.mf_rewards(lead_id, created_at desc);

create table if not exists public.mf_research_tasks (
  id uuid primary key default gen_random_uuid(), title text not null, question text not null,
  output_format text not null, status text not null default 'queued' check (status in ('queued','in_progress','needs_review','complete')),
  output_markdown text, sources jsonb not null default '[]'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.mf_engine_outbox (
  id uuid primary key default gen_random_uuid(), lead_id uuid references public.mf_leads(id) on delete restrict,
  event_key text not null unique, target_engine text not null check (target_engine in ('REFERRAL ENGINE','CASH ENGINE','Revenue Race')),
  event_type text not null, payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued','exported','acknowledged','blocked')),
  approval_required boolean not null default true, created_at timestamptz not null default now()
);

-- All writes and reads go through the JWT-checked, email-allowlisted Edge Function.
alter table public.mf_protected_entities enable row level security;
alter table public.mf_system_state enable row level security;
alter table public.mf_leads enable row level security;
alter table public.mf_rewards enable row level security;
alter table public.mf_research_tasks enable row level security;
alter table public.mf_engine_outbox enable row level security;
revoke all on public.mf_system_state, public.mf_protected_entities, public.mf_leads, public.mf_rewards, public.mf_research_tasks, public.mf_engine_outbox from anon, authenticated;
grant all on public.mf_system_state, public.mf_protected_entities, public.mf_leads, public.mf_rewards, public.mf_research_tasks, public.mf_engine_outbox to service_role;
