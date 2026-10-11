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
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
from build import atomic_json
from edition_guarantee import complete
from edition_contract import issues as edition_issues

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"
BASE="https://tom-gpt65.github.io/ai-daily-intelligence/"
HK=ZoneInfo("Asia/Hong_Kong")


def publication_outcome(index, report, expected, allow_archived=False, withdrawn=False):
    if index == [] and report is None and withdrawn:
        return {'date':None,'mode':'unavailable','news':False,'reading_available':False,
                'offline_dictionary_complete':False,'withdrawal':True,'requested_date':expected}
    if (not isinstance(index,list) or not index or not isinstance(index[0],dict)
            or not isinstance(report,dict)):
        raise ValueError("Missing public edition")
    row=index[0]
    archived = allow_archived and row.get("date") == report.get("date") and report.get("date", "") < expected
    if not archived and (row.get("date")!=expected or report.get("date")!=expected):
        raise ValueError("Expected Hong Kong edition date is not published")
    errors = edition_issues(report, row)
    if errors:
        raise ValueError("Reading acceptance failed: "+", ".join(errors))
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
    result = {"date":report["date"],"mode":mode,"updated_at":report["updated_at"],
              "news":mode!="reading_feature" and not archived,"offline_dictionary_complete":True}
    if archived:
        result.update(backup="archived_reading", requested_date=expected)
    return result


def read_local():
    index=json.loads((SITE/"reports/index.json").read_text("utf-8"))
    if index==[]:return index,None
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
    info["news_outcome"]=("no_reading_available" if publication.get('reading_available') is False else "current_news_available" if publication["news"] else
                          "archived_reading" if publication.get("backup") else "educational_fallback")
    info["workflow_run_url"]=os.environ.get("GITHUB_SERVER_URL","https://github.com")+"/"+os.environ.get(
        "GITHUB_REPOSITORY","Tom-gpt65/ai-daily-intelligence")+"/actions/runs/"+os.environ.get("GITHUB_RUN_ID","")
    return info


def get_public(path, getter=None):
    if getter:return getter(path)
    suffix="?verify="+str(time.time_ns())
    req=Request(BASE+path+suffix,headers={"User-Agent":"AI-Daily-S2-Verification",
                                         "Cache-Control":"no-cache"})
    with urlopen(req,timeout=20) as response:
        raw=response.read(2_000_001)
        if response.status!=200 or len(raw)>2_000_000:raise ValueError("Public response invalid: "+path)
    return raw


def verify_live(expected, release, getter=None, expected_report=None, expected_status=None):
    index=json.loads(get_public("reports/index.json",getter))
    report=json.loads(get_public("reports/"+expected["date"]+".json",getter)) if expected.get('date') else None
    actual=publication_outcome(index,report,expected.get("requested_date",expected["date"]),allow_archived=True,
                               withdrawn=expected.get('withdrawal') is True and release.get('removed_dates')==['2026-10-08','2026-10-09','2026-10-10','2026-10-11'])
    if actual!=expected or (expected_report is not None and report != expected_report):
        raise ValueError("Pages has not caught up with the accepted edition bytes")
    public_release=json.loads(get_public("release.json",getter))
    html=get_public("index.html",getter).decode("utf-8")
    worker=get_public("sw.js",getter).decode("utf-8")
    if (public_release!=release or ">"+release["version"]+"<" not in html
            or release["cache_namespace"] not in worker):
        raise ValueError("Public S2 app/cache revision not deployed")
    if expected_status is not None and json.loads(get_public('system-status.json',getter)) != expected_status:
        raise ValueError('Public failure/backup status has not caught up')
    for name in ('app.js','cloud-sync.js','v1.css','reading-theme-v1.css'):
        if './'+name+'?v='+release['asset_revision'] not in html:
            raise ValueError('Public resource revision is stale: '+name)
    for name in ('app.js','cloud-sync.js','sw.js','v1.css','reading-theme-v1.css'):
        if get_public(name,getter).replace(b'\r\n',b'\n') != (SITE/name).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Public resource bytes are stale: '+name)
    if release.get('version')=='S2':
        removed=release.get('removed_dates',[])
        paths=['reports/'+day+'.json' for day in removed]
        paths+=['reports/archive-revisions/s1-original/'+day+'.json' for day in ('2026-10-09','2026-10-10')]
        for path in paths:
            try:
                get_public(path,getter)
            except HTTPError as exc:
                if exc.code not in (404,410):raise
            except FileNotFoundError:
                if getter is None:raise
            else:raise ValueError('Withdrawn public article is still accessible: '+path)
    return actual


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--require-news",action="store_true")
    parser.add_argument("--require-reading",action="store_true")
    parser.add_argument("--record-attempt",action="store_true")
    args=parser.parse_args()
    index,report=read_local()
    # A code-only deployment may retain yesterday's accepted article. Its
    # latest index date must never become the definition of current news.
    day=datetime.now(HK).date().isoformat()
    release=json.loads((SITE/'release.json').read_text('utf-8'))
    status=json.loads((SITE/'system-status.json').read_text('utf-8'))
    withdrawal=release.get('removed_dates')==['2026-10-08','2026-10-09','2026-10-10','2026-10-11'] and status.get('withdrawal',{}).get('dates')==release['removed_dates']
    accepted=publication_outcome(index,report,day,allow_archived=True,withdrawn=withdrawal)
    if args.record_attempt:
        path=SITE/"system-status.json"
        info=json.loads(path.read_text("utf-8")) if path.exists() else {}
        atomic_json(path,record_attempt(info,accepted,os.environ.get("BUILD_OUTCOME",""),
                                       os.environ.get("FEED_OUTCOME","")))
    if args.live:
        release=json.loads((SITE/"release.json").read_text("utf-8"))
        for attempt in range(12):
            try:
                verify_live(accepted,release,expected_report=report,
                            expected_status=json.loads((SITE/'system-status.json').read_text('utf-8')))
                break
            except (OSError,ValueError,TypeError,KeyError) as exc:
                if attempt==11:raise
                print("Waiting for public Pages verification:",type(exc).__name__,"attempt",attempt+1)
                time.sleep(10)
    outcome=("NO READING TODAY: requested editions withdrawn" if accepted.get('reading_available') is False else "CURRENT NEWS" if accepted["news"] else "ARCHIVED READING, not today's news" if accepted.get("backup") else "EDUCATIONAL FALLBACK, not current news")
    line=f"Publication verified: {accepted['date']} | {accepted['mode']} | {outcome}"
    print(line)
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as stream:stream.write("\n### S2 publication acceptance\n"+line+"\n")
    if args.require_news and not accepted["news"]:
        print("::error title=News NOT published::No accepted current-news edition is available. Review the verified reading/withdrawal status and this run; do not clear user data.")
        return 1
    if args.require_reading and accepted.get('reading_available') is False:
        print('::error title=Reading unavailable::No accepted daily or archived reading is public. Preparation or publication requires attention.')
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
