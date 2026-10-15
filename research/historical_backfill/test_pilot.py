"""Synthetic examples are unit fixtures, never claimed as real recovered prices."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from research.historical_backfill.reconstruct import reconstruct_slot
from research.historical_backfill.normalizer import normalize
from research.historical_backfill.offline_stats import three_previews,preview_statistics,deduplicate
from research.historical_backfill.candidates import select_candidates,planned_slots
from research.historical_backfill.pilot import build
from research.historical_backfill.test_reconstruct import BASE


class ReconstructionSafety(unittest.TestCase):
    def test_inactive_latest_must_not_resurrect_active_price(self):
        args=copy.deepcopy(BASE)
        args['selections']['home'].append(dict(created_at=BASE['slot'],price=2.0,active=False))
        self.assertEqual(reconstruct_slot(**args)['status'],'INACTIVE_OR_UNKNOWN')

    def test_unknown_state(self):
        args=copy.deepcopy(BASE);del args['selections']['away'][0]['active']
        self.assertEqual(reconstruct_slot(**args)['status'],'INACTIVE_OR_UNKNOWN')

    def test_conflicting_equal_timestamps(self):
        args=copy.deepcopy(BASE)
        args['selections']['away'].append({**args['selections']['away'][0],'price':1.99})
        self.assertEqual(reconstruct_slot(**args)['status'],'AMBIGUOUS_LATEST_STATE')

    def test_invalid_latest_does_not_resurrect_old(self):
        for price in (float('nan'),float('inf'),True,0):
            args=copy.deepcopy(BASE)
            args['selections']['home'].append(dict(created_at=BASE['slot'],price=price,active=True))
            self.assertEqual(reconstruct_slot(**args)['status'],'INVALID_PRICE')

    def test_malformed_timestamp_rejects_entire_stream(self):
        args=copy.deepcopy(BASE);args['selections']['home'].append(dict(created_at='invalid',price=2,active=True))
        self.assertEqual(reconstruct_slot(**args)['status'],'INVALID_TIMESTAMP')

    def test_finite_line_and_age(self):
        for line in (float('nan'),float('inf'),True,-0.8):
            with self.assertRaises(ValueError):reconstruct_slot(**dict(BASE,line=line))
        for age in (-1,True,float('inf')):
            with self.assertRaises(ValueError):reconstruct_slot(**dict(BASE,max_age_seconds=age))

    def test_exact_slot_and_kickoff(self):
        args=copy.deepcopy(BASE)
        args['selections']['home']=[dict(created_at=BASE['slot'],price=2.0,active=True)]
        result=reconstruct_slot(**args)
        self.assertEqual(result['quotes']['home']['price'],2)
        self.assertEqual(result['data_origin'],'BACKFILLED')
        with self.assertRaises(ValueError):reconstruct_slot(**dict(BASE,slot=BASE['kickoff']))

    def test_utc_midnight_football_day(self):
        slots=planned_slots('2026-10-13','2026-10-13T20:00:00Z')
        self.assertEqual(slots[-1],'2026-10-14T00:00:00+07:00')
        self.assertEqual(len(slots),4)


class AdapterTests(unittest.TestCase):
    def sample(self):
        tick=dict(createdAt=BASE['slot'],price=1.95,active=True,id=123)
        payload=dict(fixtureId='test-only',bookmakers={'test-book':{'markets':{'42':{'outcomes':{
            '1':{'players':{'0':[tick]}},'2':{'players':{'0':[{**tick,'price':1.9}]}}}}}}})
        candidate=dict(fixture_id='test-only',bookmaker='test-book')
        catalog=[dict(review_status='VERIFIED_FULL_MATCH_AH_HOME_LINE',market_id=42,home_line=-0.75,home_outcome_id=1,away_outcome_id=2,evidence='SYNTHETIC_UNIT_TEST_ONLY')]
        return payload,candidate,catalog

    def test_gate_closed_by_default(self):
        with self.assertRaisesRegex(ValueError,'SEMANTICS'):normalize(*self.sample())

    def test_exact_id_required(self):
        p,c,m=self.sample();c['fixture_id']='other'
        with self.assertRaisesRegex(ValueError,'mismatch'):normalize(p,c,m,active_semantics_verified=True)

    def test_catalog_required_no_guess(self):
        p,c,m=self.sample();self.assertEqual(normalize(p,c,[],active_semantics_verified=True),[])
        m[0]['review_status']='UNVERIFIED'
        self.assertEqual(normalize(p,c,m,active_semantics_verified=True),[])

    def test_inactive_state_preserved(self):
        p,c,m=self.sample();p['bookmakers']['test-book']['markets']['42']['outcomes']['1']['players']['0'][0]['active']=False
        r=normalize(p,c,m,active_semantics_verified=True)
        self.assertIs(r[0]['selections']['home'][0]['active'],False)

    def test_end_to_end_without_network(self):
        with patch.object(socket,'socket',side_effect=AssertionError('network prohibited')):
            p,c,m=self.sample();n=normalize(p,c,m,active_semantics_verified=True)[0]
            row=reconstruct_slot(**{**BASE,'source':n['source'],'selections':n['selections']})
            row.update(ft_score=[1,0],ft_status='VERIFIED_EXACT_ID',market_id='42')
            stat=three_previews([], [row])
            self.assertEqual(stat['combined_offline']['unique_fixtures'],1)
            settlements={k for b in stat['backfilled_only']['bands'] for k in b['settlements']}
            self.assertEqual(settlements,{'HALF_WIN','HALF_LOSS'})


class StatsTests(unittest.TestCase):
    def test_stdlib_statistics_not_shadowed(self):
        directory=str(Path(__file__).resolve().parent)
        code="import sys; sys.path.insert(0,sys.argv[1]); from statistics import mean,stdev; assert mean([1,2,3])==2; assert stdev([1,2,3])==1"
        subprocess.run([sys.executable,'-c',code,directory],check=True,capture_output=True)

    def row(self):
        r=reconstruct_slot(**BASE);r.update(ft_score=[1,0],ft_status='VERIFIED_EXACT_ID')
        return r

    def test_price_boundaries_exclusive(self):
        for price,band in [(1.8,0),(1.9,1),(2.0,2),(2.1,3),(2.2,3)]:
            r=self.row();r['quotes']['home']['price']=price;r['quotes']['away']['price']=3
            s=preview_statistics([r]);self.assertEqual(sum(b['selection_observations'] for b in s['bands']),1)
            self.assertEqual(s['bands'][band]['selection_observations'],1)

    def test_observed_precedence(self):
        o=self.row();b=copy.deepcopy(o);o['data_origin']='OBSERVED'
        result=three_previews([o],[b]);self.assertEqual(result['combined_offline']['snapshot_rows'],1)
        self.assertEqual(result['observed_precedence_overlaps'],1)

    def test_duplicate_and_conflict(self):
        r=self.row();self.assertEqual(len(deduplicate([r,r])),1)
        b=copy.deepcopy(r);b['quotes']['home']['price']=2.0
        with self.assertRaises(ValueError):deduplicate([r,b])

    def test_missing_ft_not_settled(self):
        r=self.row();r['ft_status']='FT_MISSING'
        self.assertEqual(sum(b['selection_observations'] for b in preview_statistics([r])['bands']),0)

    def test_no_binary_quarter_line(self):
        s=preview_statistics([self.row()]);counts={k for b in s['bands'] for k in b['settlements']}
        self.assertEqual(counts,{'HALF_WIN','HALF_LOSS'})


class CandidateTests(unittest.TestCase):
    def sample(self):
        row=dict(fixture_id='idTEST',home='H',away='A',league='L',kickoff='2026-10-13T20:00:00Z',football_day='2026-10-13',tournament_id=1,bookmaker='test',mainline_verified=True,source_semantics='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED',observed_at='2026-10-13T08:04:00Z',scheduled_target_at='2026-10-13T15:00:00+07:00',ah=dict(home_line=-0.75,away_line=0.75,home_price=1.95,away_price=1.9))
        mappings=[dict(provider='oddspapi',entity_type='competition',provider_id='1',internal_id='C1',verification_status='VERIFIED_PROVIDER_SNAPSHOT')]
        comps=[dict(competition_id='C1',status='VERIFIED_OFFICIAL')]
        return [row],[row],[],mappings,comps,[]

    def test_selection_missing_rounds(self):
        c,_,_=select_candidates(*self.sample());self.assertEqual(len(c[0]['missing_rounds']),3)
        self.assertEqual(c[0]['ft_status'],'FT_MISSING')

    def test_no_fuzzy_mapping(self):
        args=list(self.sample());args[1]=[{**args[1][0],'fixture_id':'other'}]
        self.assertEqual(select_candidates(*args)[0],[])

    def test_competition_exclusion(self):
        args=list(self.sample());args[-1]=['C1'];self.assertEqual(select_candidates(*args)[0],[])

    def test_fixture_identity_conflict(self):
        args=list(self.sample());args[1]=args[1]+[{**args[1][0],'away':'DIFFERENT'}]
        self.assertEqual(select_candidates(*args)[0],[])

    def test_no_guess_of_unslotted_observation(self):
        args=list(self.sample());del args[0][0]['scheduled_target_at']
        c,_,_=select_candidates(*args);self.assertEqual(c[0]['existing_rounds'],[])
        self.assertEqual(len(c[0]['unassigned_observations']),1)

    def test_limit_enforced(self):
        with self.assertRaises(ValueError):select_candidates(*self.sample(),limit=101)

    def test_conflicting_ft_separate(self):
        args=list(self.sample());args[2]=[dict(fixture_id='idTEST',ft_home_goals=n,ft_away_goals=0,result_source='synthetic') for n in (1,2)]
        c,_,_=select_candidates(*args);self.assertEqual(c[0]['ft_status'],'FT_CONFLICT')


if __name__=='__main__':unittest.main()
