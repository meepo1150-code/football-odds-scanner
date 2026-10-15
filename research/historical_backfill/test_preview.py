"""Tests for Bangkok round scheduling and offline preview."""
import unittest

from research.historical_backfill.preview import preview, slots_for_fixture


class PreviewTests(unittest.TestCase):
    def test_bangkok_slots(self):
        slots = slots_for_fixture("2026-10-15T13:00:00Z", days_back=0)
        self.assertEqual([s[11:16] for s in slots], ["00:00", "15:00", "18:00"])

    def test_no_future_slot(self):
        slots = slots_for_fixture("2026-10-15T08:00:00Z", days_back=0)
        self.assertEqual([s[11:16] for s in slots], ["00:00"])

    def test_offline_no_data(self):
        record = {
            "fixture_id": "one", "source": "offline", "bookmaker": "book",
            "kickoff_utc": "2026-10-15T13:00:00Z",
            "home_team": "A", "away_team": "B", "line": -0.5,
            "home_ticks": [], "away_ticks": [],
        }
        result = preview([record])
        self.assertEqual(result["api_requests"], 0)
        self.assertEqual(result["writes"], 0)
        self.assertEqual(result["complete"], 0)
        self.assertGreater(result["missing"], 0)


if __name__ == "__main__":
    unittest.main()
