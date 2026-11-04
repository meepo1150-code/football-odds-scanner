import json
import tempfile
import unittest
from pathlib import Path
from youtube_prediction.pipeline import validate, append_ledger


def example():
    return {
        "date": "2026-11-04",
        "published_at": "2026-11-04T08:00:00+07:00",
        "source_type": "REVIEWED_PREDICTION",
        "predictions": [{
            "id": "p1", "fixture_id": "f1", "kickoff": "2026-11-04T20:00:00+07:00",
            "home": "A", "away": "B", "market": "OU", "line": 2.5,
            "selection": "UNDER", "label": "Under 2.5"
        }]
    }


class PredictionLedgerTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(example()), "REVIEWED")

    def test_pre_kickoff_required(self):
        d = example()
        d["predictions"][0]["kickoff"] = "2026-11-04T07:59:00+07:00"
        with self.assertRaises(ValueError):
            validate(d)

    def test_no_naive_timestamp(self):
        d = example()
        d["published_at"] = "2026-11-04T08:00:00"
        with self.assertRaises(ValueError):
            validate(d)

    def test_no_implicit_source(self):
        d = example()
        d.pop("source_type")
        with self.assertRaises(ValueError):
            validate(d)

    def test_append_only_and_idempotent(self):
        d = example()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            self.assertEqual(append_ledger(path, d), 1)
            self.assertEqual(append_ledger(path, d), 0)
            self.assertEqual(len(path.read_text().splitlines()), 1)
            d["predictions"][0]["selection"] = "OVER"
            with self.assertRaises(ValueError):
                append_ledger(path, d)

    def test_duplicate_ids(self):
        d = example()
        d["predictions"].append(dict(d["predictions"][0]))
        with self.assertRaises(ValueError):
            validate(d)


if __name__ == "__main__":
    unittest.main()
