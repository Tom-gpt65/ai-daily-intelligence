"""Consecutive future-day laboratory; synthetic RSS never reaches production."""
from __future__ import annotations
import copy
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import build
import reading_backup
import validate_site
from verify_publication import publication_outcome
from publish_reports import select_edition

ROOT = Path(__file__).resolve().parents[1]


def simulate(first_day, sources_factory):
    current_errors = validate_site.validate()
    if current_errors:
        raise ValueError("Baseline site invalid: " + "; ".join(current_errors[:5]))
    rows = []
    with tempfile.TemporaryDirectory(prefix="s1-sequential-") as name:
        site = Path(name)/"site"
        shutil.copytree(ROOT/"site", site)
        with patch.object(build,"REPORTS",site/"reports"), patch.object(build,"STATUS_PATH",site/"system-status.json"), patch.object(validate_site,"SITE",site), patch.dict(os.environ,{"OLLAMA_ENABLED":"0","TRANSLATE_ENABLED":"0"}):
            previous_news = None
            # One continuous archive, including immediately adjacent days,
            # the 60-day boundary and a long-term finite-library exhaustion.
            for offset in (0,1,2,3,4,5,7,30,59,60,61):
                day=(datetime.fromisoformat(first_day).date()+timedelta(days=offset)).isoformat()
                reserve_time=datetime.fromisoformat(day+"T07:05:00+08:00")
                reserve=reading_backup.ensure_reading(day,reserve_time)
                if validate_site.validate():
                    raise ValueError("07:05 backup is invalid on "+day)
                now=reserve_time.replace(hour=7,minute=40)
                before={p.name:p.read_bytes() for p in build.REPORTS.glob('*.json')}
                if build.build_live(now,None,sources=[],diagnostics={"feeds_total":6,"feeds_ok":0}):
                    raise ValueError("RSS outage fabricated news")
                if before!={p.name:p.read_bytes() for p in build.REPORTS.glob('*.json')}:
                    raise ValueError("RSS outage mutated article history")
                # Replayed prior sources may not become new-day news merely
                # by giving their records a fresh timestamp.
                if previous_news:
                    repeated=copy.deepcopy(previous_news['stories'])
                    for s in repeated:s['published']=now.isoformat()
                    if build.build_live(now,None,sources=repeated):
                        raise ValueError("Repeated sources accepted as fresh news")
                sources=sources_factory(now)
                for s in sources:
                    s['url']+='?lab_day='+day
                accepted=build.build_live(now,None,sources=sources)
                if accepted:
                    report=json.loads((build.REPORTS/(day+'.json')).read_text('utf-8'))
                    if report['novelty']['max_overlap']>=0.16:
                        raise ValueError("Strict originality threshold bypassed")
                    previous_news=report
                    late=reading_backup.build_reading(day,now.replace(hour=8,minute=20))
                    if select_edition(report,late) is not report:
                        raise ValueError("Late educational reserve downgraded news")
                else:
                    status=json.loads(build.STATUS_PATH.read_text('utf-8'))
                    if status['state'] not in {'repetitive_content','incomplete_dictionary','insufficient_evidence'}:
                        raise ValueError("Unexpected generation failure: "+str(status))
                    report=reading_backup.ensure_reading(day,now.replace(hour=8,minute=20))
                errors=validate_site.validate()
                if errors:
                    raise ValueError("Final simulated publication invalid: "+"; ".join(errors[:4]))
                index=json.loads((build.REPORTS/'index.json').read_text('utf-8'))
                actual=publication_outcome(index,report,day,allow_archived=True)
                existing=before.get(day+'.json')
                retained=(existing is not None and json.loads(existing)==report)
                if not accepted and actual['news'] and not retained:
                    raise ValueError("Failed new-day generation labelled current news")
                rows.append({'date':day,'reading_date':report['date'],
                             'news_accepted':accepted,'mode':report['mode'],
                             'archive_backup':bool(actual.get('backup'))})
            # Actual missing surface word, with no history to mask this
            # rejection behind an earlier originality rejection.
            dictionary_lab=Path(name)/'missing-word'
            dictionary_lab.mkdir()
            build.REPORTS=dictionary_lab
            bad_sources=sources_factory(datetime.fromisoformat(first_day+'T07:40:00+08:00'))
            bad_sources[0]['title']+=' Zzzuntranslatedword'
            if build.build_live(datetime.fromisoformat(first_day+'T07:40:00+08:00'),None,sources=bad_sources):
                raise ValueError('Unknown word was accepted without an offline meaning')
            if json.loads(build.STATUS_PATH.read_text('utf-8'))['state']!='incomplete_dictionary':
                raise ValueError('Missing-word failure was not disclosed')
            if list(dictionary_lab.glob('????-??-??.json')):
                raise ValueError('Rejected missing-word article was written')
    print('S1 sequential simulation:',json.dumps(rows,ensure_ascii=False))
    return rows
