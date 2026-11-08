"""Generate a reproducible offline validation bundle; no model/API calls."""
import argparse
import copy
import json
from pathlib import Path
from automation import export
from ai_extract import quote_from_extraction
from catalog import load_catalog, strict_json_loads


def verify(destination):
    base = Path(__file__).parent
    catalog = load_catalog(base / 'catalog.example.json')
    body = (base / 'ai_sample.txt').read_text(encoding='utf-8')
    extraction = strict_json_loads((base / 'ai_fixture.json').read_text(encoding='utf-8'))
    missing = copy.deepcopy(extraction)
    missing['items'].pop()
    duplicate = copy.deepcopy(extraction)
    duplicate['items'].append(copy.deepcopy(duplicate['items'][0]))
    cases = [('normal', body, extraction, 'REVIEW_REQUIRED', 2519000),
             ('omitted_item', body, missing, 'BLOCKED', None),
             ('duplicate_item', body, duplicate, 'BLOCKED', None),
             ('conflicting_date', body + '\n변경 희망일 2026-12-01', extraction, 'BLOCKED', None)]
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    summary = []
    for name, source, extracted, status, total in cases:
        result = quote_from_extraction(source, extracted, catalog)
        if (result['status'], result['total']) != (status, total):
            raise AssertionError('검증 실패: ' + name)
        result['processing_note'] = '직접 작성한 AI 응답 예제의 오프라인 검증. 실제 AI 호출 없음.'
        export(result, destination / name)
        summary.append({'case': name, 'status': result['status'], 'total': result['total'], 'passed': True})
    (destination / 'verification_results.json').write_text(json.dumps({'live_api_called': False, 'cases': summary}, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.out), ensure_ascii=False))
