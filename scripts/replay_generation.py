"""Run actual captured RSS through production gates, without publishing or retiming.

Artifacts contain public sources and staged output only. A failed attempt exits
nonzero and leaves every production article and private store untouched.
"""
from __future__ import annotations
import argparse,json,shutil,tempfile
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
import build,validate_site,source_analysis
from source_selection import select

ROOT=Path(__file__).resolve().parents[1]

def replay(snapshot_path,out):
    snapshot=json.loads(Path(snapshot_path).read_text('utf-8'))
    now=datetime.now(timezone.utc)
    at=datetime.fromisoformat(snapshot['at'])
    if at.tzinfo is None or now<at or now.astimezone(build.TZ).date()!=at.astimezone(build.TZ).date():
        raise ValueError('Replay capture must be from the current Hong Kong day')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='source-analysis-replay-') as directory:
        site=Path(directory)/'site';shutil.copytree(ROOT/'site',site)
        health={**snapshot['diagnostics'],'source_capture_at':snapshot['at']}
        original_request=source_analysis.request_plan
        original_generate=source_analysis.generate
        counts={'analysis-draft':0,'analysis-review':0,'analysis-part':0}
        def captured_request(prompt,output_schema):
            kind='analysis-review' if 'approved' in output_schema.get('properties',{}) else 'analysis-part'
            counts[kind]+=1
            try:
                plan=original_request(prompt,output_schema)
            except source_analysis.AnalysisResponseError as exc:
                build.atomic_json(out/(kind+'-error-'+str(counts[kind])+'.json'),{'issue':exc.code,'response':exc.response})
                raise
            build.atomic_json(out/(kind+'-'+str(counts[kind])+'.json'),plan)
            return plan
        def captured_generate(*args,**kwargs):
            plan=original_generate(*args,**kwargs)
            counts['analysis-draft']+=1
            build.atomic_json(out/('analysis-draft-'+str(counts['analysis-draft'])+'.json'),plan)
            return plan
        with patch.object(build,'REPORTS',site/'reports'),patch.object(build,'STATUS_PATH',site/'system-status.json'),patch.object(validate_site,'SITE',site):
            sources=select(snapshot.get('pool',snapshot['stories']),now,build.REPORTS,health)
            with patch.object(source_analysis,'request_plan',captured_request),patch.object(source_analysis,'generate',captured_generate):
                passed=build.build_live(now,ROOT/'.cache/ecdict.csv',sources=sources,diagnostics=health)
            shutil.copy2(build.STATUS_PATH,out/'system-status.json')
            if not passed:
                print(build.STATUS_PATH.read_text('utf-8'));return 1
            errors=validate_site.validate()
            if errors:raise ValueError('Staged site invalid: '+str(errors))
            day=now.astimezone(build.TZ).date().isoformat()
            shutil.copy2(build.REPORTS/(day+'.json'),out/(day+'.json'))
            shutil.copy2(build.REPORTS/'index.json',out/'index.json')
            print('PASS: actual captured sources -> automatic analysis -> full production contract; not deployed')
            return 0

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--snapshot');g.add_argument('--fresh',action='store_true');p.add_argument('--out',default='.cache/generation-replay')
    a=p.parse_args()
    if a.fresh:
        now=datetime.now(timezone.utc);pool=[];health={}
        stories=build.collect(now,recent=build.recent_report_stories(now.astimezone(build.TZ).date().isoformat()),diagnostics=health,candidate_pool=pool)
        path=Path(a.out)/'source-snapshot.json'
        build.atomic_json(path,{'at':now.isoformat(),'stories':stories,'pool':pool,'diagnostics':health})
        a.snapshot=path
    return replay(a.snapshot,a.out)

if __name__=='__main__':raise SystemExit(main())
