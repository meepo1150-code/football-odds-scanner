"""Offline regression and negative tests for the Football Master only."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_uefa_master import ROOT, audit


class MasterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "master"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))

    def tearDown(self):
        self.temp.cleanup()

    def edit_csv(self, name, edit):
        p = self.root / name
        with p.open(newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = reader.fieldnames, list(reader)
        edit(rows)
        with p.open("w", newline="") as f:
            writer = csv.DictWriter(f, fields)
            writer.writeheader()
            writer.writerows(rows)

    def assert_rejected(self, text):
        result = audit(self.root)
        self.assertEqual(result["structural_status"], "FAIL")
        self.assertTrue(any(text in x for x in result["errors"]), result["errors"])

    def test_complete_master(self):
        result = audit(self.root)
        self.assertEqual(result["errors"], [])
        self.assertEqual((result["associations"], result["divisions"], result["memberships"]), (54, 87, 1286))

    def test_duplicate_membership_rejected(self):
        self.edit_csv("uefa_verified_memberships_2026.csv", lambda rows: rows.append(dict(rows[0])))
        self.assert_rejected("duplicate key")

    def test_bad_code_rejected(self):
        self.edit_csv("uefa_clubs_canonical.csv", lambda rows: rows[0].update(club_id="ENG-001"))
        self.assert_rejected("Invalid club code")

    def test_existing_id_reassignment_rejected(self):
        self.edit_csv("uefa_clubs_canonical.csv", lambda rows: rows[0].update(canonical_name="Different club"))
        self.assert_rejected("Existing ID/name changed")

    def test_missing_division_rejected(self):
        self.edit_csv("uefa_league_coverage_2026.csv", lambda rows: rows.pop())
        self.assert_rejected("Coverage scope mismatch")

    def test_wrong_team_count_rejected(self):
        self.edit_csv("uefa_league_coverage_2026.csv", lambda rows: rows[0].update(expected_teams="999"))
        self.assert_rejected("Team count mismatch")

    def test_wrong_source_season_rejected(self):
        self.edit_csv("uefa_verified_memberships_2026.csv", lambda rows: rows[0].update(season="2025-26"))
        self.assert_rejected("Invalid current season")

    def test_unknown_club_rejected(self):
        self.edit_csv("uefa_verified_memberships_2026.csv", lambda rows: rows[0].update(club_id="ZZZ-XXX"))
        self.assert_rejected("unknown/redirected club")

    def test_cross_border_and_reserves(self):
        with (self.root / "research/club_assignments.csv").open() as f:
            ledger = {(r["association_id"], r["source_name"]): r["club_id"] for r in csv.DictReader(f)}
        self.assertEqual(ledger[("CHE", "Vaduz")], "LIE-VAD")
        self.assertTrue(ledger[("ESP", "FC Andorra")].startswith("AND-"))
        self.assertNotEqual(ledger[("NLD", "Ajax")], ledger[("NLD", "Jong Ajax")])
        self.assertNotEqual(ledger[("ESP", "Real Sociedad")], ledger[("ESP", "Real Sociedad B")])
        self.assertNotEqual(ledger[("AUT", "SK Rapid Wien")], ledger[("AUT", "SK Rapid Wien[A]")])

    def test_rebuild_is_idempotent(self):
        def hashes():
            return {p.relative_to(self.root): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*.csv")}
        before = hashes()
        subprocess.run([sys.executable, str(self.root / "build_uefa_registry.py")], check=True, capture_output=True)
        self.assertEqual(before, hashes())


if __name__ == "__main__":
    unittest.main()
