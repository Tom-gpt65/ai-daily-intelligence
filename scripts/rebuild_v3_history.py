"""Read-only preview of the authorised source-outline repair; 8 October is retained."""
from pathlib import Path
import hashlib
import shutil
import tempfile
from repair_content_history import repair

ROOT=Path(__file__).resolve().parents[1]

def rebuild_preview():
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
