import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from research.historical_backfill.multiday import build_manifest,add_exact_football_days,age_band
from research.historical_backfill.candidates import select_candidates
from research.historical_backfill.isolated_runner import (
    run,digest,quiet_window,summarize_account,health_check,StopPilot,load_cache)
from research.historical_backfill.coverage_metrics import coverage_report
from research.historical_backfill import storage

NOW=datetime(2026,10,15,5,tzinfo=timezone.utc) # noon Bangkok, outside production recovery


class FixtureFactory:
    def setup(self,count=10):
        tick=dict(createdAt='2026-10-13T07:59:00Z',price=1.95,active=True)
        candidates=[]; observations=[]
        for n in range(count):
            fid='idTEST'+str(n)
            candidates.append(dict(fixture_id=fid,bookmaker='test',league='Synthetic',home='H',away='A',
                kickoff='2026-10-13T20:00:00Z',ft_status='VERIFIED_EXACT_ID',ft_score=[1,0],
                missing_rounds=['2026-10-13T15:00:00+07:00'],existing_rounds=[],age_days=2,age_band='0_7',
                phase='CALIBRATION' if n<10 else 'EXPANSION_PENDING_CALIBRATION',
                request=dict(endpoint='/v4/historical-odds',params=dict(fixtureId=fid,bookmakers='test'))))
            observations.append(dict(fixture_id=fid,bookmaker='test',kickoff='2026-10-13T20:00:00Z',
                observed_at='2026-10-13T08:00:00Z',ah=dict(home_line=-0.75,home_price=1.95,away_price=1.95)))
        manifest=dict(candidates=candidates)
        catalog=[dict(market_id=42,home_line=-0.75,home_outcome_id=1,away_outcome_id=2,
            review_status='VERIFIED_FULL_MATCH_AH_HOME_LINE',evidence='SYNTHETIC_UNIT_TEST_ONLY')]
        gate=dict(credential_scope='DEDICATED_SUBSCRIPTION_VERIFIED',credential_evidence='SYNTHETIC',
            semantics_mode='PROVIDER_REPORTED_SNAPSHOT',semantics_evidence='SYNTHETIC',
            catalog_sha256=digest(catalog),manifest_sha256=digest(manifest))
        health=dict(generated_at=NOW.isoformat(),status='WARNING',issues=['existing'])
        account=dict(api_key='DO_NOT_LOG',current_subscription_id='synthetic',subscriptions=[dict(
            subscription_id='synthetic',is_active=True,sport_ids=[10],bookmakers={'test':{}},request_limit=250,request_count=5)])
        calls=[]
        def client(path,params):
            calls.append((path,params))
            if path=='/account':return 200,{},json.dumps(account).encode()
            payload=dict(fixtureId=params['fixtureId'],bookmakers={'test':{'markets':{'42':{'outcomes':{
                '1':{'players':{'0':[tick]}},'2':{'players':{'0':[tick]}}}}}}})
            return 200,{},json.dumps(payload).encode()
        return manifest,catalog,observations,gate,health,account,calls,client


