"""Isolation tests for historical raw storage."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.historical_backfill import storage


class TestStorage(unittest.TestCase):
    def test_immutable_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "historical"
            with patch.object(storage, "ROOT", root.resolve()):
                first = storage.append_raw({"fixture_id": "a", "price": 1.91}, root=root)
                second = storage.append_raw({"price": 1.91, "fixture_id": "a"}, root=root)
                self.assertEqual(first, second)
                self.assertEqual(len(list((root / "raw").glob("*.json"))), 1)

    def test_reject_outside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(storage, "ROOT", (Path(tmp) / "historical").resolve()):
                with self.assertRaises(ValueError):
                    storage.append_raw({"x": 1}, root=Path(tmp) / "production")

    def test_corrupt_record_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "historical"
            with patch.object(storage, "ROOT", root.resolve()):
                path = storage.append_raw({"x": 1}, root=root)
                path.write_text("corrupt", encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    storage.append_raw({"x": 1}, root=root)


if __name__ == "__main__":
    unittest.main()

