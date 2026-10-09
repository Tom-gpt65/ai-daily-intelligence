"""Independent verification of the public AI Daily website and its 07:40 schedule."""
from __future__ import annotations
import argparse
import json
import os
import time
import re
from urllib.parse import urlsplit
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from edition_guarantee import complete

HK = ZoneInfo("Asia/Hong_Kong")
BASE = "https://tom-gpt65.github.io/ai-daily-intelligence/"

def assess_public(index: object, report: object, expected: str) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    if not isinstance(index, list) or not index or not isinstance(index[0], dict):
        return ["Public reports/index.json is missing or empty"], warnings
    if index[0].get("date") != expected:
        errors.append(f"Latest public report is {index[0].get('date')}, expected {expected}")
    if not isinstance(report, dict):
        return errors + ["Public article JSON is invalid"], warnings
    if report.get("date") != expected:
        errors.append("Public report date differs from today's Hong Kong date")
    if report.get("demo") or report.get("mode") == "demo":
        errors.append("Public report is a fictional sample, not real RSS reporting")
    if report.get("mode") not in ("editorial", "source_digest", "reading_feature"):
        errors.append("Public report mode is unknown")
    if not complete(report):
        errors.append("At least one clickable English word lacks an offline Chinese meaning")
    if not isinstance(report.get("essay"), list) or not report["essay"]:
        errors.append("Public article has no readable paragraphs")
    if not isinstance(report.get("stories"), list):
        errors.append("Public article has invalid source records")
    elif report.get("mode") != "reading_feature" and not report["stories"]:
        errors.append("Current-news article has no traceable news sources")
    if isinstance(report.get("essay"),list):
        body=" ".join(p for p in report["essay"] if isinstance(p,str))
        words=len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b",body))
        if isinstance(report.get("word_count"),int) and abs(report["word_count"]-words)>2:
            errors.append("Published word count does not match the actual English article")
    else:
        body=""
    if isinstance(report.get("stories"),list) and report["stories"]:
        source_ids={str(item.get("id","")) for item in report["stories"] if isinstance(item,dict)}
        for item in report["stories"]:
            if not isinstance(item,dict) or not item.get("title"):
                errors.append("A reported AI story lacks a source title")
                continue
            u=urlsplit(str(item.get("url","")))
            if u.scheme not in {"http","https"} or not u.hostname:
                errors.append("A story source URL is missing or invalid")
        if all(source_ids) and body:
            cited=set(re.findall(r"\[(S\d+)\]",body))
            if cited-source_ids:
                errors.append("Article refers to a source ID absent from its sources list")
            if source_ids-cited:
                errors.append("Not every news source is cited in the English article")
    practice=report.get("practice")
    if isinstance(practice,dict) and isinstance(practice.get("items"),list):
        if practice.get("official") is True:
            errors.append("Custom exercises are incorrectly presented as official HKEAA questions")
        for q in practice["items"]:
            if not isinstance(q,dict) or not q.get("stem") or not q.get("evidence"):
                errors.append("A DSE exercise is missing its question text or evidence location")
                break
            if q.get("type")=="mc" and not (isinstance(q.get("answer"),int) and isinstance(q.get("options"),list) and 0<=q["answer"]<len(q["options"])):
                errors.append("A multiple-choice exercise has an invalid answer key")
                break
    try:
        updated = datetime.fromisoformat(report.get("updated_at", ""))
        if updated.tzinfo is None or updated.astimezone(HK).date().isoformat() != expected:
            errors.append("Last article update is not dated today in Hong Kong")
    except (TypeError, ValueError):
        errors.append("Public report has no valid update timestamp")
    reading = report.get("reading_metrics")
    count = reading.get("word_count", report.get("word_count", 0)) if isinstance(reading, dict) else report.get("word_count", 0)
    if not isinstance(count, int) or count < 1000:
        errors.append(f"Public long-form article is below 1,000 English words ({count} recorded)")
    elif count > 1550:
        warnings.append(f"Long-form article exceeds preferred 1,550-word upper bound ({count} words)")
    if report.get("mode") == "source_digest":
        warnings.append("RSS-based analysis published; editorial facts require source review")
    if report.get("mode") == "reading_feature":
        warnings.append("Today's passage is original educational reading, NOT contemporary AI news")
    elif isinstance(report.get("stories"), list) and len(report["stories"]) < 3:
        warnings.append("Fewer than three sourced AI developments today")
    return errors, warnings

def morning_refresh_status(report: object, expected: str) -> tuple[bool, str]:
    """Check publication metadata, not claim an exact public deployment time."""
    if not isinstance(report,dict) or report.get("date")!=expected:
        return False,"No report dated today was available"
    stamp=report.get("updated_at")
    try:
        updated=datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
        if updated.tzinfo is None:
            return False,"Report update time has no timezone"
        hk=updated.astimezone(HK)
        if hk.date().isoformat()!=expected:
            return False,"Report update timestamp does not match Hong Kong day"
        if (hk.hour,hk.minute)<(7,40):
            if report.get("mode")=="reading_feature":
                return True,"Pre-scheduled educational reserve has valid morning metadata; exact public availability time is unproven"
            return False,"Current-news report was last updated before the 07:40 morning generation window"
        return True,"Report metadata confirms a refresh at or after 07:40 HK; exact website availability time is not proven"
    except (TypeError,ValueError):
        return False,"Report has no valid update timestamp"

