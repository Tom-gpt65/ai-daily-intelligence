"""Site release preflight: no network and no paid services."""
import json
import re
from pathlib import Path

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
    for src in ('index.html','app.js','style.css','v3.css','v4.css','v5.css','manifest.webmanifest'):
        if src not in worker:
            errors.append(f"PWA shell missing {src}")
    manifest=json.loads((SITE/'manifest.webmanifest').read_text(encoding='utf-8'))
    if manifest.get('display')!='standalone':
        errors.append("PWA must be standalone")
    index=json.loads((SITE/'reports'/'index.json').read_text(encoding='utf-8'))
    if not isinstance(index,list):
        errors.append('Invalid reports/index.json')
    for i,x in enumerate(index):
        try:
            r=json.loads((SITE/'reports'/(x['date']+'.json')).read_text(encoding='utf-8'))
            if r.get('date')!=x['date']:
                errors.append('Report date mismatch: '+x['date'])
            if x.get("word_count")!=r.get("word_count"):
                errors.append('Indexed word count differs from published report: '+x['date'])
            if i==0 and r.get("mode")!="demo":
                body=" ".join(p for p in r.get("essay",[]) if isinstance(p,str))
                actual=len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b",body))
                if actual<1000:
                    errors.append('Latest public edition fails 1,000-English-word minimum: '+x["date"])
                if r.get("word_count")!=actual:
                    errors.append('Latest report English word count is inaccurate: '+x["date"])
        except (OSError, KeyError, ValueError) as exc:
            errors.append('Unavailable indexed report: '+str(exc))
    return errors

if __name__ == '__main__':
    issues=validate()
    if issues:
        print('FAILED site checks:',*issues,sep='\n- ')
        raise SystemExit(1)
    print('Site release checks: PASS')
