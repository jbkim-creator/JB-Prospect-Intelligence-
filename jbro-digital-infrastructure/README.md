# JBRO Digital Infrastructure — standalone website preview
This folder is an independent static website concept for **Jbro Capital Ltd.** No existing JB Prospect Intelligence files are changed.

## Current status
- Draft / unlaunched. Search engine indexing disabled with `noindex,nofollow`.
- English B2B landing page: finance intelligence, project research, Korea–APAC mapping, methodology, email contact.
- No live data submission, CRM integration, investor solicitation, payment processing, project catalogue, or confidential project details.
- No client reference or funding commitment is implied.

## Preview locally
Open `index.html` in a browser. No build tools or dependencies needed.

## Deployment
Recommended: create a dedicated GitHub repository (e.g. `jbro-digital-infrastructure`) then configure a dedicated Netlify site. Copy this folder to the new repository root.
If previewing from this existing JB Prospect Intelligence repo, **do not change its production publish directory or deploy the feature branch to its live Netlify site**.

## Next checklist
1. Confirm company legal name and corporate website domain.
2. Legal/compliance review of public services copy and footer.
3. Add a privacy notice before using hosted forms or analytics.
4. Host reviewed PDF profile and sample reports in dedicated assets folder only after approved for public distribution.
5. Configure secure CRM form or Netlify Forms, spam protection and consent, plus a verified recipient.
6. Test responsive views, forms, link tracking and accessibility; remove noindex only on public launch.

## Current implementation status — 2026-11-08
- `index.html`: institutional services, research methodology, institutional enquiry form, privacy consent checkbox.
- `privacy.html`: preliminary privacy notice (**legal review required before receiving personal data**).
- `thank-you.html`: after-submit thank-you page.
- `netlify.toml`: static site settings and search-engine noindex headers.
- PDFs are not in this GitHub folder yet. Do not show broken downloads. The approved public PDFs need to be reviewed and copied to a dedicated site during the deploy step.

## Netlify deployment checklist (separate site, not the existing JB Prospect site)
1. Create a separate GitHub repository for the JBRO site or configure a distinct Netlify project pointing to the dedicated repository.
2. Copy the contents of this directory to the standalone site's publish root.
3. In Netlify settings, set build command empty and publish directory `.`.
4. Enable Netlify Forms. The form name is `jbro-institutional-enquiry`; recipient notification email must be configured manually.
5. Before enabling submissions, have privacy/foreign-transfer/retention text reviewed and approved for actual hosting jurisdiction.
6. Test one non-sensitive contact submission; confirm form entry, spam routing, notification delivery and thank-you redirect.
7. Test desktop/mobile layouts, site links and the separate PDFs when approved.
8. Set domain, TLS/HTTPS and business email verification.
9. Remove `noindex` tags and the noindex header **only after** regulatory/privacy and factual publication approval.
10. Do not merge or replace the existing JB Prospect Intelligence production web root; this branch is solely an independent staging project.
