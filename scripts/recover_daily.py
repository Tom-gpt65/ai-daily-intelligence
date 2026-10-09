"""Trigger one free recovery run if the daily article is stale and no generation is running."""
from __future__ import annotations
import json,os,re,sys,time
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
from edition_guarantee import complete

REPO=os.environ.get("GITHUB_REPOSITORY","Tom-gpt65/ai-daily-intelligence")
TOKEN=os.environ.get("GITHUB_TOKEN","")
TODAY=datetime.now(ZoneInfo("Asia/Hong_Kong")).date().isoformat()
BASE="https://api.github.com/repos/"+REPO

def get_json(url,authorised=False):
    headers={"User-Agent":"AI-Daily-Publication-Recovery","Accept":"application/vnd.github+json","Cache-Control":"no-cache"}
    if authorised and TOKEN:headers["Authorization"]="Bearer "+TOKEN
    with urlopen(Request(url,headers=headers),timeout=25) as response:
        return json.load(response)

def edition_is_readable(index_row, report, expected=TODAY):
    """Validate live reading material, not merely its timestamp."""
    if not isinstance(index_row, dict) or not isinstance(report, dict):
        return False
    if index_row.get("date") != expected or report.get("date") != expected:
        return False
    if report.get("demo") or report.get("mode") not in {"editorial", "source_digest", "reading_feature"}:
        return False
    if not complete(report):
        return False
    paragraphs, sources = report.get("essay"), report.get("stories")
    practice = report.get("practice")
    items = practice.get("items") if isinstance(practice, dict) else None
    if not isinstance(paragraphs, list) or len(paragraphs) < 5 or not all(isinstance(p, str) for p in paragraphs):
        return False
    if not isinstance(sources, list):
        return False
    if report.get("mode") == "reading_feature":
        if sources:
            return False
    elif len(sources) < 3:
        return False
    if any(not isinstance(s, dict) or not s.get("id") or not s.get("title") or not str(s.get("url", "")).startswith(("https://", "http://")) for s in sources):
        return False
    if not isinstance(items, list) or len(items) < 7:
        return False
    count = len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b", " ".join(paragraphs)))
    return count >= 1000 and report.get("word_count") == count and index_row.get("word_count") == count and index_row.get("stories") == len(sources)


def should_dispatch(latest_date,runs,updated_at=None,quality_ok=True):
    # A report dated today might have been published during the night, well
    # before the 07:40 scheduled generation. Check publication time as well.
    freshly_updated=False
    if latest_date==TODAY and updated_at:
        try:
            update=datetime.fromisoformat(str(updated_at).replace("Z","+00:00"))
            if update.tzinfo is None:
                raise ValueError("Missing timezone in article update timestamp")
            local=update.astimezone(ZoneInfo("Asia/Hong_Kong"))
            freshly_updated=(local.date().isoformat()==TODAY and
                             (local.hour,local.minute)>=(7,40))
        except (TypeError,ValueError):
            pass
    if freshly_updated and quality_ok:
        return False,"Today's verified edition was refreshed after the morning generation window"
    active=[r for r in runs if r.get("event") in {"schedule","workflow_dispatch"} and r.get("status") in {"queued","in_progress","waiting","pending","requested"}]
    if active:
        return False,"Another report generation is queued or running"
    # Cap recovery to two dispatches per Hong Kong day, even if earlier
    # attempts completed with no new RSS items or a remote service failed.
    recovery_runs=0
    for run in runs:
        if run.get("event")!="workflow_dispatch":
            continue
        try:
            submitted=datetime.fromisoformat(str(run["created_at"]).replace("Z","+00:00"))
            if submitted.astimezone(ZoneInfo("Asia/Hong_Kong")).date().isoformat()==TODAY:
                recovery_runs+=1
        except (TypeError,ValueError,KeyError):
            pass
    if recovery_runs>=2:
        return False,"Recovery limit reached: two manual/automatic dispatches today"
    return True,"No refreshed report, no active workflow and retries remain"

def main():
    suffix="?audit="+str(int(time.time()))
    index=[]
    try:
        index=get_json("https://tom-gpt65.github.io/ai-daily-intelligence/reports/index.json"+suffix)
        date=index[0].get("date") if isinstance(index,list) and index else None
    except (OSError,ValueError,KeyError) as exc:
        print("Public report index unavailable, attempting scheduled recovery:",exc)
        date=None
    updated_at=None
    quality_ok=False
    if date==TODAY:
        try:
            report=get_json("https://tom-gpt65.github.io/ai-daily-intelligence/reports/"+TODAY+".json"+suffix)
            updated_at=report.get("updated_at") if isinstance(report,dict) else None
            quality_ok=edition_is_readable(index[0],report) if isinstance(index,list) and index else False
        except (OSError,ValueError,KeyError) as exc:
            print("Could not confirm latest article timestamp:",exc)
    if not TOKEN:
        raise RuntimeError("Actions token missing; cannot trigger recovery safely")
    # Only this workflow: frequent code-only pushes must not hide active news runs.
    results=get_json(BASE+"/actions/workflows/daily.yml/runs?per_page=100",authorised=True)
    workflow=[r for r in results.get("workflow_runs",[]) if r.get("path")==".github/workflows/daily.yml"]
    retry,reason=should_dispatch(date,workflow,updated_at,quality_ok=quality_ok)
    print(f"HK date={TODAY}; public latest={date}; updated_at={updated_at}; valid_passage={quality_ok}; decision={reason}")
    if not retry:return 0
    data=json.dumps({"ref":"main"}).encode("utf-8")
    req=Request(BASE+"/actions/workflows/daily.yml/dispatches",
                data=data,method="POST",
                headers={"Authorization":"Bearer "+TOKEN,
                         "User-Agent":"AI-Daily-Publication-Recovery",
                         "Accept":"application/vnd.github+json",
                         "Content-Type":"application/json"})
    with urlopen(req,timeout=25) as resp:
        if resp.status!=204:raise RuntimeError("Dispatch did not return HTTP 204")
    print("Recovery workflow was dispatched (completion not guaranteed)")
    return 0

if __name__=="__main__":sys.exit(main())
