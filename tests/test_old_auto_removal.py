"""Old Auto retirement must preserve the proven Manual and data consumers."""
import hashlib
from pathlib import Path
import yaml

REMOVED = (
    'automatic-four-round-odds', 'automatic-account-audit',
    'research-v2-scheduled-slot-recovery', 'research-v2-slot-watchdog',
    'canonical-slot-deadline-audit', 'scan-health-monitor', 'live-scan',
    'scanner', 'free-research-v2-scanner', 'europe-pinnacle-daily-discovery',
    'master-schedule-manual-recovery', 'v2-pipeline-health',
    'v2-mainline-observer', 'europe-discovery', 'five-dollar-live-research-v2',
    'propline-probe', 'pinnwire-probe',
)
PROTECTED = {
    '.github/workflows/manual-current-day-odds.yml': '7dde145da2fa86d70eab2c431d1241fa9592b7334c1fd93d6c0222307df9a169',
    'src/odds_scanner/europe_pinnacle_discovery.py': '1d8a4ac3f4c4671a224dc7c15bab32636167581d603b073bf47ca1ebc753b70b',
    'src/odds_scanner/research_request_budget.py': '493f37f4fdcec36c0f8917b8d440d4c0bfc9e4fecc07150be533a101eddd59e5',
    'src/odds_scanner/research_quota_checkpoint.py': '01e004977fd7204913d6b336388876974d5852df28b790d7991ddd53193940d5',
    'src/odds_scanner/oddspapi_provider.py': 'aa427cbd312b8cafe546ed110a0bb9411bcf1e83fe9e2364826160b56adf674b',
    'src/odds_scanner/provider_request_budget.py': '83dd84c1c0ff76e973863109bbe528f7f69726b02737a11486c05d0c982f841e',
}


def test_old_auto_entrypoints_are_deleted():
    for name in REMOVED:
        assert not Path('.github/workflows', name + '.yml').exists(), name
    assert not list(Path('src/odds_scanner').glob('automatic_*.py'))
    assert not Path('src/odds_scanner/research_v2_slot_recovery.py').exists()


def test_working_manual_is_byte_identical():
    for name, digest in PROTECTED.items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name


def test_no_scheduled_odds_collection_or_recovery():
    for path in Path('.github/workflows').glob('*.yml'):
        text = path.read_text()
        workflow = yaml.safe_load(text)
        events = workflow.get('on', workflow.get(True, {}))
        if 'schedule' in events:
            for command in ('odds_scanner.automatic_scan', 'odds_scanner.europe_pinnacle_discovery',
                            'odds_scanner.research_v2_slot_recovery', 'odds_scanner.propline_research_v2'):
                assert command not in text, path


def test_manual_publication_and_historical_evidence_are_retained():
    pages = Path('.github/workflows/pages.yml').read_text()
    assert "'Manual Current-Day Odds Observation'" in pages
    assert 'Automatic Four-Round Odds Observation' not in pages
    for name in ('automatic_scan_slots.jsonl',
                 'europe_pinnacle_research_v2_snapshots.jsonl', 'research_v2_slot_ledger.jsonl'):
        assert Path('data/normalized', name).is_file(), name
