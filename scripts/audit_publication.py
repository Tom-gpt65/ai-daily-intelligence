"""Independent verification of the public AI Daily website and its 07:40 schedule."""
from __future__ import annotations
import argparse
import json
import os
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

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
    if report.get("mode") not in ("editorial", "source_digest"):
        errors.append("Public report mode is unknown")
    if not isinstance(report.get("essay"), list) or not report["essay"]:
        errors.append("Public article has no readable paragraphs")
    if not isinstance(report.get("stories"), list) or not report["stories"]:
        errors.append("Public article has no traceable news sources")
    try:
        updated = datetime.fromisoformat(report.get("updated_at", ""))
        if updated.tzinfo is None or updated.astimezone(HK).date().isoformat() != expected:
            errors.append("Last article update is not dated today in Hong Kong")
    except (TypeError, ValueError):
        errors.append("Public report has no valid update timestamp")
    reading = report.get("reading_metrics")
    count = reading.get("word_count", report.get("word_count", 0)) if isinstance(reading, dict) else report.get("word_count", 0)
    if not isinstance(count, int) or count < 250:
        errors.append("Public article is unusually short and unusable as a daily briefing")
    elif count < 550:
        warnings.append(f"Briefing has only {count} English words (target 550–650)")
    if report.get("mode") == "source_digest":
        warnings.append("Fallback RSS digest published: factual context and English quality need review")
    if isinstance(report.get("stories"), list) and len(report["stories"]) < 3:
        warnings.append("Fewer than three sourced AI developments today")
    return errors, warnings

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
    errors, warnings = [], []
    try:
        index = request_json(base + "reports/index.json")
        report = request_json(base + "reports/" + args.date + ".json")
        errors, warnings = assess_public(index, report, args.date)
    except Exception as exc:
        errors.append(str(exc))
    if not args.skip_schedule:
        repo = os.environ.get("GITHUB_REPOSITORY", "Tom-gpt65/ai-daily-intelligence")
        url = "https://api.github.com/repos/" + repo + "/actions/workflows/daily.yml/runs?event=schedule&per_page=50"
        try:
            runs = request_json(url, os.environ.get("GITHUB_TOKEN", ""))
            if not recent_successful_schedule(runs, args.date):
                errors.append("No successful 07:40-scheduled daily.yml run recorded for today's Hong Kong date")
        except Exception as exc:
            errors.append(f"Unable to confirm daily scheduled workflow: {exc}")
    print("### Daily publication audit (Hong Kong)")
    print("- Expected date:", args.date)
    print("- Public website:", base)
    print("- Published on today's date:", "PASS" if not errors else "NOT VERIFIED")
    print("- 07:40 schedule confirmation:", "not checked for manual audit" if args.skip_schedule else "checked")
    for warning in warnings:
        print("- QUALITY WARNING:", warning)
    for error in errors:
        print("- ERROR:", error)
    if not errors:
        print("- RESULT: PASS (availability verified; editorial accuracy is not guaranteed)")
        return 0
    print("- RESULT: FAIL: inspect publication workflow and data sources")
    return 1

if __name__ == "__main__":
    raise SystemExit(run())
