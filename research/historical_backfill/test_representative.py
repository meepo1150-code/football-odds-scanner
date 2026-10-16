import copy
import json
import unittest
from pathlib import Path
from research.historical_backfill.representative import select
from research.historical_backfill.revalidate import validate_catalog

CATALOG = [dict(market_id=1056, home_line=-2, home_outcome_id=1056, away_outcome_id=1057),
           dict(market_id=1060, home_line=-1.5, home_outcome_id=1060, away_outcome_id=1061)]
ARGS = dict(fixture_id='synthetic', bookmaker='pinnacle', kickoff='2026-09-19T19:30:00Z',
            slot='2026-09-19T08:00:00Z', catalog=CATALOG)


def row(line=-2, h=1.892, a=1.99, mid='1056'):
    return dict(fixture_id='synthetic', bookmaker='pinnacle', market='AH', market_id=mid,
        line=line, status='COMPLETE', slot_utc=ARGS['slot'], kickoff_utc=ARGS['kickoff'],
        quotes={s:dict(price=p, active=True, quote_at_utc='2026-09-19T07:45:00Z')
                for s,p in [('home',h),('away',a)]})


class BalancedSelectionTests(unittest.TestCase):
    def test_sporting_shape_balanced_not_nearest_zero_and_no_mutation(self):
        rs=[row(-1.5,1.4,3.0,'1060'),row()]; original=copy.deepcopy(rs)
        x=select(rs,**ARGS)
        self.assertEqual(x['status'],'BALANCED_LINE')
        self.assertEqual(x['selected']['home_line'],-2)
        self.assertEqual(x['selected']['away_line'],2)
        self.assertEqual(x['selected']['quotes']['home']['price'],1.892)
        self.assertFalse(x['official_mainline_verified'])
        self.assertEqual(rs,original)

    def test_both_sides_required_in_inclusive_range(self):
        for h,a,ok in [(1.8,2.2,True),(2.2,1.8,True),(1.799,2.0,False),
                       (2,2.201,False),(1.5,2,False),(float('nan'),2,False),
                       (True,2,False),(float('inf'),2,False),(0,2,False)]:
            with self.subTest(h=h,a=a):
                x=select([row(h=h,a=a)],**ARGS)
                self.assertEqual(x['status']=='BALANCED_LINE',ok)
                if not ok:self.assertIsNone(x['selected'])

    def test_score_and_deterministic_tie(self):
        a=row(h=1.95,a=2.05);b=row(-1.5,1.99,2.01,'1060')
        self.assertEqual(select([a,b],**ARGS)['selected']['line'],-1.5)
        a=row(h=1.95,a=2.05);b=row(-1.5,2.05,1.95,'1060')
        self.assertEqual(select([a,b],**ARGS)['selected'],select([b,a],**ARGS)['selected'])

    def test_sign_quarter_market_id_and_identity_rejected(self):
        for field,value in [('line',2),('line',-2.01),('line',True),('market_id','1060'),
                ('fixture_id','wrong'),('bookmaker','bet365'),('market','OU')]:
            with self.subTest(field=field,value=value):
                r=row();r[field]=value
                self.assertEqual(select([r],**ARGS)['status'],'MAINLINE_UNRESOLVED')

    def test_timestamp_missing_inactive_stale_and_no_rollback(self):
        for side in ('home','away'):
            for field,value in [('active',False),('active',None),
                    ('quote_at_utc','2026-09-19T06:59:59Z'),
                    ('quote_at_utc','2026-09-19T08:00:01Z'),
                    ('quote_at_utc','2026-09-19T19:30:00Z'),
                    ('quote_at_utc','2026-09-19T07:45:00'),('quote_at_utc','bad')]:
                with self.subTest(side=side,field=field,value=value):
                    r=row();r['quotes'][side][field]=value
                    self.assertEqual(select([r],**ARGS)['status'],'MAINLINE_UNRESOLVED')
            r=row();del r['quotes'][side]
            self.assertEqual(select([r],**ARGS)['status'],'MAINLINE_UNRESOLVED')
        for status in ('INACTIVE_OR_UNKNOWN','STALE_QUOTE','NO_HISTORICAL_DATA'):
            r=row();r['status']=status
            self.assertEqual(select([r],**ARGS)['status'],'MAINLINE_UNRESOLVED')

    def test_exact_slot_allowed_age_boundary_and_pre_kickoff_required(self):
        for t in ('2026-09-19T07:00:00Z',ARGS['slot']):
            r=row();r['quotes']['home']['quote_at_utc']=t
            self.assertEqual(select([r],**ARGS)['status'],'BALANCED_LINE')
        r=row();r['kickoff_utc']=ARGS['slot']
        self.assertEqual(select([r],**{**ARGS,'kickoff':ARGS['slot']})['status'],'MAINLINE_UNRESOLVED')

    def test_conflicting_duplicate_does_not_silently_choose(self):
        x=select([row(),row(h=1.90)],**ARGS)
        self.assertEqual(x['status'],'MAINLINE_UNRESOLVED')
        self.assertEqual(x['reason'],'CONFLICTING_DUPLICATE_LINE')

    def test_catalog_signed_quarters_home_away_and_scope(self):
        catalog=json.loads(Path('research/historical_backfill/reports/reviewed_catalog.json').read_text())
        source=json.loads(Path('data/normalized/oddspapi_market_catalog.json').read_text())
        validate_catalog(catalog,source)
        for field,value in [('home_line',0.13),('market_id',999999),
            ('home_outcome_id',catalog[0]['away_outcome_id']),
            ('away_outcome_id',catalog[0]['home_outcome_id'])]:
            bad=copy.deepcopy(catalog);bad[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_catalog(bad,source)
        with self.assertRaises(ValueError):validate_catalog(catalog+[catalog[0]],source)

if __name__=='__main__':unittest.main()

class CalibrationBindingTests(unittest.TestCase):
    def test_invalid_gate_cannot_authorize_expansion(self):
        from research.historical_backfill.revalidate import authorize_expansion
        from unittest.mock import patch
        with patch('research.historical_backfill.revalidate.immutable_hashes', side_effect=AssertionError('must not touch cache')):
            for gate in ({}, {'status':'FAIL'}, {'status':'PASS','expansion_allowed':True}):
                with self.subTest(gate=gate),self.assertRaisesRegex(ValueError,'PRICE_QUALITY_GATE_REQUIRED'):
                    authorize_expansion(gate,{},[],Path('.'))

    def test_coverage_does_not_count_unattempted_as_tested(self):
        from research.historical_backfill.quality_coverage import coverage
        from datetime import datetime,timezone
        c=dict(fixture_id='synthetic',bookmaker='pinnacle',kickoff=ARGS['kickoff'],
               missing_rounds=[ARGS['slot']],football_day='2026-09-19',home='H',away='A',league='Test')
        r=coverage({'candidates':[c]}, {'results':[]}, CATALOG,datetime(2026,10,16,tzinfo=timezone.utc))
        self.assertEqual(r['tested_fixtures'],0)
        self.assertEqual(r['untested_slots'],1)
        self.assertIsNone(r['breakdown'][0]['coverage_of_tested'])
        result=dict(fixture_id='synthetic',bookmaker='pinnacle',historical_ah_available=True,reconstructed=[row()])
        r=coverage({'candidates':[c]}, {'results':[result]}, CATALOG,datetime(2026,10,16,tzinfo=timezone.utc))
        self.assertEqual(r['balanced_slots'],1)
        self.assertEqual(r['slots'][0]['selected']['line'],-2)

class ResumeSafetyTests(unittest.TestCase):
    def test_missing_previous_response_blocks_instead_of_refetching(self):
        from research.historical_backfill.revalidate import require_cached_prefix
        from unittest.mock import patch
        m={'candidates':[{'fixture_id':str(n)} for n in range(100)]}
        with patch('research.historical_backfill.revalidate.load_cache',side_effect=lambda root,c: None if c['fixture_id']=='92' else {'cached':True}):
            with self.assertRaisesRegex(ValueError,'RESUME_CACHE_INCOMPLETE_NO_REFETCH'):
                require_cached_prefix(m,93,Path('.'))
        with patch('research.historical_backfill.revalidate.load_cache',return_value={'cached':True}) as load:
            self.assertEqual(require_cached_prefix(m,93,Path('.')),93)
            self.assertEqual(load.call_count,93)
