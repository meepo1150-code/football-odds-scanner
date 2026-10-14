import unittest
from research.ah_ft_enrich import enrich

class EnrichmentTests(unittest.TestCase):
    def fixture(self):
        return {"fixture_id":"x","source_fixture_ids":["x"],"last_observed_at":"2026-10-10T10:00:00+00:00","last_ah_line":-.75}
    def snap(self):
        return {"fixture_id":"x","observed_at":"2026-10-10T10:00:00+00:00","kickoff":"2026-10-10T12:00:00+00:00","favorite_side":"H","mainline_verified":True,"bookmaker":"pinnacle","provider":"pinnwire","source_semantics":"verified","ah":{"home_line":-.75,"away_line":.75,"selected_side_line":-.75}}
    def test_verified_side(self):
        self.assertEqual(enrich([self.fixture()],[self.snap()])[0]["last_favorite_side"],"H")
    def test_mismatch_rejected(self):
        s=self.snap();s["ah"]["selected_side_line"]=-.5
        self.assertEqual(enrich([self.fixture()],[s])[0]["side_evidence"],"UNVERIFIED")
    def test_ambiguous_rejected(self):
        s=self.snap()
        self.assertEqual(enrich([self.fixture()],[s,s])[0]["side_evidence"],"UNVERIFIED")
    def test_after_kickoff_rejected(self):
        s=self.snap();s["kickoff"]="2026-10-10T09:00:00+00:00"
        self.assertEqual(enrich([self.fixture()],[s])[0]["side_evidence"],"UNVERIFIED")
