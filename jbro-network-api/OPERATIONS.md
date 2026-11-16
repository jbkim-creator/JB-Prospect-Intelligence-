## Partner opportunity workspace — verified 2026-11-16

- Partner workspace URL: https://jbro-network-api.onrender.com/partner
- Admin review URL: https://jbro-network-api.onrender.com/admin
- Database tables: `partner_access` (SHA-256 hashed one-time access keys; revoked by timestamp), `partner_opportunities` (partner ownership and status).
- Partner cannot log in from an application approval alone. Admin must explicitly issue an access key for an approved application. Generated key is shown once; a new key rotates the previous key.
- Partner submissions: buy requirement, stock offer, industrial asset, project opportunity, or service capability. API validates a non-confidential information checkbox; maximum 30 submitted opportunities per partner per 24 hours.
- Partner list API filters by authenticated `application_id`; partners cannot retrieve another organization's records.
- Admin can list and review all opportunities; **qualifying an opportunity does not automatically expose it to other partners or trigger sales emails**.
- Live Neon-backed smoke test: Render log `JBRO_PARTNER_ISOLATION_SMOKE_PASS`. It tested 2 synthetic applicants: intake, approval, one-time key issue, opportunity submission, owner isolation, admin review, revocation, unauthenticated admin denial.
- The test-only flag `JBRO_PARTNER_SMOKE_TEST` was disabled immediately afterward. Neon database queried after cleanup: 0 applications, 0 credentials, 0 opportunities, 0 activity events.
- Public-accessible /partner HTML is an authentication prompt only; all data APIs require an active partner key.
- Security limitations: invite keys are long-lived until rotation/revocation; no multi-factor authentication, no password reset workflow, no per-request abuse monitoring, no audited partner legal agreement or privacy policy. Before scaling partners, replace invite keys with managed identity or short-lived sessions, formalize data processing/retention and backups, and run independent browser security tests.
- No invitation emails have been sent, no customer has been granted access, and no real opportunities have yet been submitted.

---

## Partner Review Dashboard — deployed 2026-11-16

- URL: https://jbro-network-api.onrender.com/admin
- Source: `jbro-network-api/admin.html`, `admin.css`, `admin.js`, served from the API as same-origin assets.
- Render deploy: `dep-dbt97i56e07s73bq4up0` status `live`. Startup log: `JBRO_NEON_DB_STARTUP_READY`.
- Dashboard shows applications and filters by status, and updates status via authenticated PATCH. **Approval is administrative screening only; it does not grant access to deal records or trigger an email.**
- Access requires the Render environment value `JBRO_ADMIN_TOKEN` (length 32+). To set a token you know, go to Render > `jbro-network-api` > Environment > edit `JBRO_ADMIN_TOKEN` with a unique random secret of at least 32 characters, save and wait for its resulting deploy to be live. Do not send the token in chat, email or GitHub.
- The login token is held in JavaScript memory only, not localStorage/cookies. The dashboard does not embed it in public source or URLs. Use the Lock button when done.
- The UI itself loads publicly, but no applicant details are returned by the server without a valid bearer token.
- Render API public browser reachability and manual button-click QA still need independent verification.
- Post-deploy Neon check: zero applications and zero activity events.

---

## End-to-end write / review verification — 2026-11-16

- Render deploy `dep-dbt951ff3r2c73ca7et0` reached `live`.
- Server logs confirmed both `JBRO_NEON_DB_STARTUP_READY` and `JBRO_INTAKE_SMOKE_PASS`.
- Gated smoke test invoked the deployed Flask app's HTTP routes via its internal test client using the **real Neon database**: submit synthetic application (201), admin list (200), admin review PATCH (200), persisted status read, unauthorized admin read (401).
- Scoped synthetic application and its activity records were deleted immediately after verification; subsequent Neon SQL showed 0 application records and 0 activity records, including 0 `JBRO_SMOKE_TEST_%` rows.
- The temporary smoke-test flag `JBRO_SMOKE_TEST` was set back to `0`; Render redeploy triggered.
- This proves server-side route behavior with Neon; external browser form submission and actual customer approval remain untested.
- Do not enable the smoke-test flag routinely. It is only for controlled release verification.
- A manual admin dashboard is not implemented. Existing protected admin API accepts an admin bearer secret, which must never be published.

