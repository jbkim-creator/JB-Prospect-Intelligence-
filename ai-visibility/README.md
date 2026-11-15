# JBRO AI Visibility — Pilot MVP

Status: pre-deployment prototype (no paid API calls, no auto-deploy).

## Pilot scope
- Korean B2B/industrial-export positioning and inquiry landing page
- Browser-only analysis of manually collected LLM responses (tab-separated text)
- Brand mention percentage by platform, competitor comparison
- JSON evidence export
- Clearly labeled synthetic demo, *not* live LLM results

## Input specification
One record per line, tab-separated:
platform<TAB>buyer question<TAB>full answer text<TAB>collection date (optional)
Keep original evidence separately with access/terms in mind. Do not paste confidential or personal information.

## Limitations
Case-insensitive substring match only. Does not check semantics, citations, sentiment, answer authenticity or statistical significance. No AI platform integration, database, account or payment processing.

## Go-to-market
Target: Korea-based component distributors, machinery manufacturers, industrial exporters.
Offer: KRW 290,000 once for 30 buyer-intent questions; KRW 490,000/month monitoring, with written scope and VAT separately.
Pilot success gate: 3 paid diagnostics and >= 2 confirmed monthly monitoring conversions before automation investment.
No guarantees of ranking, referrals or lead volume.

## Deployment
Deploy branch `feature/ai-visibility-mvp`, publish path `ai-visibility`, build command `echo static` to an isolated Render static site. Disable auto-deploy to avoid unnecessary production deployments. Confirm service pricing before creating a new Render service.

## Next engineering steps
1. Prompt library and controlled collection form with source/date/model metadata.
2. Repeat observations per prompt/model; track confidence and variation.
3. Exact-name/entity match disambiguation and citations.
4. Customer authentication, segregated projects and secure evidence storage.
5. Optional paid API integrations only after budget approval.
