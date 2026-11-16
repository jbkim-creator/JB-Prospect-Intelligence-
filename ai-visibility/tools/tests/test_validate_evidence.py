import copy
import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from validate_evidence import validate

RECORD = dict(customer='Curious Korea',prompt='Find Korea DMC',answer='An actual response text',provider='OpenAI Responses API / web_search',model='gpt-6-luna',observed_at='2026-11-16T01:00:00+00:00',collection_method='api_auto_capture',recommended='unreviewed',citation_urls=['https://example.org'],session_id='resp_test',observed_web_search_calls=1)

class PreflightTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(dict(schema='jbro-ai-visibility-evidence-v1',records=[RECORD])), [])
    def test_missing_search(self):
        x=copy.deepcopy(RECORD); x['observed_web_search_calls']=0
        self.assertTrue(any('web_search_call' in e for e in validate(dict(schema='jbro-ai-visibility-evidence-v1',records=[x]))))
    def test_fake_recommendation_without_review(self):
        x=copy.deepcopy(RECORD); x['recommended']='yes'
        self.assertTrue(any('unreviewed' in e for e in validate(dict(schema='jbro-ai-visibility-evidence-v1',records=[x]))))
    def test_duplicate(self):
        x=dict(schema='jbro-ai-visibility-evidence-v1',records=[RECORD,copy.deepcopy(RECORD)])
        self.assertTrue(any('duplicate' in e for e in validate(x)))
    def test_no_records(self):
        self.assertTrue(validate(dict(schema='jbro-ai-visibility-evidence-v1',records=[])))
    def test_malformed_url(self):
        x=copy.deepcopy(RECORD);x['citation_urls']=['javascript:alert(1)']
        self.assertTrue(any('citation' in e for e in validate(dict(schema='jbro-ai-visibility-evidence-v1',records=[x]))))

if __name__ == '__main__':unittest.main()
