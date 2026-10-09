"""Site release preflight: no network and no paid services."""
import json
import re
from pathlib import Path
from edition_guarantee import complete

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

def validate() -> list[str]:
    errors = []
    markup = (SITE / "index.html").read_text(encoding="utf-8")
    app = (SITE / "app.js").read_text(encoding="utf-8")
    worker = (SITE / "sw.js").read_text(encoding="utf-8")
    for source in re.findall(r'(?:href|src)="(\./[^"#?]+)"', markup):
        if not (SITE / source[2:]).exists():
            errors.append(f"Missing linked local asset: {source}")
    ids = re.findall(r'\bid="([^" ]+)"', markup)
    if len(ids) != len(set(ids)):
        errors.append("Duplicate HTML element id")
    missing = sorted(set(re.findall(r"\$\('([a-zA-Z][a-zA-Z0-9-]*)'\)", app)) - set(ids))
    if missing:
        errors.append("Missing JavaScript element ids: " + ", ".join(missing))
    for src in ('index.html','app.js','style.css','v3.css','v4.css','v5.css','v6.css','v11.css','v12.css','v16.css','offline-glossary.json','reading-glossary.json','news-glossary.json','manifest.webmanifest'):
        if src not in worker:
            errors.append(f"PWA shell missing {src}")
    manifest=json.loads((SITE/'manifest.webmanifest').read_text(encoding='utf-8'))
    if manifest.get('display')!='standalone':
        errors.append("PWA must be standalone")
    index=json.loads((SITE/'reports'/'index.json').read_text(encoding='utf-8'))
    if not isinstance(index,list) or not index:
        return errors+['Missing or invalid reports/index.json']
    try:
        dates=[item['date'] for item in index]
    except (KeyError,TypeError):
        return errors+['Article index contains malformed records']
    if dates!=sorted(set(dates),reverse=True):
        errors.append('Report index dates must be unique, newest first')
    for i,item in enumerate(index):
        date=item['date']
        try:
            article=json.loads((SITE/'reports'/(date+'.json')).read_text(encoding='utf-8'))
            if article.get('date')!=date:
                errors.append('Report date mismatch: '+date)
            if item.get('word_count')!=article.get('word_count'):
                errors.append('Indexed word count differs from published report: '+date)
            if article.get('demo') or article.get('mode') not in ('editorial','source_digest','reading_feature'):
                errors.append('Unknown/demo report mode: '+date)
            paragraphs=article.get('essay')
            if not isinstance(paragraphs,list) or not 5<=len(paragraphs)<=15 or not all(isinstance(p,str) for p in paragraphs):
                errors.append('Missing/invalid reading paragraphs: '+date)
                continue
            words=len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b",' '.join(paragraphs)))
            if not 1000<=words<=1550:
                errors.append('Edition fails 1,000–1,550-English-word reading standard: '+date)
            if article.get('word_count')!=words:
                errors.append('Report English word count is inaccurate: '+date)
            if not complete(article):
                errors.append('At least one clickable word lacks offline Chinese meaning: '+date)
            practice=article.get('practice')
            items=practice.get('items') if isinstance(practice,dict) else None
            if not isinstance(items,list) or len(items)<7 or practice.get('official') is True:
                errors.append('Invalid original reading practice: '+date)
            else:
                if any(not isinstance(q,dict) or not isinstance(q.get('paragraph'),int)
                       or not 1<=q['paragraph']<=len(paragraphs) or not q.get('evidence_quote') for q in items):
                    errors.append('Broken reading question or evidence pointer: '+date)
            sources=article.get('stories',[])
            if article.get('mode')=='reading_feature':
                if sources or not article.get('subtitle'):
                    errors.append('Educational fallback not labelled correctly: '+date)
            elif not isinstance(sources,list) or len(sources)<3:
                errors.append('Current-news report missing at least three sources: '+date)
            if i==0 and item.get('updated_at')!=article.get('updated_at'):
                errors.append('Latest report revision differs from index: '+date)
        except (OSError, KeyError, ValueError, TypeError) as exc:
            errors.append('Unavailable/malformed indexed report '+date+': '+str(exc))
    return errors

if __name__ == '__main__':
    issues=validate()
    if issues:
        print('FAILED site checks:',*issues,sep='\n- ')
        raise SystemExit(1)
    print('Site release checks: PASS')
