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
        self.assertEqual((result["associations"], result["divisions"], result["memberships"]), (50, 81, 1203))

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

    def edit_review(self, edit):
        p = self.root / "research/official_roster_audit_2026_10_09.json"
        data = json.loads(p.read_text())
        edit(data["reviews"])
        p.write_text(json.dumps(data))

    def test_official_upgrade_requires_complete_evidence(self):
        self.edit_csv("uefa_league_coverage_2026.csv", lambda rows: rows[0].update(verification_status="VERIFIED_SECONDARY"))
        self.assert_rejected("Coverage metadata mismatch")

    def test_official_evidence_wrong_id_rejected(self):
        self.edit_review(lambda rows: next(r for r in rows if r["review_status"] == "OFFICIAL_ROSTER_MATCH")["comparisons"][0].update(club_id="ENG-XXX"))
        self.assert_rejected("Official evidence club ID mismatch")

    def test_official_evidence_missing_team_rejected(self):
        self.edit_review(lambda rows: next(r for r in rows if r["review_status"] == "OFFICIAL_ROSTER_MATCH")["comparisons"].pop())
        self.assert_rejected("Official evidence roster mismatch")

    def test_independent_expected_count_rejected(self):
        p = self.root / "research/rosters.json"
        data = json.loads(p.read_text())
        next(r for r in data if "evidence_id" in r)["expected_teams"] = 999
        p.write_text(json.dumps(data))
        self.assert_rejected("Independent official team count mismatch")

    def test_all_secondary_divisions_have_review_or_blocker(self):
        self.edit_review(lambda rows: rows.pop())
        self.assert_rejected("Official review scope")

    def test_cup_duplicate_id_rejected(self):
        self.edit_csv("cup_competition_registry_2026.csv", lambda rows: rows.append(dict(rows[0])))
        self.assert_rejected("Cup registry: duplicate key")

    def test_inferred_cup_entrants_rejected(self):
        self.edit_csv("cup_competition_registry_2026.csv", lambda rows: rows[0].update(participant_status="FROM_LEAGUE_MEMBERS"))
        self.assert_rejected("Cup entrants require separate reviewed source")

    def test_wrong_provider_foreign_key_rejected(self):
        self.edit_csv("provider_mappings.csv", lambda rows: rows.append(dict(entity_type="club", internal_id="ZZZ-XXX", provider="fixture_provider", provider_id="123", verification_status="VERIFIED_OFFICIAL")))
        self.assert_rejected("Provider mapping foreign key mismatch")

    def test_fixture_provider_mapping_accepts_known_ids(self):
        self.edit_csv("provider_mappings.csv", lambda rows: rows.extend([
            dict(entity_type="club", internal_id="ENG-ARS", provider="mock_only", provider_id="fixture-club-1", verification_status="VERIFIED_OFFICIAL"),
            dict(entity_type="competition", internal_id="ENG-0001", provider="mock_only", provider_id="fixture-league-1", verification_status="VERIFIED_OFFICIAL"),
        ]))
        self.assertEqual(audit(self.root)["errors"], [])

    def test_legacy_projection_cannot_keep_withdrawn_membership(self):
        self.edit_csv("memberships.csv", lambda rows: rows.append(dict(season="2026", competition_id="LTU-0001", team_id="LTU-RIT")))
        self.assert_rejected("contains stale rows")

    def test_withdrawn_club_id_and_history_are_preserved(self):
        review = json.loads((self.root / "research/official_roster_audit_2026_10_09.json").read_text())
        removed = next(r for r in review["reviews"] if r["competition_id"] == "LTU-0001")["removed_current_memberships"][0]
        with (self.root / "uefa_clubs_canonical.csv").open() as f:
            club = next(r for r in csv.DictReader(f) if r["club_id"] == removed["club_id"])
        self.assertEqual(club["season_membership_status"], "NOT_IN_CURRENT_SCOPED_ROSTERS")
        with (self.root / "research/club_assignments.csv").open() as f:
            self.assertTrue(any(r["club_id"] == removed["club_id"] for r in csv.DictReader(f)))
        self.assertIn("earlier", removed["reason"])

    def test_excluded_competition_cannot_be_readmitted(self):
        self.edit_csv("competitions.csv", lambda rows: next(r for r in rows if r['competition_id'] == 'POL-0002').update(status='VERIFIED_SECONDARY'))
        self.assert_rejected("Excluded competition identity not reserved")

    def test_excluded_current_memberships_absent_and_clubs_preserved(self):
        excluded = json.loads((self.root / 'research/user_excluded_divisions_2026_10_09.json').read_text())
        with (self.root / 'uefa_verified_memberships_2026.csv').open() as handle:
            members = list(csv.DictReader(handle))
        self.assertFalse(set(excluded['excluded_competition_ids']) & {r['competition_id'] for r in members})
        with (self.root / 'uefa_clubs_canonical.csv').open() as handle:
            clubs = {r['club_id'] for r in csv.DictReader(handle)}
        with (self.root / 'research/club_assignments.csv').open() as handle:
            assignments = list(csv.DictReader(handle))
        self.assertTrue(all(r['club_id'] in clubs for r in assignments))


if __name__ == "__main__":
    unittest.main()
