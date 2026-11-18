from datetime import date
from decimal import Decimal
from unittest.mock import Mock
import unittest
from flask import Flask
import matching

class MatchTests(unittest.TestCase):
    def line(self,side="buy",**overrides):
        data=dict(line_key="TEST-"+side.upper(),side=side,mpn="TPS92662AQPHPRQ1",
                  manufacturer="Texas Instruments",quantity="1000",currency="USD",
                  unit_price="1.000001",basis="EXW Korea; fee excluded",
                  verification="document_reviewed",valid_until="2026-12-01",
                  source_ref="test-only",case_key="TEST-001")
        data.update(overrides)
        return matching.normalize(data)
    def test_exact(self):
        b,s=self.line(),self.line("sell")
        self.assertEqual(matching.classify(b,s,date(2026,11,18))["status"],"commercial_candidate")
        self.assertIsNone(matching.classify(b,self.line("sell",mpn="TPS92662AQPHPR"),date(2026,11,18)))
        self.assertIsNone(matching.classify(b,self.line("sell",manufacturer="OTHER"),date(2026,11,18)))
    def test_uncertainty(self):
        b,s=self.line(quantity="",valid_until="",verification="reported"),self.line("sell",currency="",unit_price="")
        m=matching.classify(b,s,date(2026,11,18))
        self.assertEqual(m["status"],"review_required")
        self.assertIsNone(m["overlap_quantity"])
        self.assertIn("price_missing",m["flags"])
        self.assertIn("buyer_validity_unknown",m["flags"])
    def test_price_basis_expiry(self):
        b=self.line()
        for s,flag in [
            (self.line("sell",unit_price="1.000002"),"price_gap"),
            (self.line("sell",basis="FOB"),"price_basis_not_comparable"),
            (self.line("sell",currency="KRW"),"currency_mismatch"),
            (self.line("sell",quantity="10"),"partial_quantity"),
        ]:
            self.assertIn(flag,matching.classify(b,s,date(2026,11,18))["flags"])
        self.assertEqual(matching.classify(b,self.line("sell",valid_until="2026-11-17"),date(2026,11,18))["status"],"expired")
    def test_validation(self):
        for changes in [dict(mpn="AB CD"),dict(quantity="-1"),dict(currency=""),dict(unit_price="0"),dict(valid_until="2026-02-30"),dict(unit_price="1.0000001")]:
            with self.assertRaises(ValueError): self.line(**changes)
        self.assertEqual(self.line()["unit_price"],Decimal("1.000001"))
    def test_auth_guard(self):
        app=Flask(__name__)
        db=Mock(side_effect=AssertionError("no database"))
        matching.init(app,db,lambda:False)
        c=app.test_client()
        for method,path in [("get","lines"),("post","lines"),("get","candidates"),("post","lines/1/archive")]:
            self.assertEqual(getattr(c,method)("/api/admin/matching/"+path).status_code,401)
        db.assert_not_called()

if __name__=="__main__": unittest.main()
