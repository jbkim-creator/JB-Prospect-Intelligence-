# JBRO MONEY FINDER Autonomous Execution Engine

## Included
- Supabase Edge Function protected by a valid Supabase JWT and an explicit `jbkim@jbrocap.com` email allowlist.
- Additive schema for opportunity records, protected/DNC entities, reward tracking, research queue, and deduplicated outbox events for REFERRAL ENGINE, CASH ENGINE, and Revenue Race.
- Web app for the three prioritized partner programs, lead registration preparation, research task intake, and reward tracking.
- Lead deduplication by normalized company domain/email; protection lookup against registered customers, active deals, existing contacts, and DNC entries.
- No API/browser submission, contract, email, or payment action is implemented. This is an enforced product boundary, not a hidden background action.

## Deploy
1. Inspect existing Supabase schema while the project is active. The migration creates only `mf_*` tables and grants service-role-only access.
2. Apply `supabase/migrations/202611270001_money_finder.sql`.
3. Deploy the `money-finder` Edge Function with JWT verification enabled. Supabase supplies `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
4. Host `index.html` from GitHub Pages at the repository's `/money-finder/` path. Configure the app with the function URL and a Supabase Auth access token.
5. Seed `mf_protected_entities` from the authoritative customer/DNC/active-deal lists before production registration. Do not import or contact existing relationships without the established JBRO permission.

## Platform integration boundary
Official program pages are linked for Visual Factories, Indeavor, and Dev Partners. No public enrollment API or authorized program-account credentials were available in the inspected context, so connectors do not submit or scrape forms. Registration remains a prepared draft for an operator to review and approve. Research work is queued; the current implementation does not call a paid LLM or claim to have completed external research automatically.

## Local check
Open `index.html` directly to inspect the UI. API operations require the Supabase function and an authorized session. External actions are absent from the API.

