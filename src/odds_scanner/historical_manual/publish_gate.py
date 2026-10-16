"""Offline publication gate for manual historical scan artifacts.

Classifies *verified empty* runs without lying about successful publication.
No network, credentials or production dataset writes.
"""
import argparse
import json
import os
from pathlib import Path


def classify(report, run_id):
    if report.get("research_only") is not True:
        raise ValueError("NOT_RESEARCH_ONLY")
    url = str(report.get("run_url", ""))
    if not url.endswith("/actions/runs/" + str(run_id)):
        raise ValueError("HISTORICAL_ARTIFACT_RUN_MISMATCH")
    if report.get("status") == "COMPLETED":
        return True
    if report.get("status") == "NO_VERIFIED_FIXTURES":
        plan = report.get("plan") or {}
        if any(plan.get(k) != 0 for k in (
                "unique_fixtures", "fixture_bookmaker_pairs",
                "requested_target_slots", "planned_historical_requests")):
            raise ValueError("EMPTY_RUN_MANIFEST_INCONSISTENT")
        if (report.get("results") or report.get("errors")
                or report.get("historical_requests") != 0
                or report.get("account_requests") != 0
                or report.get("production_writes") != 0):
            raise ValueError("EMPTY_RUN_REPORT_INCONSISTENT")
        return False
    raise ValueError("HISTORICAL_SCAN_NOT_COMPLETED: " + str(report.get("status")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    publish = classify(report, args.run_id)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a") as fh:
            fh.write("publish=" + str(publish).lower() + "\n")
    if publish:
        summary = "Verified completed historical artifact: importing offline and publishing.\n"
    else:
        summary = (
            "NO_VERIFIED_FIXTURES: no verified fixture candidates, no historical API "
            "requests, and no rows to publish. Dataset and Dashboard remain unchanged. "
            "This is **not** a successful odds recovery or a Pages deployment.\n"
        )
        print("::warning::NO_VERIFIED_FIXTURES: no verified data; skipping import and Pages deployment")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as fh:
            fh.write("\n### Historical publication gate\n\n" + summary)
    print(summary.strip())


if __name__ == "__main__":
    main()
