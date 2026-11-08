import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from automation import build
from catalog import load_catalog
from ai_extract import quote_from_extraction, request_payload, extract_live

BASE = Path(__file__).parent


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(BASE / 'catalog.example.json')
        self.body = (BASE / 'ai_sample.txt').read_text(encoding='utf-8')
        self.extracted = json.loads((BASE / 'ai_fixture.json').read_text(encoding='utf-8'))

    def test_fixture_calculation(self):
        result = quote_from_extraction(self.body, self.extracted, self.catalog)
        self.assertEqual(result['total'], 2519000)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertFalse(result['automatic_send'])

    def test_hallucination_and_uncertainty_block(self):
        for key, value in [('quantity', 600), ('product_code', 'FAKE-001'), ('printing', '2도'), ('evidence', '架空の文章'), ('needs_review', True)]:
            with self.subTest(key=key):
                extracted = copy.deepcopy(self.extracted)
                extracted['items'][0][key] = value
                result = quote_from_extraction(self.body, extracted, self.catalog)
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertIsNone(result['total'])

    def test_unresolved_and_false_date_block(self):
        for change in [{'unresolved': ['포장 확인 필요']}, {'requested_delivery': '2026-12-01'}]:
            extracted = {**self.extracted, **change}
            self.assertEqual(quote_from_extraction(self.body, extracted, self.catalog)['status'], 'BLOCKED')

    def test_custom_catalog_and_date_not_product(self):
        raw = 'Content-Type: text/plain; charset=utf-8\n\nCUP-001 300개 인쇄: 없음\n납기: 2026-11-30'
        result = build(raw, catalog=self.catalog['products'], catalog_id=self.catalog['id'])
        self.assertEqual(result['net'], 1110000)

    def test_invalid_catalog_rejected(self):
        for mutation in [{'vat_mode': 'inclusive'}, {'products': {'CUP-001': {'name': '컵', 'tiers': [[300, 100], [100, 90]], 'setup': 0, 'print_each': 0}}}]:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'bad.json'
                path.write_text(json.dumps({**self.catalog, **mutation}), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_catalog(path)

    def test_payload_privacy_and_strict_format(self):
        payload = request_payload(self.body, self.catalog, 'test-model')
        self.assertFalse(payload['store'])
        self.assertTrue(payload['text']['format']['strict'])
        self.assertNotIn('tiers', payload['input'])
        self.assertNotIn('3700', payload['input'])

    def test_live_guards_before_network(self):
        with patch('ai_extract.urlopen') as network:
            with self.assertRaises(ValueError):
                extract_live(self.body, self.catalog, 'test-model')
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
                extract_live(self.body, self.catalog, 'test-model', allow_external=True, synthetic_input=True)
            network.assert_not_called()

    def test_live_response_shape_with_mock_transport(self):
        response = {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(self.extracted)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-test-key'}), patch('ai_extract.urlopen') as network:
            network.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
            result = extract_live(self.body, self.catalog, 'test-model', allow_external=True, synthetic_input=True)
            self.assertEqual(result, self.extracted)
            self.assertEqual(network.call_args.args[0].full_url, 'https://api.openai.com/v1/responses')


if __name__ == '__main__':
    unittest.main()
