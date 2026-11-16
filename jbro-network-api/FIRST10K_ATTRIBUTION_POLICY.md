# FIRST10K conversion reporting — 2.5 Trade Network by JBRO
Effective 2026-11-16.

## Already implemented
- Public landing URL supports an optional `ref` code, for example `?lang=en&ref=LINKEDIN-FIRST10K#first-trade-offer`.
- On successful voluntary partner application, the **selected user-entered referral code** is stored in the existing `partner_applications.summary` prefix as `[Referral: CODE]`; an opted-in fee waiver review is `[FIRST10K coupon request]`. No new database table, visitor cookies, tracking pixels, automated marketing, or third-party analytics SDK is added.
- The private, admin-authenticated `/api/admin/first10k-funnel` provides per-code **application counts, coupon-interest flags, approved application counts, coupon issuance counts**, plus overall recorded USD fee discount and coupon-linked **completed** deal value. `/admin` shows this section.
- Non-registered referrals aggregate as `UNATTRIBUTED`. `ref` values have only `[A-Za-z0-9_-]` characters retained and are limited to 40 chars.
- Grouped summaries contain no email, organization or buyer identity, but the existing secured application review shows individual inquiry data as before.
- **Completed** coupon-associated GMV counts each linked USD Deal Room only once if a signed contract exists and the latest inspection, shipment, delivery and payment stages are all verified. A deal may be associated with a coupon but the association does not establish that the coupon caused the deal.
- USD discount uses cents and does not represent cash cost or JBRO revenue. These figures are historical/lifetime; the instrument does not yet assert monthly attribution or historical Gmail lead matching.
- Intake remains explicitly consented and gated by the current service authorization. Merely viewing the page sends **no tracking events**.

## Unsupported / not measured
- Unique visitors, page views, ad clicks, CTR, ad conversion rate, email opens, unique domain attribution, first/last click, GDPR consent to advertising trackers: **not implemented**.
- Existing Gmail leads are not automatically converted into platform partner applications.
- FIRST10K is never auto-approved or auto-issued on website application, and no existing deal fee agreement is altered.

## Active FIRST10K terms
One authorized, first-time fee-paying **buyer OR seller** (not both sides automatically), one eligible **USD** first transaction, agreed JBRO **2.5% fee** waived only on the first **US$10,000 goods principal**, maximum **US$250**. Prior eligibility approval and signed fee terms required. No retroactive stacking, no guarantee of transaction. Taxes, transport, FX and inspection costs are excluded.

## Initial launch checks
1. Sign in to `https://jbro-network-api.onrender.com/admin` via the existing admin bearer token.
2. Confirm FIRST10K Campaign Funnel shows **zero** until a real, consented application or coupon is recorded.
3. Submit only real consented applications via live landing, not fabricated lead data.
4. Confirm coupon requests/approvals are distinguished from issued coupon records and contract completion.
5. Use manual publishing of the prepared EN/KO campaign posts. Do not send repetitive coupon-only sales emails to counterparties already contacted that day.
