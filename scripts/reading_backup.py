"""Publish a dated, independently readable AI-literacy lesson when news fails.

This is NOT today's news. The fixed original educational material and each
English token's Chinese meaning are committed with the website and tested
without internet, a paid API or a local language model.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from build import ROOT, REPORTS, reading_metrics, choose_vocab, put_report, put_status
from dse_assessment_v7 import make_exam
from edition_guarantee import fill_dictionary,complete,article_words
from content_novelty import audit_history

HK=ZoneInfo("Asia/Hong_Kong")

def build_reading(date,now=None,variant=0):
    now=now or datetime.now(timezone.utc)
    bank=json.loads((ROOT/"site"/"reading-library.json").read_text(encoding="utf-8"))
    topics=list(bank["topics"])
    if len(topics)<12:raise ValueError("Reading reserve is incomplete")
    ordinal=datetime.fromisoformat(date).date().toordinal()
    # Select ten original sections from a broad educational library.
    # The arithmetic is deterministic for each date: no paid model, no RSS,
    # and no randomness that could change an already assigned daily lesson.
    # With 24 topics, adjacent days draw non-overlapping topic groups.
    selected=sorted({(ordinal*7+variant+i*5)%len(topics) for i in range(10)})
    if len(selected)!=10:
        raise ValueError("The reserve reading library must support ten unique sections")
    chosen=[topics[i] for i in selected]
    essay=[bank["intro"],*chosen,bank["conclusion"]]
    metrics=reading_metrics(essay)
    if not 1000<=metrics["word_count"]<=1550:
        raise ValueError("Curated reading is outside the 1,000–1,550 word limit")
    dictionary,missing=fill_dictionary(essay,{})
    if missing:
        raise ValueError("Reserved reading missing offline Chinese meanings: "+", ".join(missing[:20]))
    headings=[
        "AI claims and evidence", "Testing and research methods",
        "Financial expectations", "Practical technology",
        "Language and uncertainty", "Comparing sources",
        "Rules and responsibility", "Fairness and inclusion",
        "Learning with technology", "Reliable systems",
        "Transparency and trust", "Public perspectives"
    ]
    labels=bank.get("titles",headings)
    if not isinstance(labels,list) or len(labels)!=len(topics):
        raise ValueError("Reading topic headings and paragraphs are inconsistent")
    featured=labels[selected[(ordinal//3)%len(selected)]]
    report={
        "schema":4,"validation_profile":"v2","date":date,
        "updated_at":now.astimezone(HK).isoformat(),
        "headline":"AI literacy: "+featured,
        "subtitle":"Original extended English reading · Not today's AI news",
        "mode":"reading_feature","demo":False,
        "editorial_notice":"Evergreen educational essay, not a current-news report. No new event or verified source is claimed.",
        "word_count":metrics["word_count"],"essay":essay,
        "translations":[],"reading_metrics":metrics,
        "processing":{"source_count":0,"backup_reading":True,"offline_dictionary_complete":True},
        "quality_note":"原創 AI 素養延伸閱讀，並非今日新聞；每個英文詞均附有離線中文詞義。詞義須按語境判斷。",
        "stories":[],"dictionary":dictionary,"questions":[],
        "practice":make_exam(essay,[],date),
    }
    report["advanced_vocabulary"]=choose_vocab(dictionary)
    if len(report["practice"].get("items",[]))<7 or not complete(report):
        raise ValueError("Reserve reading failed questions or dictionary gate")
    return report


def ensure_reading(today, now=None):
    """Publish only a novel reserve, otherwise retain explicitly dated history.

    A finite educational bank cannot honestly supply unlimited new material.
    Reusing an archived passage does not create a new dated edition or pass
    the originality gate. News can still upgrade it later in the morning.
    """
    now = now or datetime.now(timezone.utc)
    from build import STATUS_PATH, REPORTS, atomic_json
    from edition_contract import issues as edition_issues
    try:
        existing=json.loads((REPORTS/(today+'.json')).read_text(encoding='utf-8'))
        if not edition_issues(existing,reports=REPORTS):
            return existing
    except (OSError, ValueError, TypeError, KeyError):
        pass
    try:
        previous = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(previous.get("checked_at", ""))
        if checked.astimezone(HK).date().isoformat() != today:
            previous = {}
    except (OSError, ValueError, TypeError):
        previous = {}
    failed = previous.get("state") in {
        "feed_error", "no_new_stories", "insufficient_evidence",
        "incomplete_dictionary", "editorial_quality_rejected", "build_failed",
        "repetitive_content", "history_unavailable"}
    for variant in range(24):
        candidate = build_reading(today, now, variant=variant)
        try:
            novelty = audit_history(candidate, REPORTS)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            previous = {**previous, "state": "history_unavailable", "failure_reason": str(exc)}
            failed = True
            break
        if not novelty["pass"]:
            continue
        candidate.update(validation_profile="s1", novelty=novelty)
        if edition_issues(candidate,reports=REPORTS):
            continue
        put_report(candidate)
        if failed:
            atomic_json(STATUS_PATH, {**previous, "latest_date": today, "mode": "reading_feature",
                                     "published_reading_at": candidate["updated_at"]})
        else:
            put_status("published", now, latest_date=today, mode="reading_feature", source_count=0)
        return candidate
    # Keep the original article date and all user progress/answer anchors.
    index = json.loads((REPORTS/"index.json").read_text(encoding="utf-8"))
    if not index:
        raise ValueError("No validated archived reading available")
    original = json.loads((REPORTS/(index[0]["date"]+".json")).read_text(encoding="utf-8"))
    if edition_issues(original, index[0]):
        raise ValueError("Archived backup failed reading/dictionary/questions contract")
    info = {**previous, "schema": 1, "checked_at": now.astimezone(HK).isoformat(),
            "state": previous.get("state") if failed else "reading_reserve_reused",
            "latest_date": original["date"], "mode": original["mode"],
            "backup": {"kind": "archived_reading", "date": original["date"],
                       "requested_date": today, "reason": "No reserve passed the strict 60-day <16% originality gate"}}
    atomic_json(STATUS_PATH, info)
    print("[safe downgrade] No novel reserve accepted; archived reading retained:", original["date"])
    return original

def main():
    from build import REPORTS
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",default=datetime.now(HK).date().isoformat())
    parser.add_argument("--if-missing",action="store_true")
    args=parser.parse_args()
    today=args.date
    if args.if_missing:
        existing=REPORTS/(today+".json")
        try:
            article=json.loads(existing.read_text(encoding="utf-8"))
            from edition_contract import issues as edition_issues
            if article.get("date")==today and not edition_issues(article, reports=REPORTS):
                print(f"[daily] Existing {today} passage is complete ({article['mode']}); keep it")
                return 0
        except (OSError,ValueError,TypeError,AttributeError):
            pass
    if today!=datetime.now(HK).date().isoformat() and not args.date:
        raise ValueError("A past date requires an explicit date argument")
    ensure_reading(today)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
