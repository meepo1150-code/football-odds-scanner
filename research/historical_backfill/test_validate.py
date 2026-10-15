"""Offline validation regression tests: no API, no filesystem writes."""
import unittest

from research.historical_backfill.validate import validate_ah_record


def sample():
    return {
        "fixture_id": "sample-1",
        "source": "fixture-source",
        "bookmaker": "sample-book",
        "kickoff_utc": "2026-09-10T19:00:00Z",
        "home_team": "Team A",
        "away_team": "Team B",
        "line": -0.75,
        "home_ticks": [{"created_at": "2026-09-10T18:30:00Z", "price": 1.95}],
        "away_ticks": [{"created_at": "2026-09-10T18:30:00Z", "price": 1.91}],
    }


class ValidateAHTests(unittest.TestCase):
    def test_valid(self):
        result = validate_ah_record(sample())
        self.assertEqual(result["provenance"], "HISTORICAL_RECONSTRUCTED")
        self.assertEqual(result["line"], -0.75)

    def test_missing_source(self):
        record = sample()
        del record["source"]
        with self.assertRaises(ValueError):
            validate_ah_record(record)

    def test_prohibit_oddspapi(self):
        record = sample()
        record["source"] = "OddsPapi"
        with self.assertRaises(ValueError):
            validate_ah_record(record)

    def test_post_kickoff(self):
        record = sample()
        record["home_ticks"][0]["created_at"] = record["kickoff_utc"]
        with self.assertRaises(ValueError):
            validate_ah_record(record)

    def test_bad_quarter_line(self):
        record = sample()
        record["line"] = -0.8
        with self.assertRaises(ValueError):
            validate_ah_record(record)

    def test_naive_quote_time(self):
        record = sample()
        record["away_ticks"][0]["created_at"] = "2026-09-10T18:30:00"
        with self.assertRaises(ValueError):
            validate_ah_record(record)

    def test_missing_side_is_explicit_not_fabricated(self):
        record = sample()
        record["away_ticks"] = []
        result = validate_ah_record(record)
        self.assertEqual(result["away_ticks"], [])


if __name__ == "__main__":
    unittest.main()
