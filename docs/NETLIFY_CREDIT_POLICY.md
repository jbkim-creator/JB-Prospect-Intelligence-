# Netlify free-tier credit preservation policy

Applies to this Netlify-hosted static website. Keep the public production site available while reducing billed production deploys.

## Required release workflow

1. Make changes on feature branches, not directly on `main`.
2. Open a pull request against `main`. Review the **Deploy Preview** link, including lead form submission and email notification when those features are affected.
3. Batch related, tested changes into one release rather than merging each small edit.
4. Merge into `main` only when ready to publish. **Every successful production deploy costs 15 credits** on credit-based billing. Preview/branch deploys cost zero deploy credits, although traffic and other metered usage may still count.
5. Before merging, check Netlify team's **Usage & billing → Credit usage**. Preserve headroom for important releases and customer traffic.
6. If development needs a temporary freeze, do not toggle **Stopped builds** if previews are needed: stopped builds disables production, preview, and branch builds alike.

## Netlify dashboard configuration (requires Netlify account access)

- Keep **Deploy Previews** enabled for pull requests.
- Review **Project configuration → Developer settings → Continuous deployment**; verify the production branch is `main` and do not publish unreviewed feature commits directly to `main`.
- Optional during periods without planned releases: manage production release frequency through GitHub pull-request approvals, not a blanket 'stop builds' switch.
- Check credit consumption by category: production deploys, bandwidth, web requests and any compute/AI inference. Build policy alone does not prevent traffic charges.

## Do not do

- Do not make automatic `main` commits just to adjust deployment settings.
- Do not add a blanket `[build] ignore` rule that can silently prevent legitimate production releases.
- Do not disable forms or replace an already working site just to save deploy credits.

Official docs:
- https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/how-credits-work/
- https://docs.netlify.com/deploy/deploy-types/deploy-previews/
- https://docs.netlify.com/build/configure-builds/stop-or-activate-builds/
