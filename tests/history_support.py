"""Withdrawn S1 incident fixtures remain read-only, outside the public website."""
import json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def historical(day, original=False):
    return json.loads((ROOT/'content-history/retired'/(day+('-original' if original else '')+'.json')).read_text('utf-8'))

def row(report):
    return {**{k:report[k] for k in ('date','mode','word_count','updated_at','headline')},'stories':len(report['stories'])}

def seed_corpus(reports):
    target=Path(reports).parent.parent/'content-history/retired'
    shutil.copytree(ROOT/'content-history/retired',target,dirs_exist_ok=True)

def all_readings():
    reports=ROOT/'site/reports'
    rows=json.loads((reports/'index.json').read_text('utf-8'))
    values=[json.loads((reports/(r['date']+'.json')).read_text('utf-8')) for r in rows]
    values.extend(json.loads(p.read_text('utf-8')) for p in sorted((ROOT/'reading-reserve').glob('????-??-??.json')))
    if not values:raise AssertionError('No published or actually prepared reading available for acceptance')
    return values
