import tempfile
import unittest
from pathlib import Path
from automation import build, run, csv_safe


class PilotTests(unittest.TestCase):
    def raw(self, body):
        return 'Message-ID: <test@example.invalid>\nContent-Type: text/plain; charset=utf-8\n\n' + body

    def test_tier_and_tax(self):
        r = build(self.raw('DEMO-T01 300개 인쇄: 1도\nDEMO-P01 500개 인쇄: 없음\n납기: 2026-11-30'))
        self.assertEqual((r['net'], r['vat'], r['total']), (1880000, 188000, 2068000))
        self.assertFalse(r['automatic_send'])
        self.assertEqual(r['status'], 'REVIEW_REQUIRED')

    def test_missing_and_ambiguous(self):
        for body in ['DEMO-T01 10개 인쇄: 없음', 'DEMO-T01 100개 300개 인쇄: 없음', '텀블러 300개', 'DEMO-X99 300개 인쇄: 없음', 'DEMO-T01 300개']:
            with self.subTest(body=body):
                r = build(self.raw(body))
                self.assertEqual(r['status'], 'BLOCKED')
                self.assertIsNone(r['total'])

    def test_no_partial_total(self):
        r = build(self.raw('DEMO-T01 300개 인쇄: 없음\n텀블러 500개\n납기: 2026-11-30'))
        self.assertIsNone(r['total'])

    def test_reply_ignored(self):
        r = build(self.raw('DEMO-T01 300개 인쇄: 없음\n납기: 2026-11-30\n> DEMO-P01 500개 인쇄: 없음'))
        self.assertEqual(len(r['items']), 1)

    def test_invalid_date(self):
        r = build(self.raw('DEMO-T01 300개 인쇄: 없음\n납기: 2026-99-99'))
        self.assertEqual(r['status'], 'BLOCKED')

    def test_csv_injection(self):
        for x in ['=HYPERLINK("bad")', ' +SUM(A1)', '@cmd', '-1']:
            self.assertTrue(csv_safe(x).startswith("'"))

    def test_deduplicate_and_exports(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'input.eml'
            p.write_text(self.raw('DEMO-T01 300개 인쇄: 없음\n납기: 2026-11-30'), encoding='utf-8')
            output, _ = run(p, Path(d) / 'out')
            self.assertEqual({x.name for x in output.iterdir()}, {'quote.json', 'quote.html', 'order.csv'})
            with self.assertRaises(ValueError):
                run(p, Path(d) / 'out')


if __name__ == '__main__':
    unittest.main()
