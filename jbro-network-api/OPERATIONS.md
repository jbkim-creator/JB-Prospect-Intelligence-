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
