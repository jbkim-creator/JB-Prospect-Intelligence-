"""Offline security and parsing tests for AI Visibility web_search collector.

Run from project root:
python3 -m unittest discover -s tools/tests -v
No network, provider credentials or third-party packages needed.
"""
import importlib.util
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "tools" / "collect_openai_web_search.py"
spec = importlib.util.spec_from_file_location("jbro_collector", COLLECTOR)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CollectorTests(unittest.TestCase):
    def test_extract_text_and_citations(self):
        fixture = {"output": [
            {"type":"web_search_call","status":"completed"},
            {"type":"message","content":[{"type":"output_text",
                "text":"Supplier comparison with sources.",
                "annotations":[
                    {"type":"url_citation","url":"https://example.com/a"},
                    {"type":"url_citation","url":"https://example.com/a"},
                    {"type":"url_citation","url":"javascript:alert(1)"}
                ]}]}
        ]}
        text, citations = mod.extract_response(fixture)
        self.assertEqual(text,"Supplier comparison with sources.")
        self.assertEqual(citations,["https://example.com/a"])

    def test_empty_response(self):
        text, citations = mod.extract_response({"output":[{"type":"web_search_call","status":"completed"}]})
        self.assertEqual(text,"")
        self.assertEqual(citations,[])

    def test_offline_self_test(self):
        p = subprocess.run([sys.executable,str(COLLECTOR),"--self-test"],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("PASS:",p.stdout)

    def test_default_is_dry_run(self):
        p = subprocess.run([sys.executable,str(COLLECTOR)],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("DRY RUN",p.stdout)
        self.assertIn("No API requests made",p.stdout)

    def test_cannot_charge_without_explicit_confirmation(self):
        p = subprocess.run([sys.executable,str(COLLECTOR),"--execute","--max-calls","1"],
                           capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("--confirm-paid-calls YES",p.stderr)

    def test_strict_request_limit(self):
        p = subprocess.run([sys.executable,str(COLLECTOR),"--max-calls","10"],
                           capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("between 1 and 9",p.stderr)

if __name__=="__main__":
    unittest.main()
