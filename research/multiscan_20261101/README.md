# Multiscan value research — 1 November 2026

**EXPLORATORY / NO PROVEN EDGE — retain production schedule and shadow-test before reducing scans.**

- [Six reports and data](results/README.md)
- [Locked protocol](PROTOCOL.md)
- [Verification and limits](VERIFICATION.md)

Run from the repository root:

```sh
python -m pip install -r research/multiscan_20261101/requirements.txt
python research/multiscan_20261101/analyze.py
python research/multiscan_20261101/verify.py
```

No network calls occur during analysis. Use the pinned base-data commit for reproduction; the input manifest fingerprints all data files. CSVs larger than 100 KB are stored as `.csv.gz` and can be read with pandas or any gzip utility. Production source/configuration and normalized input data are unchanged.
