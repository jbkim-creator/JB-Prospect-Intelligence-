# JBRO AI Visibility — Controlled API Sampling

Status: **integration source ready; no paid API calls have been executed**.

This script collects OpenAI **Responses API with web_search** results. It does **not** measure the ChatGPT consumer UI, Gemini UI, or Perplexity UI. Label every report accordingly.

## Safety and cost
- Standard invocation is **dry-run** and makes no requests.
- Actual billable calls require both `--execute` and `--confirm-paid-calls YES`.
- Uses `OPENAI_API_KEY` only from the environment on the operator's secure machine.
- Never put the key in browser code, GitHub, ChatGPT messages, or a public Render static site.
- At most 9 **Responses API requests** per script execution; default 3, one question for each pilot company. A single model response may make multiple web-search tool calls, so this is **not** a cap on search-tool charges.
- No automatic retries. The script stops on a failed API request.
- **This is a per-execution request cap, not a true billing budget cap**. Search tools and token usage can vary; set a provider-side monthly project spend limit.
- Avoid patient records, sensitive supplier information, and other personal or confidential information in prompts.
- Output JSON contains search answer text and citations; keep it in a private location, not a public repository.

## Offline parser self-test (zero API requests)

```bash
python3 tools/collect_openai_web_search.py --self-test
```

Self-test uses **synthetic** content and must never be included as customer evidence. It checks the response-parser logic, not live API compatibility. Confirm model availability, platform billing controls, and terms before live measurement.

## Dry run

```bash
python3 tools/collect_openai_web_search.py
```

## Explicitly authorize up to 3 billable requests

```bash
export OPENAI_API_KEY="your_key_in_secure_terminal_environment"
python3 tools/collect_openai_web_search.py --execute --confirm-paid-calls YES --max-calls 3 --output evidence-2026-11-16.json
```

Check current OpenAI pricing and model availability before running:
https://developers.openai.com/api/docs/pricing
https://developers.openai.com/api/docs/guides/tools-web-search

## Evidence workflow
1. Confirm prompts and company identities with the client. Do **not** include a target brand name in the search prompt.
2. Run the script with 3 requests (1 question each: Evita Clinic, Curious Korea, HY Corporation).
3. Check returned answers, citations, successful `web_search_call` traces, question coverage, response IDs and API usage. The script now discards an answer without a search-call trace.
4. Visit `/report.html` and import generated JSON, then select each company.
5. The collector leaves recommendation verdict `unreviewed`; have a human inspect full answer before classifying recommendation/mention vs mere citation.
6. Save PDFs only after reviewer approval, with API origin and observed date shown explicitly.
7. Extend to 9 total calls only if pilot quality and cost justify it.

## Reporting guardrails
- "Appeared in OpenAI Responses web_search answer" is not the same as "recommended by ChatGPT/Gemini/Perplexity users."
- Never infer total AI search share from 1-3 samples.
- No fake values when answer text or citations are absent.
- A successful response does not imply guaranteed visibility or revenue lift.

## Engineering constraints
This is a local CLI, not a publicly exposed endpoint. The Render static website cannot safely hold provider credentials or independently run paid AI API workflows. For fully automatic scheduling, a secured backend, provider secret store, customer access controls, billing approvals, and audit logs are prerequisites.

## On-demand GitHub Actions pilot (no credentials in the repo)

An isolated manual workflow lives at `.github/workflows/ai-visibility-pilot.yml` on the feature branch.

- Default manual input is `execute_paid_calls: false`, which runs offline tests and a dry run only.
- Billable execution requires the operator to select true, choose 1 or 3 requests, and separately store `OPENAI_API_KEY` and a strong independent `EVIDENCE_ENCRYPTION_PASSWORD` as Actions repository secrets. Both must exist before any billable requests.
- The workflow never runs on a schedule or on a code push.
- This repository is public. Evidence is **encrypted before artifact upload**, then the unencrypted runner file is deleted. The encrypted artifact expires after one day. Do not publish the encryption password or raw evidence.
- GitHub's workflow_dispatch UI generally requires the workflow to exist on the default branch; it may not be available from this feature branch until an authorized merge or an isolated default-branch workflow addition.
- Before any billable run, configure a provider-side usage limit and confirm GitHub Actions artifact access controls.

This workflow does not bypass API authentication and is not evidence of a paid API call having run.

## Default-branch manual workflow (safe entry point)

The **manual-only** workflow is available at [GitHub Actions / JBRO AI Visibility safe pilot](https://github.com/jbkim-creator/JB-Prospect-Intelligence-/actions/workflows/jbro-ai-visibility-manual.yml). It checks out the isolated `feature/ai-visibility-mvp` branch and does not merge the app into `main`.

1. In GitHub repo Settings → Secrets and variables → Actions, configure `OPENAI_API_KEY` (API project key) and `EVIDENCE_ENCRYPTION_PASSWORD` (long unique passphrase). Do not put either value in chat, code, or a form hosted by the public website.
2. In Actions → **JBRO AI Visibility safe pilot** → Run workflow, leave `approve_paid_calls` unchecked to perform offline tests / dry run first. This has no OpenAI API charge.
3. When the dry run and tests succeed and a project-level usage limit is set, check `approve_paid_calls` and select **1** request for the first paid sample.
4. Download the `ai-visibility-evidence-encrypted` artifact within one day. It contains only `evidence-openai.json.enc` (encrypted). Decrypt locally with the same passphrase using:

```bash
export EVIDENCE_ENCRYPTION_PASSWORD='your private password'
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in evidence-openai.json.enc -out evidence-openai.json -pass env:EVIDENCE_ENCRYPTION_PASSWORD
python3 tools/validate_evidence.py evidence-openai.json
```

5. Open `/report.html` and import the JSON, review full answers and record reviewer name + time in `/collect.html`; export updated evidence if desired. **Never upload plaintext client evidence to a public repository.**

This workflow is opt-in only and has not yet made any paid API requests.
