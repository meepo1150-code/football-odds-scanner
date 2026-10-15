"""Network-free tests for historical-only reconstruction."""
import unittest

from research.historical_backfill.reconstruct import reconstruct_slot


BASE = dict(
    fixture_id="fixture-test-1",
    kickoff="2026-10-01T15:00:00Z",
    slot="2026-10-01T14:00:00Z",
    source="offline-test",
    bookmaker="test-book",
    market="AH",
    line=-0.75,
    selections={
        "home": [
            {"created_at": "2026-10-01T13:50:00Z", "price": 1.95},
            {"created_at": "2026-10-01T14:10:00Z", "price": 1.80},
        ],
        "away": [{"created_at": "2026-10-01T13:59:00Z", "price": 1.90}],
    },
)


class TestReconstruct(unittest.TestCase):
    def test_last_available_not_future(self):
        result = reconstruct_slot(**BASE)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["quotes"]["home"]["price"], 1.95)
        self.assertEqual(result["quotes"]["away"]["price"], 1.90)

    def test_missing_side(self):
        args = dict(BASE, selections={"home": BASE["selections"]["home"]})
        self.assertEqual(reconstruct_slot(**args)["status"], "NO_HISTORICAL_DATA")

    def test_stale_quote(self):
        self.assertEqual(reconstruct_slot(**dict(BASE, max_age_seconds=30))["status"], "NO_HISTORICAL_DATA")

    def test_kickoff_exclusion(self):
        with self.assertRaises(ValueError):
            reconstruct_slot(**dict(BASE, slot=BASE["kickoff"]))

    def test_invalid_line(self):
        with self.assertRaises(ValueError):
            reconstruct_slot(**dict(BASE, line=-0.8))

    def test_naive_timestamp(self):
        with self.assertRaises(ValueError):
            reconstruct_slot(**dict(BASE, slot="2026-10-01T14:00:00"))

    def test_invalid_price(self):
        args = dict(BASE, selections={"home": [{"created_at": BASE["slot"], "price": 0}], "away": BASE["selections"]["away"]})
        self.assertEqual(reconstruct_slot(**args)["status"], "NO_HISTORICAL_DATA")


if __name__ == "__main__":
    unittest.main()
