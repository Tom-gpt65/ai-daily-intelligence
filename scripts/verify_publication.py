"""Check the actual deployment and fail NEWS visibly after safe reading is live.

No credentials, notification services, database writes or private data. A green
scheduled news job means a complete current-news edition was publicly verified.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from build import atomic_json
from edition_guarantee import complete

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
BASE="https://tom-gpt65.github.io/ai-daily-intelligence/"
HK=ZoneInfo("Asia/Hong_Kong")


def publication_outcome(index, report, expected):
    if (not isinstance(index,list) or not index or not isinstance(index[0],dict)
            or not isinstance(report,dict)):
        raise ValueError("Missing public edition")
    row=index[0]
    if row.get("date")!=expected or report.get("date")!=expected:
        raise ValueError("Expected Hong Kong edition date is not published")
    if row.get("updated_at")!=report.get("updated_at") or not row.get("updated_at"):
        raise ValueError("Index/article revision mismatch")
    if report.get("demo") or not complete(report):
        raise ValueError("Demo or incomplete offline dictionary")
    mode=report.get("mode")
    if mode not in {"reading_feature","editorial","source_digest"}:
        raise ValueError("Unknown publication mode")
    if mode=="reading_feature" and report.get("stories")!=[]:
        raise ValueError("Educational reserve falsely claims sources")
    if mode!="reading_feature" and len(report.get("stories",[]))<3:
        raise ValueError("Current news lacks three source anchors")
    return {"date":expected,"mode":mode,"updated_at":report["updated_at"],
            "news":mode!="reading_feature","offline_dictionary_complete":True}


def read_local():
    index=json.loads((SITE/"reports/index.json").read_text("utf-8"))
    day=index[0]["date"]
    report=json.loads((SITE/"reports"/(day+".json")).read_text("utf-8"))
    return index,report


def record_attempt(status, publication, build_outcome="", feed_outcome="", now=None):
    now=now or datetime.now(HK)
    info=dict(status) if isinstance(status,dict) else {}
    if build_outcome=="failure":info["state"]="build_failed"
    elif feed_outcome=="failure":info["state"]="feed_error"
    info["checked_at"]=now.astimezone(HK).isoformat()
    info["publication"]=publication
    info["news_outcome"]="current_news_available" if publication["news"] else "educational_fallback"
    info["workflow_run_url"]=os.environ.get("GITHUB_SERVER_URL","https://github.com")+"/"+os.environ.get(
        "GITHUB_REPOSITORY","Tom-gpt65/ai-daily-intelligence")+"/actions/runs/"+os.environ.get("GITHUB_RUN_ID","")
    return info


def get_public(path, getter=None):
    if getter:return getter(path)
    suffix="?verify="+str(time.time_ns())
    req=Request(BASE+path+suffix,headers={"User-Agent":"AI-Daily-V2-Verification",
                                         "Cache-Control":"no-cache"})
    with urlopen(req,timeout=20) as response:
        raw=response.read(2_000_001)
        if response.status!=200 or len(raw)>2_000_000:raise ValueError("Public response invalid: "+path)
    return raw


def verify_live(expected, release, getter=None):
    index=json.loads(get_public("reports/index.json",getter))
    report=json.loads(get_public("reports/"+expected["date"]+".json",getter))
    actual=publication_outcome(index,report,expected["date"])
    if actual!=expected:raise ValueError("Pages has not caught up with the accepted edition")
    public_release=json.loads(get_public("release.json",getter))
    html=get_public("index.html",getter).decode("utf-8")
    worker=get_public("sw.js",getter).decode("utf-8")
    if (public_release!=release or ">"+release["version"]+"<" not in html
            or release["cache_namespace"] not in worker):
        raise ValueError("Public V2 app/cache revision not deployed")
    return actual


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--require-news",action="store_true")
    parser.add_argument("--record-attempt",action="store_true")
    args=parser.parse_args()
    index,report=read_local()
    day=datetime.now(HK).date().isoformat() if args.require_news or args.record_attempt else index[0]["date"]
    accepted=publication_outcome(index,report,day)
    if args.record_attempt:
        path=SITE/"system-status.json"
        info=json.loads(path.read_text("utf-8")) if path.exists() else {}
        atomic_json(path,record_attempt(info,accepted,os.environ.get("BUILD_OUTCOME",""),
                                       os.environ.get("FEED_OUTCOME","")))
    if args.live:
        release=json.loads((SITE/"release.json").read_text("utf-8"))
        for attempt in range(12):
            try:
                verify_live(accepted,release)
                break
            except (OSError,ValueError,TypeError,KeyError) as exc:
                if attempt==11:raise
                print("Waiting for public Pages verification:",type(exc).__name__,"attempt",attempt+1)
                time.sleep(10)
    outcome="CURRENT NEWS" if accepted["news"] else "EDUCATIONAL FALLBACK, not current news"
    line=f"Publication verified: {accepted['date']} | {accepted['mode']} | {outcome}"
    print(line)
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as stream:stream.write("\n### V2 publication acceptance\n"+line+"\n")
    if args.require_news and not accepted["news"]:
        print("::error title=News NOT published::Safe educational reading is live. Current-news generation failed or sources were insufficient. Review system-status.json and this run; do not clear user data.")
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
