import unittest
from unittest.mock import patch
from automation import build
from demo_app import as_email, SAMPLES, DemoApp
import tkinter as tk


class DesktopTests(unittest.TestCase):
    def test_examples_and_stable_duplicate_key(self):
        for name, body in SAMPLES.items():
            with self.subTest(name=name):
                a, b = build(as_email(body)), build(as_email(body))
                self.assertEqual(a['request_id'], b['request_id'])
                self.assertEqual(a['status'], 'REVIEW_REQUIRED' if name == '정상 요청' else 'BLOCKED')

    def test_input_size_is_bytes(self):
        with self.assertRaises(ValueError):
            as_email('가' * 17000)

    def test_desktop_and_stale_input_guard(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = DemoApp(root)
            app.analyze()
            self.assertEqual(app.result['total'], 2068000)
            self.assertEqual(len(app.table.get_children()), 2)
            app.input.insert('end', '\n변경된 본문')
            with patch('demo_app.messagebox.showinfo') as info, patch('demo_app.filedialog.askdirectory') as picker:
                app.save()
                info.assert_called_once()
                picker.assert_not_called()
            app.sample.set('인쇄 조건 누락')
            app.load_sample()
            app.analyze()
            self.assertIsNone(app.result['total'])
            self.assertIn('보류', app.status.get())
        finally:
            root.destroy()


    def test_error_clears_previous_total_and_catalog_change_requires_review(self):
        from pathlib import Path
        root = tk.Tk()
        root.withdraw()
        try:
            app = DemoApp(root)
            app.analyze()
            self.assertEqual(app.result['total'], 2068000)
            app.input.delete('1.0', 'end')
            app.input.insert('1.0', '가' * 17000)
            with patch('demo_app.messagebox.showerror'):
                app.analyze()
            self.assertIsNone(app.result)
            self.assertEqual(app.totals.get(), '')
            self.assertEqual(len(app.table.get_children()), 0)
            with patch('demo_app.filedialog.askopenfilename', return_value=str(Path(__file__).parent / 'catalog.example.json')):
                app.select_catalog()
            self.assertIsNone(app.reviewed_body)
            self.assertIn('CUP-001', app.catalog_options['catalog'])
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