---

# Neon migration verified — 2026-11-16

- Neon project: `jbro-os-network` (`misty-glitter-91914189`), database `jbro_os`, Singapore, PostgreSQL 17.
- Tables `partner_applications`, `activity_events` and the application index created. SQL query confirmed 0 applications immediately after creation.
- Render service `jbro-network-api` (`srv-dbt8fh6k1f9s73b5a9q0`) has secret `DATABASE_URL` set through Render environment variables. Credential is not in GitHub.
- Render deploy `dep-dbt8vflg1s2s7394euog` is `live` and startup logs include `JBRO_NEON_DB_STARTUP_READY`, confirming an actual successful database connection from the deployed API.
- **Not yet independently verified:** external public form submission, admin approval flow, backups, and automated Gmail sync.
- Original Render database `dpg-dbt8eu67bikc73dc0neg-a` is preserved until no data must be migrated and it is safe to retire. Its trial expires 2026-12-16.
- Neon Free uses auto-suspend after the plan's idle timeout (project setting 0 means default). Stay inside quota and plan secure backups.

---

# JBRO Network API — Render operating procedure

Service: `jbro-network-api` (Singapore, free web service)
Database: `jbro-os-network-db` (Render PostgreSQL 18, Singapore, free; expires 2026-12-16)
Portal: https://jbro-global-network.onrender.com

## Current safety state
- The API is deployed but **does not accept applications until DATABASE_URL is configured**.
- `POST /api/partner-applications` returns HTTP 503 without the DB setting.
- The portal explicitly offers a manual email fallback and must never falsely claim an application was saved.
- Admin endpoints require the `JBRO_ADMIN_TOKEN` bearer token. No token means access denied.
- No prior JBRO deal, Gmail or buyer/supplier datasets are in the public repository.

## One-time database wiring (Render Dashboard)
1. Open Render > PostgreSQL > `jbro-os-network-db`, and copy its **Internal Database URL** using Render's credential-copy control. Do not paste this URL into chat, GitHub, frontend code or logs.
2. Open Render > Web Services > `jbro-network-api` > Environment.
3. Add a secret environment variable named `DATABASE_URL`, paste the copied internal URL as its value, and save. This will trigger a deployment.
4. Visit `https://jbro-network-api.onrender.com/readyz`. Only `{"status":"ready"}` confirms the database can be reached and schema initialized.
5. Submit one **test-only** partner inquiry via the public portal. Confirm it returns a `JBRO-P-...` reference.
6. Only after a successful test, introduce real partners. Replace or rotate `JBRO_ADMIN_TOKEN` as needed; never publish it.

## Admin API
- `GET /api/admin/applications`: list latest 100 applications. Requires `Authorization: Bearer <token>`.
- `PATCH /api/admin/applications/<id>`: set status to pending/reviewing/approved/rejected. Requires same token.
- There is no browser administrator dashboard yet; access is API-only.

## Operating safeguards and limitations
- Public data collection is limited to organization, business email, optional country, role, nonconfidential summary, explicit consent and timestamp.
- Backend requires specific origin and enforces basic per-instance rate limiting and a honeypot; this is **not** production-grade bot protection. Stronger rate limits, abuse monitoring, encryption policy, retention/deletion workflows, GDPR privacy information and operational backups are required before broad outreach.
- Render free Postgres expires **2026-12-16**. A reminder is scheduled for **2026-12-09 at 09:00 Europe/London**.
- Render free web services may sleep and restart; do not use as an operational SLA.
- The API does **not** currently synchronize Gmail, expose private deal rooms, process partner payouts or auto-send messages.
