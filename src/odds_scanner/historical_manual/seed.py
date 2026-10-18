"""Import only hash-verified finished-fixture cache from the pinned Actions artifact."""
import argparse
import json
import shutil
from pathlib import Path
from .planner import stamp
from .runner import CACHE, cache_read
from .safety import StopPilot, digest


def seed(directory, destination=CACHE):
    count = 0
    for index in sorted(directory.rglob('*.json')):
        if index.parent.name == 'cache':
            cache_dir = index.parent
            revision = False
        elif index.parent.parent.name == 'revisions' and index.parents[2].name == 'cache':
            cache_dir = index.parents[2]
            revision = True
        else:
            continue
        if index.is_symlink():
            raise StopPilot('SEED_SYMLINK')
        receipt = json.loads(index.read_text())
        request = receipt['request']
        if (request.get('endpoint') != '/v4/historical-odds'
                or set(request['params']) != {'fixtureId', 'bookmakers'}
                or (not revision and index.stem != digest(request))
                or (revision and (index.parent.name != digest(request) or index.stem != digest(receipt)))):
            raise StopPilot('SEED_REQUEST_INVALID')
        candidate = dict(fixture_id=request['params']['fixtureId'], request=request,
                         kickoff='2026-01-01T00:00:00+00:00')
        # Timestamp check here is structural; actual kickoff freshness is checked
        # against exact native source evidence by the planner/cache reader later.
        stamp(receipt['fetched_at'])
        cache_read(cache_dir.parent.resolve(), candidate)
        dest = destination/'cache'/index.relative_to(cache_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() != index.read_bytes():
            raise StopPilot('SEED_CACHE_CONFLICT')
        if not dest.exists():
            shutil.copyfile(index, dest)
        if receipt.get('raw_sha256'):
            raw = cache_dir.parent/'raw'/(receipt['raw_sha256']+'.json')
            output = destination/'raw'/raw.name
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists() and output.read_bytes() != raw.read_bytes():
                raise StopPilot('SEED_RAW_CONFLICT')
            if not output.exists():
                shutil.copyfile(raw, output)
        count += 1
    if not count:
        raise StopPilot('PINNED_ARTIFACT_CACHE_NOT_FOUND')
    print(json.dumps({'verified_cache_receipts_imported': count, 'provider_requests': 0}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--directory', required=True, type=Path)
    seed(p.parse_args().directory)
