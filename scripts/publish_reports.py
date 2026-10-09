"""Conflict-safe publication of daily reports from GitHub Actions.

Preserves the generated files, fetches the latest main branch, merges report
indices and retries non-fast-forward pushes. Never forces a push.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from datetime import datetime,timezone
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from edition_guarantee import complete

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/"site"/"reports"
STATUS=ROOT/"site"/"system-status.json"

def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):
        return default

def merge_index(remote, local):
    """Newly generated date wins, without discarding other published dates."""
    combined={}
    for row in remote if isinstance(remote,list) else []:
        if isinstance(row,dict) and isinstance(row.get("date"),str):
            combined[row["date"]]=copy.deepcopy(row)
    for row in local if isinstance(local,list) else []:
        if isinstance(row,dict) and isinstance(row.get("date"),str):
            combined[row["date"]]=copy.deepcopy(row)
    return sorted(combined.values(),key=lambda row:row["date"],reverse=True)[:100]

def utc_instant(value):
    """Normalise mixed Z/+08:00 timestamps; do not compare them as strings."""
    try:
        stamp=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo is not None else None
    except (TypeError,ValueError):
        return None

def incoming_is_newer(existing, incoming):
    previous=utc_instant(existing.get("updated_at"))
    proposed=utc_instant(incoming.get("updated_at"))
    if previous is None:return proposed is not None
    return proposed is not None and proposed>=previous

def git(*args):
    return subprocess.run(["git",*args],cwd=ROOT,check=True,
                          text=True,capture_output=True)

def publish(max_attempts=5):
    with tempfile.TemporaryDirectory(prefix="daily-publish-") as tmp:
        backup=Path(tmp)
        shutil.copytree(REPORTS,backup/"reports")
        status_backup=STATUS.read_bytes() if STATUS.exists() else b""
        report_index=read_json(backup/"reports"/"index.json",[])
        # Only replay the newly produced edition files and this run's status.
        # Never restore old copies of all reports over newer remote files.
        current_date=report_index[0].get("date") if report_index else None
        if not current_date or not (backup/"reports"/f"{current_date}.json").exists():
            raise RuntimeError("Missing generated report and index; refusing publication")
        for attempt in range(1,max_attempts+1):
            git("fetch","origin","main")
            git("reset","--hard","origin/main")
            remote=read_json(REPORTS/"index.json",[])
            local=read_json(backup/"reports"/"index.json",[])
            REPORTS.mkdir(parents=True,exist_ok=True)
            # Do not regress a report already published for the same date:
            # last completed generation wins if it has a newer update timestamp.
            incoming=read_json(backup/"reports"/f"{current_date}.json",{})
            existing=read_json(REPORTS/f"{current_date}.json",{})
            # An already verified sourced news article outranks a later
            # emergency educational reserve for the same Hong Kong date.
            # Updating content in a slow retry must not downgrade the edition.
            preserve_news=(existing.get("mode") in ("editorial","source_digest")
                           and incoming.get("mode")=="reading_feature" and complete(existing))
            if existing and (preserve_news or not incoming_is_newer(existing,incoming)):
                chosen=existing
                preserve_remote_status=True
            else:
                if not incoming.get("essay"):
                    raise RuntimeError("Generated edition has no English passage")
                if incoming.get("mode") != "reading_feature" and not incoming.get("stories"):
                    raise RuntimeError("Current-news report has no cited sources")
                if not complete(incoming):
                    raise RuntimeError("Generated passage has words without offline Chinese meanings")
                shutil.copy2(backup/"reports"/f"{current_date}.json",REPORTS/f"{current_date}.json")
                chosen=incoming
                preserve_remote_status=False
            combined=merge_index(remote,local)
            combined=[row for row in combined if row["date"]!=current_date]
            chosen_row={
                "date":current_date,
                "headline":chosen.get("headline",""),
                "mode":chosen.get("mode","source_digest"),
                "word_count":chosen.get("word_count",0),
                "stories":len(chosen.get("stories",[])),
                "updated_at":chosen.get("updated_at","")
            }
            combined=merge_index(combined,[chosen_row])
            (REPORTS/"index.json").write_text(json.dumps(combined,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            if status_backup and not preserve_remote_status:
                STATUS.write_bytes(status_backup)
            git("add","site/reports","site/system-status.json")
            if not git("diff","--cached","--name-only").stdout.strip():
                print("[publish] Already up to date")
                return
            git("commit","-m",f"Update AI daily edition {current_date}")
            try:
                git("push","origin","HEAD:main")
                print(f"[publish] Updated {current_date} on attempt {attempt}")
                return
            except subprocess.CalledProcessError:
                if attempt==max_attempts:raise
                time.sleep(min(attempt*2,10))
        raise RuntimeError("Publish retry budget exhausted")

if __name__=="__main__":
    publish()
