# 2.5 Trade Network by JBRO — Trial-to-GMV Operations KPI

Effective 2026-11-16. The actual baseline in Neon is currently **0** approved partners, 0 signed / completed Deal Rooms, 0 completed GMV, and 0 coupon issues at time of evaluation. Existing Gmail pipeline leads are external pre-contract opportunities, **not yet realized GMV**.

## Read-only admin dashboard
- Open: `https://jbro-network-api.onrender.com/admin`; log in with the existing JBRO admin token. No public KPI endpoint.
- `GET /api/admin/gmv-kpis` requires the same existing bearer token (minimum 32 chars); no database changes are made.
- **Signed pipeline GMV**: reward deal value linked to a Deal Room with a *signed* sale contract. Unpaid/undelivered signed deals are not completed GMV.
- **Completed GMV**: sum each Deal Room's linked reward deal value **once**, only if a signed sale contract exists and the *latest status of each* inspection, shipment, delivery and payment execution stage is `verified`. Verification is administrative, not an independent bank audit.
- **Recorded JBRO commissions**: sum of documented `reward_receipts.amount_won` (minor unit). Separate from GMV and requires bank reconciliation.
- USD is stored as integer cents; KRW as won. Do not aggregate the two currencies in the same amount.
- Dashboard is **lifetime** since DB creation, not the prior month's cash or historical sales in Gmail. Do not mistake it for a rolling monthly GMV without adding event timestamps and separate monthly scope.
- Draft deals, open RFQs, indicative offers, duplicated outreach, unreconciled money transfers and FIRST10K coupons are never GMV.
- FIRST10K is the waiver on the specified **one-side 2.5% JBRO fee** applicable to the **first US$10,000 eligible USD transaction value**, maximum **US$250**. Do not equate waived fee with earned revenue.

## Operating milestones
1. **Trial**: a real buyer PO with agreed seller terms, authenticity review and secure pre-shipment inspection. Status remains pilot until verifiable signed terms and documented execution.
2. **First closed deal**: complete the inspection→shipment→delivery→payment verification; reconcile any JBRO commission with bank statement.
3. **Scale 1**: first repeat order from the same verified buyer, with higher total quantity or item additions when demand supports it.
4. **Scale 2**: add a second independently verified supply source and broaden buyers without disclosing confidential customer info.
5. **Scale 3**: run monthly completed GMV growth targets only after at least one actual completed deal exists. Suggested aspirational goals: day30 US$10,000, day60 US$100,000, day90 US$500,000, reviewed after real trial completion; not forecasts or actual achieved revenue.

## Real trial candidates at start
- RuiReach exact TI TPS92662AQPHPRQ1 (Hong Kong destination): trial **100–200 pcs proposed**, or 1 unopened 1,000-pc reel if physical split invalidates sealed factory packaging. Buyer approval not yet received. Origin-IC and AOYUE offers both indicative/unverified.
- ExcessChip STMicroelectronics M41T00M6F 2,500pcs: buyer initial **US$0.210/pc** pending exact DC; seller's minimum acceptable price unknown. Still far from a confirmed trial order.
- No confirmed PO, stock reservation, authenticity proof, receipt, or signed deal before this note.
- Communicate explicitly that trial-size quotes require new verification and secure payment/inspection terms. Never make buyer payment or order commitment without their authority.

## KPI governance
- Weekly: identify top RFQ bottleneck (buyer budget, physical stock, provenance, price, shipping, fee agreement).
- Every month: report completed GMV separately for USD and KRW, count verified completed orders, median completed ticket size, repeat-buyer count (only when signed customer identity data and event records are sufficient), recorded JBRO commission and bank-reconciled receipts.
- Avoid manufacturing metrics that data tables do not currently support. The dashboard currently does not claim repeat-buyer ratio or monthly revenue as measured fields.
- Trademarks/domain are not yet legally cleared: display name remains provisional pending clearance. No change to legal contracting entity or banking details.
