## Buyer–Seller Deal Rooms — 2026-11-16

- Code `jbro-network-api/dealrooms.py`. Administrator creates private KRW sale terms identifying two approved buyer/seller partner applications; one optional linked draft `reward_deals` record must have the same total deal value.
- Sale terms capture verified-by-operator **names as entered**, description, quantity/unit, amount, delivery, inspection, payment, governing law, dispute resolution, and optional additional terms. They are not automatically verified by law firms, banks, inspection agencies or buyer/seller registries.
- Admin issues immutable SHA-256-identified version 1 draft for both parties to view. Only approved linked buyer and seller can retrieve it or accept using individual partner access; a third partner is denied. Both must separately declare representative authority and agree to the exact frozen hash.
- Database `deal_rooms`, `deal_sale_contracts`, `deal_sale_assents`, `deal_room_audit`; optional link `deal_rooms.reward_deal_id` to separate 2.5% JBRO fee and partner reward pool.
- Linked fee/reward contract can only finalize after the buyer/seller sale document status is signed. Even then no commission is presumed received and no bank transfer is performed by the app.
- Live Neon-backed integration test: `JBRO_DEALROOM_SMOKE_PASS` from Render. Verified third-party access denial, wrong document-hash rejection, bilateral signatures, isolation, linked reward contract blocker and post-sign settlement blocked without actual fee receipt. All synthetic records cleaned up; Neon reported zero rooms, zero signatures, zero reward deals and zero synthetic applicants after test. Temporary smoke-test environment flag `JBRO_DEALROOM_SMOKE_TEST` was switched back to 0 and a normal deploy requested.
- Admin UI: https://jbro-network-api.onrender.com/admin ; partner UI: https://jbro-network-api.onrender.com/partner ; both require existing authentication.
- **Critical commercial boundary:** this is a pilot contract acceptance workflow, NOT a legal guarantee of valid e-signatures, identity authentication, signer authority, contract enforceability, escrow, invoice issuance, shipment, asset transfer, goods quality, or cash payment. No external customer has entered or signed a live sale in this rollout. Agreement templates are placeholders requiring jurisdiction-specific legal advice, actual registered legal entities, authority checks, tax, sanctions/export-control checks, Incoterms and dispute provisions. Current access keys are long-lived and not multi-factor authenticated; implement stronger authenticated signatures, downloadable signed copies, an audit archive, amendment/cancellation workflow, and legal review before using for high-value binding transactions.
- Current version supports **one immutable version 1 per room**; edits after issue are intentionally disabled. To amend terms, start a new room until a supersession workflow is implemented.

---

## In-platform participation/reward agreements — 2026-11-16

Implemented `jbro-network-api/contracts.py`. Routes:
- `POST /api/admin/rewards/<deal_id>/contracts/issue`: freeze one per-participant commission-sharing agreement after deal draft has all approved participants and 100% total allocation; requires administrator legal-review confirmation.
- `GET /api/admin/rewards/<deal_id>/contracts`: private contract documents and bilateral assent status.
- `GET /api/partner/contracts`: each approved invite-only partner sees only their own terms/document and its immutable SHA-256 fingerprint.
- `POST /api/partner/contracts/<contract_id>/accept`: signed-in participant submits full representative name and explicit authorized-signatory and read-and-accept confirmations against the exact SHA-256 fingerprint. Cross-partner signatures, changed documents and repeat signatures are rejected.
- `POST /api/admin/contracts/<contract_id>/countersign`: authenticated JBRO administrator separately accepts the same document hash.
- `POST /api/admin/rewards/<deal_id>/contracts/finalize`: requires all participant-specific agreements fully countersigned and validated 100% allocations, then changes reward deal to `signed` with aggregate SHA-256 reference.
- Legacy `POST /api/admin/rewards/<deal_id>/sign` always rejects unilateral admin agreement attestation.

Neon: `reward_contracts` (frozen versioned agreement text, SHA-256) and `reward_contract_assents` (unique per-party consent, timestamp, representative, document hash, pseudonymized IP fingerprint, UA). Mutations of participant allocations are locked after documents have been issued. No automatic funds are transferred, and no customer purchase order/seller contract is represented here.

Live Neon-backed smoke test confirmed `JBRO_PLATFORM_CONTRACT_SMOKE_PASS`: frozen hash integrity, unauthorized signer and wrong-hash rejection, duplicate assent prevention, all-party finalization and no settlement before bank receipts. The test used two fake partners, then deleted all test agreements, signatures, offers and fake partner identities. Test flag `JBRO_CONTRACT_SMOKE_TEST` switched back to `0` with new Render deployment.

