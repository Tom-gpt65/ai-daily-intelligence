"""Authorised S2 withdrawal. Preserve exact prose outside Pages before removal."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from build import ROOT, atomic_json
from s2_reserve import WITHDRAWN

def withdraw(root=ROOT):
    root=Path(root);reports=(root/'site/reports').resolve()
    retired=root/'content-history/retired'
    manifest_path=root/'docs/S2_WITHDRAWN_FILES.json'
    previous_manifest=json.loads(manifest_path.read_text('utf-8')) if manifest_path.exists() else {}
    manifest=dict(previous_manifest.get('files',{}))
    for item in manifest.values():
        backup=(root/item['backup']).resolve()
        if not backup.is_relative_to(retired.resolve()):raise ValueError('Withdrawal backup escapes the preserved history directory')
        if hashlib.sha256(backup.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=item['sha256']:
            raise ValueError('Preserved withdrawal backup changed')
    targets=[]
    for day in WITHDRAWN:
        for path in reports.rglob(day+'.json'):
            target=path.resolve()
            if not target.is_relative_to(reports):raise ValueError('Withdrawal path escapes public reports')
            name=day+('-original' if 'archive-revisions' in path.parts else '')+'.json'
            backup=retired/name
            raw=path.read_bytes().replace(b'\r\n',b'\n')
            if not backup.is_file() or backup.read_bytes().replace(b'\r\n',b'\n')!=raw:
                raise ValueError('Exact withdrawal backup missing: '+str(path))
            manifest[path.relative_to(root).as_posix()]={'backup':backup.relative_to(root).as_posix(),
                                                        'sha256':hashlib.sha256(raw).hexdigest()}
            targets.append(target)
    old=json.loads((root/'site/system-status.json').read_text('utf-8'))
    rows=json.loads((reports/'index.json').read_text('utf-8'))
    if not isinstance(rows,list):raise ValueError('Cannot withdraw from a malformed index')
    if not targets and not any(r.get('date') in WITHDRAWN for r in rows):return manifest
    atomic_json(root/'docs/S2_WITHDRAWN_FILES.json',{'dates':WITHDRAWN,'files':manifest,
                'reason':'User requested removal from the public website; original dates and prose retained for strict novelty checks.',
                'no_published_edition_on_2026_10_11':not any(p.name=='2026-10-11.json' for p in targets)})
    for target in targets:target.unlink()
    atomic_json(reports/'index.json',[r for r in rows if r['date'] not in WITHDRAWN])
    atomic_json(root/'site/system-status.json',{'schema':1,'checked_at':datetime.now(timezone.utc).isoformat(),
                'state':'editions_withdrawn','latest_date':None,'mode':'unavailable',
                'withdrawal':{'dates':WITHDRAWN},'previous_failure':old,
                'news_outcome':'no_reading_available'})
    return manifest

if __name__=='__main__':
    print('Withdrawn with verified backups:',list(withdraw()))
