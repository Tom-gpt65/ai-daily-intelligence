"""Trigger one free recovery run if the daily article is stale and no generation is running."""
from __future__ import annotations
import json,os,sys
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

REPO=os.environ.get("GITHUB_REPOSITORY","Tom-gpt65/ai-daily-intelligence")
TOKEN=os.environ.get("GITHUB_TOKEN","")
TODAY=datetime.now(ZoneInfo("Asia/Hong_Kong")).date().isoformat()
BASE="https://api.github.com/repos/"+REPO

def get_json(url,authorised=False):
    headers={"User-Agent":"AI-Daily-Publication-Recovery","Accept":"application/vnd.github+json"}
    if authorised and TOKEN:headers["Authorization"]="Bearer "+TOKEN
    with urlopen(Request(url,headers=headers),timeout=25) as response:
        return json.load(response)

def should_dispatch(latest_date,runs):
    if latest_date==TODAY:
        return False,"Today's report is already publicly listed"
    active=[r for r in runs if r.get("status") in {"queued","in_progress","waiting","pending","requested"}]
    if active:
        return False,"Another report generation is queued or running"
    return True,"No fresh report and no active workflow; requesting retry"

def main():
    try:
        index=get_json("https://tom-gpt65.github.io/ai-daily-intelligence/reports/index.json?date="+TODAY)
        date=index[0].get("date") if isinstance(index,list) and index else None
    except (OSError,ValueError,KeyError) as exc:
        print("Public report index unavailable, attempting scheduled recovery:",exc)
        date=None
    if not TOKEN:
        raise RuntimeError("Actions token missing; cannot trigger recovery safely")
    results=get_json(BASE+"/actions/runs?per_page=35",authorised=True)
    workflow=[r for r in results.get("workflow_runs",[]) if r.get("path")==".github/workflows/daily.yml"]
    retry,reason=should_dispatch(date,workflow)
    print(f"HK date={TODAY}; public latest={date}; decision={reason}")
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
