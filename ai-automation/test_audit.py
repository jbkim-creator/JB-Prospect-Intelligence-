"""Adversarial regression cases found during pre-pilot review."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from automation import build
from catalog import load_catalog
from ai_extract import quote_from_extraction

BASE = Path(__file__).parent


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(BASE / 'catalog.example.json')
        self.body = (BASE / 'ai_sample.txt').read_text(encoding='utf-8')
        self.extracted = json.loads((BASE / 'ai_fixture.json').read_text(encoding='utf-8'))

    def test_omitted_ai_item_must_block_total(self):
        self.extracted['items'].pop()
        self.assertIsNone(quote_from_extraction(self.body, self.extracted, self.catalog)['total'])

    def test_duplicate_ai_item_must_block_total(self):
        self.extracted['items'].append(copy.deepcopy(self.extracted['items'][0]))
        self.assertIsNone(quote_from_extraction(self.body, self.extracted, self.catalog)['total'])

    def test_conflicting_dates_must_block(self):
        self.assertIsNone(quote_from_extraction(self.body + '\n변경 희망일 2026-12-01', self.extracted, self.catalog)['total'])

    def test_conflicting_printing_must_block(self):
        raw = 'Content-Type: text/plain; charset=utf-8\n\nDEMO-T01 300개 인쇄: 없음 인쇄: 2도\n납기: 2026-11-30'
        self.assertIsNone(build(raw)['total'])

    def test_cross_item_evidence_must_block(self):
        self.extracted['items'][0]['quantity'] = 500
        self.extracted['items'][0]['evidence'] = '\n'.join(self.body.splitlines()[:2])
        self.assertIsNone(quote_from_extraction(self.body, self.extracted, self.catalog)['total'])

    def test_invalid_root_must_raise_value_error(self):
        with self.assertRaises(ValueError):
            quote_from_extraction(self.body, None, self.catalog)

    def test_catalog_duplicate_key_must_reject(self):
        raw = json.dumps(self.catalog).replace('"currency": "KRW"', '"currency": "USD", "currency": "KRW"')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog.json'
            path.write_text(raw, encoding='utf-8')
            with self.assertRaises(ValueError):
                load_catalog(path)


if __name__ == '__main__':
    unittest.main()
