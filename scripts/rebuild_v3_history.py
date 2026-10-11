"""Read-only preview of the authorised source-outline repair; 8 October is retained."""
from pathlib import Path
import hashlib
import shutil
import tempfile
from repair_content_history import repair
from content_novelty import verified_retired_history
import json

ROOT=Path(__file__).resolve().parents[1]

def rebuild_preview():
    release=json.loads((ROOT/'site/release.json').read_text('utf-8'))
    if release.get('version')=='S2':
        history=verified_retired_history(ROOT/'site/reports')
        for day in release['removed_dates']:
            if list((ROOT/'site/reports').rglob(day+'.json')):
                raise ValueError('Withdrawn edition was recreated: '+day)
        print('PASS: protected withdrawal backups verified; no withdrawn article regenerated')
        print('Preserved history:',history)
        return 0
    destination=ROOT/'.cache/history-preview'
    before=(ROOT/'site/reports/2026-10-08.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='s1-history-preview-') as folder:
        sandbox=Path(folder)
        shutil.copytree(ROOT/'site',sandbox/'site')
        (sandbox/'docs').mkdir()
        repair(sandbox,apply=True)
        assert (sandbox/'site/reports/2026-10-08.json').read_bytes()==before
        assert (ROOT/'site/reports/2026-10-08.json').read_bytes()==before
        destination.mkdir(parents=True,exist_ok=True)
        shutil.copytree(sandbox/'site/reports',destination/'reports',dirs_exist_ok=True)
        shutil.copytree(sandbox/'docs',destination/'docs',dirs_exist_ok=True)
    print('PASS: programmatic 9/10 preview; published files untouched; 8 October SHA256',hashlib.sha256(before.replace(b'\r\n',b'\n')).hexdigest())
    print('Preview retained:',destination)
    return 0

if __name__=='__main__':
    raise SystemExit(rebuild_preview())
