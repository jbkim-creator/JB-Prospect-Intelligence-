import unittest
from unittest.mock import Mock
from flask import Flask
import closing_desk

class ClosingDeskTests(unittest.TestCase):
    def base(self):
        return dict(deal_key="TEST-001",sector="semiconductor",title="Synthetic RFQ",
                    stage="negotiation",source_ref="test-only-reference",blocker="Need quote",
                    next_action="Request quote",due_date="2026-12-01",fee_state="proposed",
                    fee_evidence="",handoff_ref="",currency="USD",indicative_value="1234.56")
    def check_invalid(self, **changes):
        data=self.base()
        data.update(changes)
        with self.assertRaises(ValueError):
            closing_desk.normalize(data)
    def test_amount_precision(self):
        self.assertEqual(closing_desk.normalize(self.base())["indicative_value_minor"],123456)
        self.check_invalid(currency="KRW",indicative_value="123.45")
        self.check_invalid(currency="EUR")
        self.check_invalid(indicative_value="0")
        self.check_invalid(currency="")
    def test_evidence_gates(self):
        self.check_invalid(stage="fee_agreed")
        self.check_invalid(fee_state="written_agreement")
        self.check_invalid(fee_state="waived")
        self.check_invalid(stage="handoff")
        self.check_invalid(due_date="")
        self.check_invalid(due_date="2026-02-30")
        self.check_invalid(revision=True)
        self.check_invalid(deal_key="invalid key")
        self.check_invalid(blocker="")
        data=self.base()
        data.update(stage="fee_agreed",fee_state="written_agreement",fee_evidence="synthetic signed agreement ref")
        self.assertEqual(closing_desk.normalize(data)["stage"],"fee_agreed")
    def test_unknown_value_and_hold(self):
        data=self.base()
        data.update(currency="",indicative_value="",stage="on_hold",due_date="")
        result=closing_desk.normalize(data)
        self.assertIsNone(result["indicative_value_minor"])
        self.assertIsNone(result["due_date"])
    def test_unauthenticated_routes_never_touch_database(self):
        app=Flask(__name__)
        db=Mock(side_effect=AssertionError("DB must not be called"))
        closing_desk.init(app,db,lambda:False)
        c=app.test_client()
        self.assertEqual(c.get("/api/admin/closing-desk").status_code,401)
        self.assertEqual(c.post("/api/admin/closing-desk",json=self.base()).status_code,401)
        self.assertEqual(c.patch("/api/admin/closing-desk/1",json=self.base()).status_code,401)
        db.assert_not_called()
    def test_validation_before_db(self):
        app=Flask(__name__)
        db=Mock(side_effect=AssertionError("DB must not be called"))
        closing_desk.init(app,db,lambda:True)
        c=app.test_client()
        self.assertEqual(c.post("/api/admin/closing-desk",json={}).status_code,400)
        self.assertEqual(c.patch("/api/admin/closing-desk/1",json=self.base()).status_code,400)
        db.assert_not_called()

if __name__ == "__main__":
    unittest.main()