def recent_successful_schedule(runs: object, expected: str) -> bool:
    if not isinstance(runs, dict):
        return False
    for run in runs.get("workflow_runs", []):
        if run.get("event") != "schedule" or run.get("conclusion") != "success":
            continue
        try:
            started = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if started.astimezone(HK).date().isoformat() == expected:
                return True
        except (KeyError, TypeError, ValueError):
            continue
    return False

def recent_successful_recovery(runs: object, expected: str) -> bool:
    """Separate confirmed dispatch runs from successful scheduled executions."""
    if not isinstance(runs, dict):
        return False
    for run in runs.get("workflow_runs", []):
        if run.get("event") != "workflow_dispatch" or run.get("conclusion") != "success":
            continue
        try:
            started = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if started.astimezone(HK).date().isoformat() == expected:
                return True
        except (KeyError, TypeError, ValueError):
            continue
    return False


def request_json(url: str, token: str = "") -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI-Daily-Independent-Audit"}
    if token:
        headers["Authorization"] = "Bearer " + token
    last = None
    for attempt in range(4):
        try:
            address = url + ("&" if "?" in url else "?") + urlencode({"audit": int(time.time())})
            request = Request(address, headers=headers)
            with urlopen(request, timeout=25) as response:
                return json.loads(response.read(2_000_000).decode("utf-8"))
        except (OSError, ValueError) as exc:
            last = exc
            if attempt < 3:
                time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Could not retrieve public verification data: {last}")

def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-schedule", action="store_true", help="Check public website without requiring the 07:40 scheduled run (for manual/push verification)")
    parser.add_argument("--date", default=datetime.now(HK).date().isoformat())
    parser.add_argument("--site", default=BASE)
    args = parser.parse_args()
    base = args.site.rstrip("/") + "/"
    public_errors, warnings = [], []
    refresh_ok, refresh_note = False, "Article could not be loaded"
    report=None
    try:
        index = request_json(base + "reports/index.json")
        report = request_json(base + "reports/" + args.date + ".json")
        public_errors, warnings = assess_public(index, report, args.date)
        refresh_ok, refresh_note = morning_refresh_status(report,args.date)
    except Exception as exc:
        public_errors.append(str(exc))
    schedule_errors = []
    scheduled_ok = None
    recovered_ok = None
    if not args.skip_schedule:
        repo = os.environ.get("GITHUB_REPOSITORY", "Tom-gpt65/ai-daily-intelligence")
        url = "https://api.github.com/repos/" + repo + "/actions/workflows/daily.yml/runs?per_page=100"
        try:
            runs = request_json(url, os.environ.get("GITHUB_TOKEN", ""))
            scheduled_ok = recent_successful_schedule(runs,args.date)
            recovered_ok = recent_successful_recovery(runs,args.date)
            if not scheduled_ok:
                if recovered_ok and refresh_ok and not public_errors:
                    warnings.append("The original scheduled job did not succeed, but a later verified passage was published")
                elif isinstance(report,dict) and report.get("mode")=="reading_feature" and refresh_ok and not public_errors:
                    warnings.append("The 07:05 educational safety net provided today's passage; scheduled news status is reported separately")
                else:
                    schedule_errors.append("Neither a successful scheduled run nor verified published reading could be confirmed")
        except Exception as exc:
            schedule_errors.append(f"Unable to confirm scheduled workflow: {exc}")
        if not refresh_ok:
            public_errors.append("Morning freshness check failed: "+refresh_note)
    errors = public_errors + schedule_errors
    print("### Independent daily publication audit (Hong Kong)")
    print("- Expected date:",args.date)
    print("- Public website:",base)
    print("- Public report content/date:", "PASS" if not public_errors else "FAIL")
    print("- Article timestamp after 07:40:", "PASS" if refresh_ok else "FAIL", "-",refresh_note)
    print("- 07:40 scheduled job:", "NOT CHECKED (manual audit)" if scheduled_ok is None else ("PASS" if scheduled_ok else "FAIL"))
    print("- Recovery/manual daily job:", "NOT CHECKED (manual audit)" if recovered_ok is None else ("SUCCESSFUL RUN FOUND" if recovered_ok else "NONE CONFIRMED"))
    print("- Website accessible at exactly 08:00: NOT PROVEN by report timestamps; 08:05/09:17 observations are separate")
    for warning in warnings:
        print("- QUALITY WARNING:",warning)
    for error in errors:
        print("- ERROR:",error)
    if not errors:
        print("- RESULT: PASS (public freshness and either scheduled run or recovery verified; factual or HKEAA-level accuracy NOT certified)")
        return 0
    print("- RESULT: FAIL (see separate content and scheduler findings above)")
    return 1

if __name__ == "__main__":
    raise SystemExit(run())
