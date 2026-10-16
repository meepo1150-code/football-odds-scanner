"""Recompute real current health on a private copy, using main's health implementation.

Health evaluation time is fresh; scan/quote/source timestamps remain untouched.
The checked-out main tree is hashed before/after and never written or pushed.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from research.historical_backfill.actions_pilot import OUT, context_gate
from research.historical_backfill.isolated_runner import StopPilot


def source_hashes(source):
    result={}
    for directory in ('data','reports','config'):
        for p in sorted((source/directory).rglob('*')):
            if p.is_symlink():raise StopPilot('HEALTH_SOURCE_SYMLINK')
            if '__pycache__' in p.parts or p.suffix in ('.pyc','.pyo'):continue
            if p.is_file():result[str(p.relative_to(source))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def rebuild(source=Path('production-state'), *, context_validator=context_gate):
    context_validator(os.environ)
    source=source.resolve();before=source_hashes(source)
    destination=(OUT/'health-inputs').resolve()
    if destination.exists():raise StopPilot('HEALTH_INPUTS_ALREADY_EXIST')
    destination.mkdir(parents=True)
    for directory in ('data','reports','config'):
        shutil.copytree(source/directory,destination/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
    env={**os.environ,'PYTHONPATH':str(source/'src')}
    # Exact production health code, run without provider credentials in its environment.
    for key in ('ODDSPAPI_KEY','HISTORICAL_ODDSPAPI_KEY','ACCOUNT_PROBE_KEY'):
        env.pop(key,None)
    code='from pathlib import Path; from odds_scanner.scan_health import refresh; refresh(Path(__import__("sys").argv[1]))'
    done=subprocess.run([sys.executable,'-c',code,str(destination)],env=env,capture_output=True,timeout=90)
    if done.returncode:raise StopPilot('OFFLINE_HEALTH_REBUILD_FAILED')
    if before!=source_hashes(source):raise StopPilot('PRODUCTION_CHECKOUT_MUTATED')
    report=json.loads((destination/'reports/scan_health_monitor.json').read_text())
    if report.get('api_requests_used')!=0 or report.get('raw_deleted')!=0:raise StopPilot('HEALTH_NOT_READ_ONLY')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'health.json').write_text(json.dumps(report,indent=2)+'\n')
    sha=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    evidence={'production_commit':sha,'source_hashes':before,'production_inputs_unchanged':True,
              'evaluation_generated_at':report['generated_at'],'status':report['status'],
              'issues':report['issues'],'api_requests':0,'source_quote_timestamps_changed':False}
    (OUT/'health-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    # The bulky input copy is internal only; upload explicit summary files, not inputs.
    print(json.dumps({k:v for k,v in evidence.items() if k!='source_hashes'},indent=2))
    return report

if __name__=='__main__':rebuild()
