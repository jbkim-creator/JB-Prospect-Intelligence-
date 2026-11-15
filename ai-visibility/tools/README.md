# JBRO AI Visibility — Controlled API Sampling

Status: **integration source ready; no paid API calls have been executed**.

This script collects OpenAI **Responses API with web_search** results. It does **not** measure the ChatGPT consumer UI, Gemini UI, or Perplexity UI. Label every report accordingly.

## Safety and cost
- Standard invocation is **dry-run** and makes no requests.
- Actual billable calls require both `--execute` and `--confirm-paid-calls YES`.
- Uses `OPENAI_API_KEY` only from the environment on the operator's secure machine.
- Never put the key in browser code, GitHub, ChatGPT messages, or a public Render static site.
- At most 9 calls per script execution; default 3, one question for each pilot company.
- No automatic retries. The script stops on a failed API request.
- **This is a per-execution request cap, not a true billing budget cap**. Search tools and token usage can vary; set a provider-side monthly project spend limit.
- Avoid patient records, sensitive supplier information, and other personal or confidential information in prompts.
- Output JSON contains search answer text and citations; keep it in a private location, not a public repository.

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
3. Check returned answers, citations, question coverage, response IDs and API usage.
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
