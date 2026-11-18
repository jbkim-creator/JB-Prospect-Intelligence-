from datetime import date
from unittest.mock import Mock
import unittest
from flask import Flask
import sales_queue

class SalesQueueTests(unittest.TestCase):
    def case(self, **changes):
        c=dict(deal_key="TEST-001",title="Test",sector="semiconductor",stage="negotiation",due_date=date(2026,11,18),fee_state="proposed",blocker="Verify",next_action="Review",source_ref="test-only",revision=1)
        c.update(changes)
        return c
    def test_priority(self):
        result=sales_queue.prioritize(self.case(),{"exact_pairs":1},date(2026,11,18))
        self.assertEqual(result["score"],88)
        self.assertEqual(result["priority"],"urgent")
        self.assertFalse(result["dispatch_permitted"])
    def test_overdue_and_closed(self):
        result=sales_queue.prioritize(self.case(),{},date(2026,11,19))
        self.assertIn("overdue",result["reasons"])
        for stage in ("lost","on_hold","handoff"):
            self.assertIsNone(sales_queue.prioritize(self.case(stage=stage),{},date(2026,11,19)))
    def test_normal(self):
        result=sales_queue.prioritize(self.case(sector="industrial",stage="qualified",due_date=date(2026,12,1)),{},date(2026,11,18))
        self.assertEqual(result["priority"],"normal")
    def test_match_stats(self):
        row=dict(mpn="TEST-123",manufacturer="TEST",quantity=None,currency=None,unit_price=None,basis="",verification="reported",valid_until=None,case_key="TEST-001")
        lines=[dict(row,side="buy",line_key="B-001"),dict(row,side="sell",line_key="S-001")]
        stats=sales_queue.matching_stats(lines)
        self.assertEqual(stats["TEST-001"]["exact_pairs"],1)
        self.assertEqual(stats["TEST-001"]["review_required"],1)
    def test_auth(self):
        app=Flask(__name__)
        db=Mock(side_effect=AssertionError("no db access"))
        sales_queue.init(app,db,lambda:False)
        self.assertEqual(app.test_client().get("/api/admin/sales-queue").status_code,401)
        db.assert_not_called()

if __name__=="__main__": unittest.main()