class RunnerTests(unittest.TestCase,FixtureFactory):
    def invoke(self,args,**changes):
        m,c,o,g,h,a,calls,client=args
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'historical'
            with patch.object(storage,'ROOT',root):
                return run(m,c,o,g,lambda:h,key='SYNTHETIC',client=client,
                           clock=lambda:NOW,sleeper=lambda _:None,root=root,**changes)

    def test_missing_credential_zero_requests(self):
        m,c,o,g,h,*_=self.setup()
        r=run(m,c,o,g,lambda:h,clock=lambda:NOW)
        self.assertEqual(r['actual_total_requests'],0)
        self.assertEqual(r['errors'],['ISOLATED_CREDENTIAL_NOT_CONFIGURED'])

    def test_calibration_real_pipeline_synthetic_transport(self):
        args=self.setup();r=self.invoke(args)
        self.assertTrue(r['calibration_passed']);self.assertEqual(r['actual_historical_requests'],10)
        self.assertEqual(r['actual_account_requests'],21)
        self.assertFalse(r['live_coverage_measured'])
        self.assertNotIn('DO_NOT_LOG',json.dumps(r))

    def test_expansion_requires_quality_and_is_capped(self):
        args=self.setup(20);r=self.invoke(args,allow_expansion=True)
        self.assertTrue(r['expansion_started']);self.assertEqual(r['actual_historical_requests'],20)
        self.assertEqual(len(r['results']),20)

    def test_default_does_not_expand(self):
        r=self.invoke(self.setup(20));self.assertEqual(r['actual_historical_requests'],10)

    def test_429_immediate_stop_no_retry(self):
        args=list(self.setup());old=args[-1]
        args[-1]=lambda path,params:(429,{'Retry-After':'999'},b'') if path=='/historical-odds' else old(path,params)
        r=self.invoke(args,allow_expansion=True)
        self.assertEqual(r['actual_historical_requests'],1)
        self.assertEqual(r['errors'],['HTTP_429_STOP_NO_RETRY'])

    def test_quota_anomaly_stops(self):
        args=list(self.setup());old=args[-1];counts={'n':0}
        def client(path,params):
            if path=='/account':
                counts['n']+=1
                if counts['n']>=3:args[5]['subscriptions'][0]['request_count']=6
            return old(path,params)
        args[-1]=client;r=self.invoke(args)
        self.assertEqual(r['actual_historical_requests'],1)
        self.assertEqual(r['errors'],['QUOTA_OR_SUBSCRIPTION_ANOMALY'])

    def test_no_ah_prevents_expansion(self):
        args=list(self.setup(20));old=args[-1]
        args[-1]=lambda path,params:(200,{},json.dumps(dict(fixtureId=params['fixtureId'],bookmakers={})).encode()) if path=='/historical-odds' else old(path,params)
        r=self.invoke(args,allow_expansion=True)
        self.assertEqual(r['actual_historical_requests'],10)
        self.assertFalse(r['expansion_started'])

    def test_cache_first_hash_and_immutability(self):
        args=self.setup();m,c,o,g,h,a,calls,client=args
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'historical'
            with patch.object(storage,'ROOT',root):
                common=dict(key='SYNTHETIC',client=client,clock=lambda:NOW,sleeper=lambda _:None,root=root)
                first=run(m,c,o,g,lambda:h,**common)
                second=run(m,c,o,g,lambda:h,**common)
                self.assertEqual(first['actual_historical_requests'],10)
                self.assertEqual(second['actual_historical_requests'],0)
                self.assertEqual(second['cache_hits'],10)
                index=next((root/'cache').glob('*.json'));receipt=json.loads(index.read_text())
                (root/'raw'/(receipt['raw_sha256']+'.json')).write_bytes(b'corrupt')
                with self.assertRaises(StopPilot):load_cache(root,next(c for c in m['candidates'] if c['request']==receipt['request']))

    def test_unverified_credential_scope_blocks(self):
        args=list(self.setup());args[3]['credential_scope']='PRODUCTION_ALIAS'
        r=self.invoke(args);self.assertEqual(r['actual_total_requests'],0)

    def test_unreviewed_manifest_blocks(self):
        args=list(self.setup());args[0]['candidates'][0]['home']='Changed'
        r=self.invoke(args);self.assertEqual(r['actual_total_requests'],0)

    def test_unsafe_request_contract_blocks(self):
        args=list(self.setup());args[0]['candidates'][0]['request']['params']['active']=True
        args[3]['manifest_sha256']=digest(args[0]);r=self.invoke(args)
        self.assertEqual(r['actual_total_requests'],0)

    def test_account_entitlement_and_quota(self):
        args=self.setup();account=args[5]
        with self.assertRaises(StopPilot):summarize_account(account,{'unauthorized'},NOW)
        account['subscriptions'][0]['request_count']=250
        with self.assertRaises(StopPilot):summarize_account(account,{'test'},NOW)

    def test_health_stale_and_degradation(self):
        h=self.setup()[4]
        with self.assertRaises(StopPilot):health_check(h,h,NOW+timedelta(minutes=16))
        with self.assertRaises(StopPilot):health_check({**h,'status':'FAIL'},h,NOW)
        with self.assertRaises(StopPilot):health_check({**h,'issues':['new']},h,NOW)

    def test_quiet_windows_include_midnight_and_recovery(self):
        self.assertTrue(quiet_window(NOW))
        for t in ('2026-10-15T07:50:00Z','2026-10-15T10:00:00Z','2026-10-15T17:01:00Z'):
            self.assertFalse(quiet_window(datetime.fromisoformat(t.replace('Z','+00:00'))))

    def test_coverage_untested_is_not_zero(self):
        m,*_=self.setup();r=coverage_report(m,dict(results=[]))
        self.assertTrue(all(x['coverage'] is None for x in r))
        self.assertEqual(next(x for x in r if x['dimension']=='age_band' and x['value']=='8_14')['status'],'NO_CANDIDATES')


class MultiDayTests(unittest.TestCase):
    def test_exact_day_enrichment_never_guesses(self):
        r=dict(fixture_id='idSynthetic',kickoff='2026-10-13T20:00:00Z',football_day='2026-10-13')
        o=dict(r);del o['football_day']
        self.assertEqual(add_exact_football_days([o],[r])[0]['football_day'],r['football_day'])
        self.assertEqual(add_exact_football_days([o],[]),[])
        self.assertEqual(add_exact_football_days([o],[r,{**r,'football_day':'2026-10-12'}]),[])

    def test_nonoverlapping_age_bands(self):
        self.assertEqual([age_band(n) for n in (7,8,14,15,30,31)],['0_7','8_14','8_14','15_30','15_30','OUTSIDE_30'])

    def test_scope_and_calibration_contracts(self):
        with self.assertRaises(ValueError):build_manifest([],[],[],[],[],[],[],as_of=NOW.isoformat())
        with self.assertRaises(ValueError):build_manifest([],[],[],[],[],[],[],as_of=NOW.isoformat(),maximum=101)

    def test_hundred_fixture_selection_preserves_calibration(self):
        rows=[]
        for n in range(110):
            day='2026-10-13' if n%2 else '2026-10-14'
            rows.append(dict(fixture_id='idSynthetic'+str(n),home='H'+str(n),away='A'+str(n),
                league='Synthetic',tournament_id=1,bookmaker='test',football_day=day,
                kickoff=day+'T20:00:00Z',observed_at=day+'T08:01:00Z',scheduled_target_at=day+'T15:00:00+07:00',
                source_semantics='CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED',mainline_verified=True,
                ah=dict(home_line=-0.75,away_line=0.75,home_price=1.95,away_price=1.9)))
        mappings=[dict(provider='oddspapi',entity_type='competition',provider_id='1',internal_id='C1',verification_status='VERIFIED_PROVIDER_SNAPSHOT')]
        comps=[dict(competition_id='C1',status='VERIFIED_OFFICIAL')]
        calibration=select_candidates(rows,rows,[],mappings,comps,[])[0]
        r=build_manifest(rows,rows,[],mappings,comps,[],calibration,as_of=NOW.isoformat())
        self.assertEqual(r['unique_fixture_count'],100)
        self.assertEqual([c['fixture_id'] for c in r['candidates'][:10]],[c['fixture_id'] for c in calibration])
        self.assertEqual(r['expansion_count'],90)


if __name__=='__main__':unittest.main()
