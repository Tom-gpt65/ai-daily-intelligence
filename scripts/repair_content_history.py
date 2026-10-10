"""Rebuild authorised archived editions through the production generator.

Preserve original bytes and sources; stage all changes and run the shared
publication contract before copying any regenerated report to the checkout.
No operator-authored article text and no fresh-news claim for historic inputs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import build
import validate_site
from content_novelty import overlap
from edition_contract import issues
from editorial_quality import inspect

ROOT=Path(__file__).resolve().parents[1]
DAYS=('2026-10-09','2026-10-10')
HK=ZoneInfo('Asia/Hong_Kong')


def repair(root=ROOT, apply=False):
    root=Path(root)
    originals={day:(root/'site/reports/archive-revisions/s1-original'/(day+'.json')).read_bytes().replace(b'\r\n',b'\n') for day in DAYS}
    source_reports={day:json.loads(raw) for day,raw in originals.items()}
    settings=(build.REPORTS,build.STATUS_PATH,validate_site.SITE)
    rebuilt_at=datetime.now(HK).isoformat()
    try:
        with tempfile.TemporaryDirectory(prefix='s1-content-repair-') as name:
            site=Path(name)/'site'
            shutil.copytree(root/'site',site)
            build.REPORTS=site/'reports'
            build.STATUS_PATH=site/'system-status.json'
            validate_site.SITE=site
            generated={}
            for day in DAYS:
                # A disclosed historical validation reference, not a claim
                # that these sources were fetched at that time today.
                source_clock=min(datetime.fromisoformat(day+'T23:30:00+08:00'),datetime.fromisoformat(rebuilt_at))
                if not build.build_live(source_clock,None,sources=source_reports[day]['stories']):
                    raise ValueError('Historical generator rejected '+day+': '+build.STATUS_PATH.read_text('utf-8'))
                path=build.REPORTS/(day+'.json')
                report=json.loads(path.read_text('utf-8'))
                report.update(updated_at=rebuilt_at,history_rebuilt_at=rebuilt_at,historical_rebuild=True,
                              source_snapshot_date=day,historical_source_reference_at=source_clock.isoformat(),
                              original_revision_sha256=hashlib.sha256(originals[day]).hexdigest(),
                              generation_provenance='build.build_live -> source_outline.compose; archived source snapshot only',
                              editorial_notice='Automatically reconstructed reading from the archived '+day+' RSS snapshot; not fresh reporting or independently confirmed news.')
                report['quality_note']+=' 本篇由程式重製，使用原日期已保存的 RSS 來源；重製時間不代表新聞發生時間。'
                errors=issues(report,reports=build.REPORTS)
                if errors:
                    raise ValueError('Rebuilt edition failed: '+str(errors))
                build.atomic_json(path,report)
                generated[day]=report
            scores={}
            for day,report in generated.items():
                for old_day,old in source_reports.items():
                    score=overlap(report['essay'],old['essay'])
                    scores[day+' / original '+old_day]=score
                    if score>=0.16:
                        raise ValueError('Replacement recycles original content: '+str(score))
            pair=overlap(generated[DAYS[0]]['essay'],generated[DAYS[1]]['essay'])
            if pair>=0.16:
                raise ValueError('Rebuilt cross-day overlap is not strictly below 16%')
            scores['rebuilt 09 / rebuilt 10']=pair
            index=json.loads((build.REPORTS/'index.json').read_text('utf-8'))
            for row in index:
                if row['date'] in generated:
                    report=generated[row['date']]
                    for key in ('headline','word_count','updated_at','mode'):
                        row[key]=report[key]
                    row['stories']=len(report['stories'])
            build.atomic_json(build.REPORTS/'index.json',index)
            errors=validate_site.validate()
            if errors:
                raise ValueError('Staged site validation failed: '+str(errors))
            evidence={'generated_at':rebuilt_at,'program':'repair_content_history.py -> build.build_live -> source_outline.compose',
                      'threshold_exclusive':0.16,'five_word_overlap':scores,
                      'original_quality':{day:inspect(r['essay'],r['stories']) for day,r in source_reports.items()},
                      'rebuilt_quality':{day:r['editorial_quality'] for day,r in generated.items()},
                      'original_sha256':{day:hashlib.sha256(raw).hexdigest() for day,raw in originals.items()},
                      'site_validation':'PASS','applied':apply}
            if apply:
                for day in DAYS:
                    shutil.copy2(build.REPORTS/(day+'.json'),root/'site/reports'/(day+'.json'))
                shutil.copy2(build.REPORTS/'index.json',root/'site/reports/index.json')
                build.atomic_json(root/'docs/S1_CONTENT_REPAIR_EVIDENCE.json',evidence)
            print(json.dumps(evidence,ensure_ascii=False,indent=2))
            return evidence
    finally:
        build.REPORTS,build.STATUS_PATH,validate_site.SITE=settings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Replace only the two authorised dated reports after all staged checks pass')
    repair(apply=parser.parse_args().apply)
