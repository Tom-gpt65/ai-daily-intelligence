"""Dated reserve validation and conflict-safe preparation publication."""
from __future__ import annotations
import argparse, copy, json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from build import ROOT, atomic_json
from content_novelty import audit, recent_articles
from edition_contract import issues

WITHDRAWN = ['2026-10-08','2026-10-09','2026-10-10','2026-10-11']

def release_for(reports):
    path=Path(reports).parent/'release.json'
    if not path.exists():return {}
    result=json.loads(path.read_text('utf-8'))
    if not isinstance(result,dict):raise ValueError('Release manifest is malformed')
    return result

def validate_reserve(report, reports, extra=()):
    if not isinstance(report,dict) or report.get('content_generation_profile')!='educational_model_s2':
        raise ValueError('Reserve must be an automatically reviewed S2 reading')
    day=report.get('date')
    if day in release_for(reports).get('removed_dates',[]):
        raise ValueError('Cannot restore a withdrawn edition')
    errors=issues(report,reports=Path(reports))
    # Include earlier prepared dates, not only published dates. Future packs
    # cannot repeat each other while waiting outside the public index.
    checked=audit(report,[*recent_articles(Path(reports),day),*extra])
    if not checked['pass']:errors.extend(checked['issues'])
    if errors:raise ValueError('Invalid prepared reading: '+','.join(sorted(set(errors))))
    return report

def load(day, reports):
    path=Path(reports).parent.parent/'reading-reserve'/(day+'.json')
    if not path.is_file():return None
    report=json.loads(path.read_text('utf-8'))
    if report.get('date')!=day:raise ValueError('Prepared date mismatch')
    other=[json.loads(p.read_text('utf-8')) for p in path.parent.glob('????-??-??.json') if p!=path]
    return copy.deepcopy(validate_reserve(report,reports,other))

def validate_all(root=ROOT):
    reports=Path(root)/'site/reports'
    packs=[]
    for path in sorted((Path(root)/'reading-reserve').glob('????-??-??.json')):
        value=json.loads(path.read_text('utf-8'))
        if value.get('date')!=path.stem:raise ValueError('Reserve filename/date mismatch')
        validate_reserve(value,reports,packs)
        packs.append(value)
    return packs

def publish(directory, attempts=5):
    """Replay immutable accepted packs on the latest main, never force push.

    Uses a disposable clone's reset, with the same unrelated-edit guard as the
    daily publisher. The staging directory is outside tracked release files.
    """
    def git(*args):
        return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,check=True)
    changed=git('status','--porcelain','--untracked-files=all').stdout.splitlines()
    if changed:raise ValueError('Preparation publisher requires a clean disposable checkout')
    staged=[json.loads(p.read_text('utf-8')) for p in sorted(Path(directory).glob('????-??-??.json'))]
    if not staged:raise ValueError('No automatically accepted reserves to publish')
    for attempt in range(attempts):
        git('fetch','origin','main');git('reset','--hard','origin/main')
        current=validate_all()
        for report in staged:
            if any(r['date']==report['date'] for r in current):continue
            validate_reserve(report,ROOT/'site/reports',current)
            atomic_json(ROOT/'reading-reserve'/(report['date']+'.json'),report)
            current.append(report)
        # Validate with the just-fetched code, not a stale imported module.
        subprocess.run([sys.executable,'scripts/s2_reserve.py','--validate'],cwd=ROOT,check=True)
        git('add','reading-reserve')
        if not git('diff','--cached','--name-only').stdout.strip():return
        git('commit','-m','Prepare reviewed S2 educational readings')
        try:git('push','origin','HEAD:main');return
        except subprocess.CalledProcessError:
            if attempt==attempts-1:raise
            time.sleep(min(10,2*(attempt+1)))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--validate',action='store_true');parser.add_argument('--publish')
    args=parser.parse_args()
    if args.publish:publish(args.publish)
    else:
        packs=validate_all()
        if not packs:raise ValueError('S2 readiness failed: no automatically accepted reserves')
        print('S2 reserve validation PASS:',[r['date'] for r in packs])
    return 0

if __name__=='__main__':raise SystemExit(main())
