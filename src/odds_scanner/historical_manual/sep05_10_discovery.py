"""One-off isolated discovery of native OddsPapi IDs for Sep 05-10 2026.

Only one billable /fixtures query on a distinct historical-research account.
No change to existing Manual Current-Day or Manual Historical collectors.
"""
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from odds_scanner.historical_manual.planner import build, football_day, stamp
from odds_scanner.historical_manual.runner import fresh_health
from odds_scanner.historical_manual.safety import (
    HttpClient, StopPilot, health_check, summarize_account,
)
from odds_scanner.master_schedule_plan import items, registry

START, END = "2026-09-05", "2026-09-10"
BOOKS = "pinnacle,bet365"
PATH = Path("data/research/manual_historical_provider_receipts.jsonl")
REPORT = Path("research/sep05_10_discovery/output/discovery.json")
PARAMS = {"sportId": 10, "from": "2026-09-04T23:00:00Z",
          "to": "2026-09-10T23:00:00Z", "language": "en"}


class FixturesClient(HttpClient):
    def __call__(self, path, params):
        if path != "/fixtures":
            return super().__call__(path, params)
        if params != PARAMS:
            raise StopPilot("DISCOVERY_UNREVIEWED_PARAMETERS")
        url = "https://api.oddspapi.io/v4/fixtures?" + urllib.parse.urlencode(
            {**params, "apiKey": self.key})
        try:
            with self.opener.open(url, timeout=60) as response:
                raw = response.read(64 * 1024 * 1024 + 1)
                if len(raw) > 64 * 1024 * 1024:
                    raise StopPilot("DISCOVERY_RESPONSE_TOO_LARGE")
                return response.status, dict(response.headers), raw
        except urllib.error.HTTPError as exc:
            return exc.code, {}, b""
        except (urllib.error.URLError, TimeoutError, OSError):
            # Never leak the apiKey-bearing URL from an HTTP exception.
            raise StopPilot("DISCOVERY_TRANSPORT_FAILED") from None


def receipt_digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True,
                                   ensure_ascii=False).encode()).hexdigest()


def validated_receipt(payload, now):
    all_rows = items(payload)
    approved = {str(t["tournament_id"]) for t in registry()}
    by_day, seen = {}, {}
    for row in all_rows:
        fid = str(row.get("fixtureId") or "")
        ko = row.get("startTime")
        if not (fid.startswith("id") and fid[2:].isdigit() and ko):
            continue
        identity = (row.get("participant1Name"), row.get("participant2Name"),
                    stamp(ko).isoformat(), str(row.get("tournamentId")))
        if fid in seen and seen[fid] != identity:
            raise StopPilot("DISCOVERY_NATIVE_IDENTITY_CONFLICT")
        seen[fid] = identity
        if (str(row.get("tournamentId")) not in approved
                or row.get("statusId") != 2 or row.get("sportId") != 10
                or not all(identity[:2])):
            continue
        d = football_day(ko).isoformat()
        if START <= d <= END:
            by_day.setdefault(d, set()).add(fid)
    r = dict(provider="oddspapi", endpoint="/fixtures",
             params=PARAMS, observed_at=now.isoformat(), payload=payload)
    r["response_id"] = receipt_digest(r)
    return r, {"provider_fixture_rows": len(all_rows),
               "approved_finished_fixture_rows": sum(map(len, by_day.values())),
               "approved_by_football_day": {k: len(v) for k, v in sorted(by_day.items())}}


def account(key, books, now, factory):
    if not key:
        raise StopPilot("DISCOVERY_CREDENTIAL_UNAVAILABLE")
    status, _, raw = factory(key)("/account", {})
    if status != 200:
        raise StopPilot("DISCOVERY_ACCOUNT_HTTP_" + str(status))
    return summarize_account(json.loads(raw), books, now)


