#!/usr/bin/env python3
"""Offline preflight for JBRO AI Visibility evidence; no API requests."""
import argparse
import json
from pathlib import Path

VALID_ORIGINS = {'api_auto_capture', 'manual_direct_capture'}
VALID_VERDICTS = {'yes', 'no', 'ambiguous', 'unreviewed'}

def validate(doc):
    errors = []
    if not isinstance(doc, dict) or doc.get('schema') != 'jbro-ai-visibility-evidence-v1':
        return ['Invalid evidence schema']
    records = doc.get('records')
    if not isinstance(records, list) or not records:
        return ['Missing nonempty records list']
    seen = set()
    for i, item in enumerate(records, 1):
        at = f'record {i}'
        if not isinstance(item, dict):
            errors.append(f'{at}: not an object')
            continue
        for field in ('customer','prompt','answer','provider','model','observed_at','collection_method'):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f'{at}: missing {field}')
        if item.get('collection_method') not in VALID_ORIGINS:
            errors.append(f'{at}: unknown collection method')
        if item.get('recommended') not in VALID_VERDICTS:
            errors.append(f'{at}: invalid recommendation verdict')
        urls = item.get('citation_urls')
        if not isinstance(urls, list) or any(not isinstance(url, str) or not url.startswith(('https://','http://')) for url in urls):
            errors.append(f'{at}: malformed citations')
        sid = item.get('session_id')
        if not isinstance(sid, str) or not sid.strip():
            errors.append(f'{at}: missing session ID')
        key = (item.get('customer'), item.get('provider'), sid, item.get('prompt'))
        if key in seen:
            errors.append(f'{at}: duplicate customer/provider/session/question')
        seen.add(key)
        if item.get('collection_method') == 'api_auto_capture':
            calls = item.get('observed_web_search_calls', 0)
            if not isinstance(calls, int) or isinstance(calls, bool) or calls < 1:
                errors.append(f'{at}: API capture missing web_search_call trace')
            statuses = item.get('web_search_statuses', [])
            if not isinstance(statuses, list) or 'completed' not in statuses:
                errors.append(f'{at}: no completed web-search call evidence')
            if item.get('recommended') != 'unreviewed':
                errors.append(f'{at}: automated recommendation judgment must start unreviewed')
    return errors

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('json_file', type=Path)
    args = p.parse_args()
    try:
        doc = json.loads(args.json_file.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        p.exit(2, f'FAIL: cannot open JSON: {exc}\n')
    errors = validate(doc)
    if errors:
        for e in errors:
            print('FAIL:', e)
        return 1
    print('PASS: evidence structural preflight; provenance still requires human verification')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
