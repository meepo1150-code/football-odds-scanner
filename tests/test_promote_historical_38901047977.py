import importlib.util
from pathlib import Path
from datetime import datetime, timezone

SPEC=importlib.util.spec_from_file_location("promotion",Path(__file__).resolve().parents[1]/"scripts/promote_historical_38901047977.py")
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

def test_utc_slot_and_bangkok_time():
    assert mod.dt("2026-09-20T08:00:00+00:00")==datetime(2026,9,20,8,tzinfo=timezone.utc)

def test_empty_historical_fails_closed():
    try:
        mod.build([],[],{"candidates":[]})
    except ValueError as e:
        assert "105" in str(e)
    else:
        raise AssertionError("Missing reviewed history accepted")
