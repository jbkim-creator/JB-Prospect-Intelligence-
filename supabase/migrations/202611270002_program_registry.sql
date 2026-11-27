-- Track partner-program enrollment separately from customer and referral leads.
create table if not exists public.mf_partner_registry (
  id text primary key,
  display_name text not null,
  homepage text not null,
  contact_email text,
  status text not null default 'not_contacted' check (status in ('not_contacted','draft_saved','inquiry_sent','terms_received','eligible','registered','paused','not_eligible')),
  fee_notes text,
  updated_at timestamptz not null default now()
);
alter table public.mf_partner_registry enable row level security;
revoke all on public.mf_partner_registry from anon, authenticated;
grant all on public.mf_partner_registry to service_role;

insert into public.mf_partner_registry (id,display_name,homepage,status,contact_email,fee_notes) values
 ('dev_partners','Dev Partners','https://devpartners.co/referral','inquiry_sent','steven@devpartners.co','Inquiry sent 2026-11-27; awaiting confirmation of current qualified-meeting and revenue-share terms.'),
 ('indeavor','Indeavor','https://www.indeavor.com/partnerships/','draft_saved','info@indeavor.com','Gmail draft saved 2026-11-27; not sent. Verify reward claims and Korean corporate eligibility before submission.'),
 ('visual_factories','Visual Factories','https://visualfactories.com/partners/','not_contacted',null,'Official partner page requests a referral fee schedule; no company-specific fees verified yet.')
on conflict (id) do nothing;

-- Known active JBRO counterparties are pre-protected. This is deliberately
-- not marked complete: the authoritative full customer/DNC list is still required.
insert into public.mf_protected_entities (entity_name,protection_type,source_ref)
select v.entity_name, v.protection_type, 'known_active_deal_memory_2026-11-27'
from (values
 ('Federal Equipment','active_deal'),('RuiReach','active_deal'),('MET-TECH GmbH','active_deal'),
 ('Sunspike','active_deal'),('MergersCorp','active_deal'),('Cushman & Wakefield','active_deal'),
 ('ServerPartDeals','active_deal'),('Sun Techno','active_deal'),('Global Carbon Capital','active_deal'),
 ('DCC EU','active_deal'),('Gordon Brothers','active_deal'),('American Plant and Equipment','active_deal'),
 ('EnTrust Global','active_deal'),('Next Infrastructure Core','active_deal'),
 ('Portless','existing_contact'),('Dev Partners','existing_contact'),('Indeavor','existing_contact')
) as v(entity_name,protection_type)
where not exists (
 select 1 from public.mf_protected_entities p
 where lower(p.entity_name)=lower(v.entity_name) and p.protection_type=v.protection_type
);