**Production limitations:** This is an authenticated online acceptance MVP, not a qualified digital-signature certificate, legal identity verification, PKI-backed nonrepudiation, or guaranteed enforceability of a contract. The current partner account key is a long-lived bearer token without MFA; operator identity and authorized signatory declarations are self-reported. Before legally binding commercial launch, replace with MFA identity provider/qualified e-sign vendor as necessary; verify the contracting entity's exact registration and jurisdiction and approved signatory identity; obtain legal review of governing law, taxes and data retention; implement signed document download/receipts, a stronger tamper-evident audit/log archive and a cancellation/amendment process. Participation contracts are distinct from actual buyer-seller sale/purchase agreements and counterparty purchase orders. 

---

## Deal Rewards 2.5% — accounting MVP (2026-11-16)

Purpose: share **a portion of the 2.5% fee actually received by JBRO on one agreed side of a trade**, not 2.5% of the entire deal as a participation reward.

- Source: `jbro-network-api/rewards.py`, registered in `server.py`. Neon DB tables: `reward_deals`, `reward_contributors`, `reward_receipts`, `reward_settlements`, `reward_audit`.
- Financial unit: KRW integer won only. Fee = transaction amount * 250 / 10,000, truncated to won. Reward pool = actually received JBRO commission * assigned share (default 30%, maximum 40%). Not tax- or expense-adjusted. No forex conversion.
- Only the admin can record new draft pools and assign approved partner participation with separate written individual fee/role references. Allocations must add to exactly 100% before a pool can be marked signed. The admin's signed-reference entry is an assertion, not automatic legal document validation.
- Only admin-confirmed **actual commission receipts** with a bank statement reference enter the ledger. Cumulative receipts cannot exceed the contractual 2.5% ceiling. Once a settlement is approved, receipt recording for the pool is locked; additional receipts require a later formally designed adjustment/true-up workflow.
- The admin can approve settlement amounts only after receipt, signed-reference, complete allocation and affirmative compliance check. Individual settlement approvals cannot be repeated. Integer division residuals remain unallocated within JBRO's funds.
- No funds are sent by this service. The mark-paid endpoint only records an independently confirmed bank transfer reference; it is not a disbursement mechanism.
- Partners see only their own **signed** deal allocations and approved/paid ledger amounts. The system does not expose other partners' names, share percentages or private offers. XP remains separate and has no claim on money.
- Temporary `JBRO_REWARD_SMOKE_TEST=1` runs a synthetic test at startup including actual Neon DB CRUD for two partners, 100m KRW trade value, 2.5m KRW commission receipt, 750k KRW reward pool and 1.75m KRW retained before costs, duplicate prevention, access isolation, and scoped cleanup. **Disable after successful verification.**
- Privacy, partner KYC/AML or sanctions screening, documented authority/fee agreement, Korean and cross-border tax/legal review, invoices, retention schedule, reversal/chargeback process, bank reconciliation, MFA, and independent security audit remain required before real financial settlement.
- No actual commission receipts or third-party payouts have been recorded or authorized by this initial rollout.

---

## JBRO TradeQuest — first live release (2026-11-16)

- Partner page: https://jbro-network-api.onrender.com/partner (invite-only)
- Admin page: https://jbro-network-api.onrender.com/admin (admin token required)
- Added `tradequest.py` and Neon tables `tradequest_missions`, `tradequest_claims`, `tradequest_xp_ledger`.
- Admin creates draft missions, explicitly opens/closes them, reviews claims and verifies or rejects contributions. Every verified claim grants fixed, non-transferable XP exactly once via database-enforced unique `claim_id`. No monetary representation or payout.
- Partner sees only open mission description and their own claim status/total XP; submissions never expose identities or another partner's claim evidence. Claim text is private to submitting partner and admin.
- Real Neon smoke test passed: Render log `JBRO_TRADEQUEST_SMOKE_PASS`. Tested draft invisibility, open visibility, authenticated contribution, duplicate claim rejection, other-partner isolation, verified XP, repeat-award rejection, unauthenticated admin denial. All synthetic records cleaned up.
- Smoke test env `JBRO_QUEST_SMOKE_TEST=0` restored; normal production redeploy triggered.
- Two generic **exploratory** missions were added as open records: semiconductor sourcing capability and enterprise HDD supply-channel qualification. These are clearly labeled PILOT and explicitly NOT confirmed purchase orders. They contain no counterparty names, confidential terms or actual RFQ representation.
- As of deployment, claims and XP awards are 0; no real partners were invited or paid.
- Future hardening: CAPTCHA/rate-limiting for contributions, MFA/short-lived partner sessions, privacy controls, audited evidence and appeals workflow; external browser QA before broad rollout.

---

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
