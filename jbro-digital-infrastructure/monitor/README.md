# JBRO Private Deal Monitor — Supabase integration staging
Status: CODE READY / DATABASE NOT CONNECTED / NOT DEPLOYED.

## Reuse
- Existing `datacenter-investors/schema.sql` must already be applied (provides `dc_admin_users`, `dc_is_admin()`, `dc_deals`).
- Run `monitor/schema-monitor.sql` in your existing Supabase project's SQL Editor. This is an additive migration; review in staging / take backup first.
- In Supabase Auth, create a single administrator (disable public signups; use MFA where available). Put their auth UUID in `dc_admin_users` following `datacenter-investors/CRM-README.md`.
- Set only the project URL and *publishable/anon* key in `monitor/config.js`. NEVER store service-role key, passwords or internal records in GitHub.
- Host the `monitor` directory under the *same* static site only when ready. The Supabase RLS policies—not the obscurity of the URL—protect records.

## Implemented
- Single-admin Supabase password login with `dc_admin_users` authorization.
- Private opportunity list, filters, verification state, priority score, next action and due date.
- Create new opportunity, compare normalized source URLs with current loaded records and DB unique index to catch duplicate links.
- Multi-table schema for evidence links, action history, monitor runs. These additional tables currently have no UI for editing.
- Existing CRM tables are preserved.

## Not implemented / not yet tested against live DB
- Supabase project existence or connection, SQL execution, end-to-end authentication, deployed URL.
- Automated source discovery, alert scheduler, Gmail integration, fee calculation, institution matching, comprehensive similarity deduplication.
- Browser session refresh; users must sign back in when token expires.
- Existing Netlify Forms are not automatically synchronized.
- Production hardening: stronger URL validation on all DB reads, content security policy, audit logs, MFA and privacy review.

## Safety
This work is on a separate feature branch; it should NOT be merged or deployed until Supabase is connected and migration verified. Existing Render production branch `feature/jbro-digital-infrastructure-site` is unchanged.
