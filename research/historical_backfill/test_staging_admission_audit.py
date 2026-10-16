"""Regression tests for isolated historical staging admission; no API or production writes."""
import unittest
from copy import deepcopy
from research.historical_backfill.staging_admission_audit import inspect

def row():
    return {
        "fixture_id":"fixture-test", "bookmaker":"pinnacle",
        "slot_utc":"2026-10-14T08:00:00+00:00",
        "kickoff_utc":"2026-10-14T12:00:00+00:00",
        "selected":{
            "line":-0.25, "line_selection":"BALANCED_LINE",
            "data_origin":"BACKFILLED", "raw_record_hash":"a"*64,
            "ft_status":"VERIFIED_EXACT_ID",
            "quotes":{
                "home":{"price":1.92,"active":True,"quote_at_utc":"2026-10-14T07:50:00+00:00"},
                "away":{"price":1.98,"active":True,"quote_at_utc":"2026-10-14T07:50:00+00:00"},
            },
        },
    }

class AdmissionTests(unittest.TestCase):
    def audit(self, *rows):
        return inspect({"coverage":{"slots":list(rows)}})

    def test_valid_backfill(self):
        result=self.audit(row())
        self.assertEqual(result["price_valid_representatives"],1)
        self.assertFalse(result["production_import_approved"])

    def test_duplicate(self):
        result=self.audit(row(),deepcopy(row()))
        self.assertEqual(result["price_valid_representatives"],1)
        self.assertIn("DUPLICATE_REPRESENTATIVE",result["rejected"][0]["reason"])

    def test_stale_quote(self):
        r=row()
        r["selected"]["quotes"]["home"]["quote_at_utc"]="2026-10-14T06:00:00+00:00"
        self.assertEqual(self.audit(r)["price_valid_representatives"],0)

    def test_after_target(self):
        r=row()
        r["selected"]["quotes"]["away"]["quote_at_utc"]="2026-10-14T08:01:00+00:00"
        self.assertEqual(self.audit(r)["price_valid_representatives"],0)

    def test_unbalanced_price(self):
        r=row()
        r["selected"]["quotes"]["home"]["price"]=1.6
        self.assertEqual(self.audit(r)["price_valid_representatives"],0)

    def test_inactive(self):
        r=row()
        r["selected"]["quotes"]["away"]["active"]=False
        self.assertEqual(self.audit(r)["price_valid_representatives"],0)

    def test_unresolved(self):
        r=row()
        r["selected"]=None
        result=self.audit(r)
        self.assertEqual(result["rejected"][0]["reason"],"MAINLINE_UNRESOLVED")

    def test_wrong_origin(self):
        r=row()
        r["selected"]["data_origin"]="OBSERVED_LIVE"
        self.assertEqual(self.audit(r)["price_valid_representatives"],0)

    def test_no_ft_does_not_authorize_import(self):
        r=row()
        r["selected"]["ft_status"]="FT_MISSING"
        result=self.audit(r)
        self.assertEqual(result["ft_status_counts"]["FT_MISSING"],1)
        self.assertFalse(result["production_import_approved"])

if __name__=="__main__":
    unittest.main()
