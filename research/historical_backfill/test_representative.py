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
