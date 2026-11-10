# JBRO Speed-First Deal Execution Playbook
Version: 2026-11-10
Owner: Jbro Capital Ltd.
Status: operational policy / proposed internal SLAs (not a public guarantee)

## Principle
Every active deal must advance to an evidenced milestone or carry a named blocker, owner, and next action. Speed means decision velocity, not indiscriminate follow-up.

## Stage SLAs (Korea business hours, test targets)
- Initial response to new qualified inbound: within 2 business hours.
- RFQ qualification: within 4 business hours.
- First supplier/buyer candidate assessment: within 24 business hours.
- Comparable quote, evidence-based progress report, or explicit no-fit: within 48 business hours.
- Qualified deal: next owner and time-bound milestone assigned before handoff.
- Prospective customer or supplier reply windows are not under JBRO control; no delivery, inventory, or price guarantee is implied.

## Minimum viable information
Source Rescue: buyer authority, precise PN/specs, quantity, acceptable condition, target price/budget, ship-to, delivery, payment terms, compliance.
Surplus Rescue: lawful ownership/authority, items and serials, condition and photos if authorized, location, quantity, asking guidance, available dates, inspection and removal terms.
No signed fee protection or lawful authority -> do not disclose counterparty identities.

## Parallel workflow
T+0: assign owner, log received_at, stage, next_action, next_due_at, consent/confidentiality requirements.
T+2h: acknowledge, request ALL missing deal-critical details in one batch.
T+4h: score qualified intent; begin evidence-based parallel candidate search.
T+24h: candidate shortlist or transparent blocker and fallback.
T+48h: standardized comparable quote/progress update; propose one unambiguous next action.
Then: fee agreement + counterparty registration before named introductions; confirm written commercial terms; monitor contract/PO, shipment/inspection, settlement, received fee separately.

## Aging policy measured from last substantive advance, not last email
0-24h: normal; 24-48h: investigate; 48-72h: unblock/re-route; >72h: founder decision to advance, park, or abandon.
Do NOT chase a supplier repeatedly while awaiting an agreed response; seek alternative buyers/suppliers instead.

## Daily Deal Velocity Dashboard
For every live deal track:
deal_id, customer, segment, source, received_at, last_substantive_milestone_at, stage_entered_at, next_action, owner, next_due_at, blocker, blocker_owner, verified_Rfq, quote_received, fee_terms_signed, PO_signed, fee_cash_received, status, risk/compliance.
Metrics: median first response time, RFQ-to-quote time, stage dwell time, stalled-deals share (>48h), 7-day stage advancement %, quote-to-order %, days to fee cash receipt, and lost-deal reasons.
Separate outreach counts from validated deal progress and money received.

## Active pilots
MET: finalize project-specific 5% + VAT separate fee, condition/warranty/returns, then live inventory + named buyer matching.
SunSpike HDD: confirm quantities/condition/target landed price once; compare parallel supplier quotes; don't assume PO.
RuiReach: exact TI PN evidence, authentic/traceable inventory, stock/lead time.
Retemz: reflect accepted 6-month protection and 10-business-day settlement in executable agreement before introductions.
Monks: confirm buyer identity protection and written registration plus project fee sharing before outreach; check local regulated intermediary rules.

## Automation and customer messaging
Use existing Gmail threads and avoid duplicative follow-up. AI may triage and draft but must not make false claims or silently commit to price/availability. Automations can report aging and next actions; human review/authorization required for external commitments.

## Weekly improvement loop
Identify top three delays by stage and remove one bottleneck per week. A/B test simultaneous quotes vs serial quotes with control for product mix; record conversion and time-to-close. Do not claim mathematically exponential conversion decay without measurement.
