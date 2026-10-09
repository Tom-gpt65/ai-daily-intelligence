"""Trigger one free recovery run if the daily article is stale and no generation is running."""
from __future__ import annotations
import json,os,sys,time
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

REPO=os.environ.get("GITHUB_REPOSITORY","Tom-gpt65/ai-daily-intelligence")
TOKEN=os.environ.get("GITHUB_TOKEN","")
TODAY=datetime.now(ZoneInfo("Asia/Hong_Kong")).date().isoformat()
BASE="https://api.github.com/repos/"+REPO

def get_json(url,authorised=False):
    headers={"User-Agent":"AI-Daily-Publication-Recovery","Accept":"application/vnd.github+json","Cache-Control":"no-cache"}
    if authorised and TOKEN:headers["Authorization"]="Bearer "+TOKEN
    with urlopen(Request(url,headers=headers),timeout=25) as response:
        return json.load(response)

def should_dispatch(latest_date,runs,updated_at=None):
    # A report dated today might have been published during the night, well
    # before the 07:40 scheduled generation. Check publication time as well.
    freshly_updated=False
    if latest_date==TODAY and updated_at:
        try:
            update=datetime.fromisoformat(str(updated_at).replace("Z","+00:00"))
            local=update.astimezone(ZoneInfo("Asia/Hong_Kong"))
            freshly_updated=(local.date().isoformat()==TODAY and
                             (local.hour,local.minute)>=(7,40))
        except (TypeError,ValueError):
            pass
    if freshly_updated:
        return False,"Today's edition was refreshed after the morning generation window"
    active=[r for r in runs if r.get("status") in {"queued","in_progress","waiting","pending","requested"}]
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
    try:
        index=get_json("https://tom-gpt65.github.io/ai-daily-intelligence/reports/index.json"+suffix)
        date=index[0].get("date") if isinstance(index,list) and index else None
    except (OSError,ValueError,KeyError) as exc:
        print("Public report index unavailable, attempting scheduled recovery:",exc)
        date=None
    updated_at=None
    if date==TODAY:
        try:
            report=get_json("https://tom-gpt65.github.io/ai-daily-intelligence/reports/"+TODAY+".json"+suffix)
            updated_at=report.get("updated_at") if isinstance(report,dict) else None
        except (OSError,ValueError,KeyError) as exc:
            print("Could not confirm latest article timestamp:",exc)
    if not TOKEN:
        raise RuntimeError("Actions token missing; cannot trigger recovery safely")
    results=get_json(BASE+"/actions/runs?per_page=35",authorised=True)
    workflow=[r for r in results.get("workflow_runs",[]) if r.get("path")==".github/workflows/daily.yml"]
    retry,reason=should_dispatch(date,workflow,updated_at)
    print(f"HK date={TODAY}; public latest={date}; updated_at={updated_at}; decision={reason}")
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
