# Jbro Capital — Institutional Data Center Buyer Pool CRM
Production-facing admin UI route: `/datacenter-investors/admin.html`. Public landing page and Netlify Forms are unchanged.

## Enable secure CRM
1. Create a separate Supabase project and run `schema.sql` in the SQL Editor. **This database does not connect to Netlify Forms automatically.**
2. In Supabase Authentication create/invite administrator using a strong password and MFA (recommended). Disable public signups.
3. Get administrator UUID from Authentication > Users. Execute in SQL Editor:
   `insert into public.dc_admin_users(user_id) values ('ADMIN_AUTH_UUID');`
4. Configure `crm-config.js` with your Supabase Project URL and **publishable/anon** key, which are browser-safe. Never put the service role secret in public files.
5. Log in to `admin.html`. Existing Netlify registration leads can be exported by an authorized operator as CSV from Netlify dashboard, then securely imported from the CRM. Deduplication is based on institution + email. Do not commit CSV data to GitHub.
6. Add actual commission-backed opportunities manually and mark commission verified only after reviewing signed agreements and source authority.
7. Select deal/buyer, create match candidates; approved and later match stages are blocked at database level unless commission verification and deal review are completed.

## Permissions & limitations
- Client-side route is **not** the security boundary. Supabase Authentication + Postgres Row Level Security restrict all investor and deal records; the database has no anonymous table read access.
- Netlify email notifications and contact form remain active separately; syncing leads is currently a manual CSV import.
- Restrict admin access, keep only minimum necessary investor details, implement retention/deletion and obtain privacy/cross-border transfer review before production operations.
- The CRM does not send emails, automatically rate investment suitability, represent exclusivity, or create legally binding agreements.
- Do not put contracts, confidential teasers, private keys or passwords in the public repo.
