#!/usr/bin/env bash
set -euo pipefail
# Run from repository root, on isolated research checkout.
test -f research/full_gap_audit/results/pinned-b6976e2f/expected_actual_matrix.jsonl.gz
python -m unittest discover -s research/full_gap_audit -p 'test_*report.py' -v
python -m unittest discover -s research/full_gap_audit -p 'test_silent_slot_expansion.py' -v
python research/full_gap_audit/fixture_round_report.py \
  --matrix research/full_gap_audit/results/pinned-b6976e2f/expected_actual_matrix.jsonl.gz \
  --output research/full_gap_audit/results/fixture-round-report-20261016.csv
python research/full_gap_audit/silent_slot_expansion.py \
  --matrix research/full_gap_audit/results/pinned-b6976e2f/expected_actual_matrix.jsonl.gz \
  --output research/full_gap_audit/results/silent-slot-triage-20261016.json
echo "Research-only reports created; no historical API calls."
