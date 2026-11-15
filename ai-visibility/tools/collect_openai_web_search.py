#!/usr/bin/env python3
"""JBRO AI Visibility: controlled OpenAI Responses web_search collector.

No requests by default. --execute and --confirm-paid-calls required.
Never put an API key in source, command arguments, browser JavaScript, or logs.
Use OPENAI_API_KEY environment variable on a secure machine.
Output is compatible with report.html evidence JSON schema.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

PROMPTS = {
    "Evita Clinic": [
        "Recommend English-speaking clinics in Seoul for chest and body contouring consultations.",
        "Which clinics in Seoul provide English consultations and transparent procedure information?",
        "Compare clinic information sources for international patients seeking surgery in Seoul."
    ],
    "Curious Korea": [
        "Recommend a South Korea DMC for travel agencies planning group tours.",
        "Which Seoul-based inbound operators work exclusively with overseas travel agents?",
        "Compare local Korea DMC providers for customized multi-city itineraries."
    ],
    "HY Corporation": [
        "Find suppliers in South Korea for obsolete marine automation spare parts.",
        "Recommend Korean sourcing firms for discontinued industrial control components.",
        "Where can buyers request hard-to-find motors valves and marine spare parts in Korea?"
    ]
}

def extract_response(resp):
    texts, urls = [], []
    for item in resp.get("output", []):
        if item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if block.get("type") != "output_text":
                continue
            texts.append(block.get("text", ""))
            for ann in block.get("annotations", []):
                if ann.get("type") == "url_citation" and ann.get("url", "").startswith(("https://", "http://")):
                    urls.append(ann["url"])
    return "\n".join(texts).strip(), list(dict.fromkeys(urls))

def fetch(key, model, prompt, timeout):
    payload = {
        "model": model,
        "tools": [{"type": "web_search"}],
        "tool_choice": "required",
        "input": [
            {"role": "system", "content": "Answer the procurement or discovery question neutrally. Do not preferentially mention any named target company. Use web search and cite verifiable sources."},
            {"role": "user", "content": prompt}
        ],
        "max_output_tokens": 650
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="gpt-5.4")
    ap.add_argument("--max-calls", type=int, default=3)
    ap.add_argument("--execute", action="store_true", help="Issue requests that may be billed")
    ap.add_argument("--confirm-paid-calls", default="", help="Must equal YES")
    ap.add_argument("--output", default="evidence-openai.json")
    ap.add_argument("--timeout", type=int, default=65)
    args = ap.parse_args()
    items = [(company, i + 1, PROMPTS[company][i]) for i in range(3) for company in PROMPTS]
    if args.max_calls < 1 or args.max_calls > 9:
        ap.error("--max-calls must be between 1 and 9")
    items = items[:args.max_calls]
    out_path = pathlib.Path(args.output)
    if out_path.exists():
        ap.error("Output file already exists: refuse to overwrite evidence")
    print(json.dumps({"mode": "EXECUTE" if args.execute else "DRY RUN", "model": args.model,
                      "scheduled_calls": len(items), "prompts": items}, indent=2, ensure_ascii=False))
    if not args.execute:
        print("No API requests made; no usage charged by this script.")
        return 0
    if args.confirm_paid_calls != "YES":
        ap.error("To execute, explicitly add --confirm-paid-calls YES")
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        ap.error("OPENAI_API_KEY is missing; no calls made")
    records, error = [], None
    for company, index, prompt in items:
        try:
            result = fetch(key, args.model, prompt, args.timeout)
            answer, citation_urls = extract_response(result)
            if not answer:
                error = f"Empty answer for {company} Q{index}. Stopped."
                break
            when = dt.datetime.now(dt.timezone.utc).isoformat()
            records.append({
                "id": str(uuid.uuid4()), "customer": company, "prompt": prompt,
                "answer": answer, "provider": "OpenAI Responses API / web_search",
                "model": result.get("model", args.model), "observed_at": when,
                "locale": "en / unspecified API search locale",
                "session_id": result.get("id", str(uuid.uuid4())),
                "recommended": "unreviewed",
                "citation_urls": citation_urls,
                "proof_ref": "Provider response id: " + result.get("id", "unavailable"),
                "captured_at": when,
                "collection_method": "api_auto_capture",
                "capture_origin": "api_auto_capture",
                "question_id": f"Q{index:02d}",
                "usage": result.get("usage", {})
            })
            print(f"Saved in memory: {company} Q{index} ({len(answer)} chars, {len(citation_urls)} citations)")
        except urllib.error.HTTPError as ex:
            error = f"HTTP {ex.code} at {company} Q{index}; stopped without retry"
            break
        except Exception as ex:
            error = f"{type(ex).__name__} at {company} Q{index}; stopped without retry"
            break
    if records:
        # Output uses the shared evidence schema but marks automated API capture explicitly.
        out = {"schema": "jbro-ai-visibility-evidence-v1",
               "source": "OpenAI Responses API with web_search (not ChatGPT UI)",
               "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
               "records": records, "error": error}
        with out_path.open("x", encoding="utf-8") as fp:
            json.dump(out, fp, indent=2, ensure_ascii=False)
        print(f"Saved {len(records)} records to {out_path}")
    if error:
        print("Stopped: " + error, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