def execute(*, root=Path("."), now=None, factory=FixturesClient, env=None,
            health_reader=None):
    now = now or datetime.now(timezone.utc)
    env = env if env is not None else os.environ
    receipt_file = root / PATH
    if receipt_file.exists() and receipt_file.stat().st_size:
        for line in receipt_file.read_text().splitlines():
            row = json.loads(line)
            if row.get("params") == PARAMS:
                expected = receipt_digest({k: v for k, v in row.items()
                                           if k != "response_id"})
                if row.get("response_id") != expected:
                    raise StopPilot("DISCOVERY_PREEXISTING_RECEIPT_INVALID")
                m = build(root, START, END, "15:00,18:00,21:00,00:00", BOOKS, now)
                return dict(status="VERIFIED_EXISTING_RECEIPT",
                    billable_discovery_requests=0,
                    approved_fixture_count=m["unique_fixtures"],
                    fixture_bookmaker_pairs=m["fixture_bookmaker_pairs"],
                    dispatch_recovery=bool(m["unique_fixtures"]),
                    receipt_id=row["response_id"])
    if (env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("PILOT_ENVIRONMENT") != "historical-research"):
        raise StopPilot("DISCOVERY_ISOLATED_MAIN_ONLY")
    history_key = env.get("HISTORICAL_ODDSPAPI_KEY")
    production_key = env.get("ACCOUNT_PROBE_KEY")
    prod = account(production_key, set(), now, factory)
    research = account(history_key, set(BOOKS.split(",")), now, factory)
    if prod["subscription_fingerprint"] == research["subscription_fingerprint"]:
        raise StopPilot("DISCOVERY_ACCOUNT_NOT_ISOLATED")
    if research["request_limit"] - research["request_count"] < 1:
        raise StopPilot("DISCOVERY_RESEARCH_QUOTA_EXHAUSTED")
    isolation = dict(production=prod["subscription_fingerprint"],
                     research=research["subscription_fingerprint"])
    read_health = health_reader or (lambda: fresh_health(root))
    baseline = read_health()
    health_check(baseline, baseline, now, account_isolation=isolation)
    # One and only one billable discovery call, never on production credentials.
    status, _, raw = factory(history_key)("/fixtures", PARAMS)
    if status != 200:
        raise StopPilot("DISCOVERY_HTTP_" + str(status))
    if history_key.encode() in raw or production_key.encode() in raw:
        raise StopPilot("DISCOVERY_SECRET_IN_RESPONSE")
    receipt, counts = validated_receipt(json.loads(raw), now)
    after = account(history_key, set(BOOKS.split(",")), now, factory)
    after_prod = account(production_key, set(), now, factory)
    if (research["subscription_fingerprint"] != after["subscription_fingerprint"]
            or after["request_count"] != research["request_count"] + 1):
        raise StopPilot("DISCOVERY_UNEXPECTED_RESEARCH_QUOTA_CHANGE")
    if (prod["subscription_fingerprint"] != after_prod["subscription_fingerprint"]
            or after_prod["request_count"] < prod["request_count"]):
        raise StopPilot("DISCOVERY_PRODUCTION_ACCOUNT_CHANGED")
    health_check(read_health(), baseline, now, account_isolation=isolation)
    receipt_file.parent.mkdir(parents=True, exist_ok=True)
    with receipt_file.open("a") as out:
        out.write(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")) + "\n")
    m = build(root, START, END, "15:00,18:00,21:00,00:00", BOOKS, now)
    report = dict(status="DISCOVERED", date_range=[START, END],
                  billable_discovery_requests=1,
                  production_discovery_requests=0,
                  approved_fixture_count=m["unique_fixtures"],
                  fixture_bookmaker_pairs=m["fixture_bookmaker_pairs"],
                  dispatch_recovery=bool(m["unique_fixtures"]),
                  receipt_id=receipt["response_id"], **counts)
    target = root / REPORT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main():
    try:
        report = execute()
    except (StopPilot, ValueError, TypeError, KeyError, OSError) as exc:
        print("::error::" + (str(exc) if isinstance(exc, StopPilot) else type(exc).__name__))
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write("dispatch=" + str(report["dispatch_recovery"]).lower() + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
            out.write("### Native fixture discovery Sep05-10\n\n" +
                      json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
