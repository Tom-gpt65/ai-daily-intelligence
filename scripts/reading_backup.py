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

HK=ZoneInfo("Asia/Hong_Kong")

def build_reading(date,now=None):
    now=now or datetime.now(timezone.utc)
    bank=json.loads((ROOT/"site"/"reading-library.json").read_text(encoding="utf-8"))
    topics=list(bank["topics"])
    if len(topics)<12:raise ValueError("Reading reserve is incomplete")
    ordinal=datetime.fromisoformat(date).date().toordinal()
    # Select ten original sections from a broad educational library.
    # The arithmetic is deterministic for each date: no paid model, no RSS,
    # and no randomness that could change an already assigned daily lesson.
    # With 24 topics, adjacent days draw non-overlapping topic groups.
    selected=sorted({(ordinal*7+i*5)%len(topics) for i in range(10)})
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

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",default=datetime.now(HK).date().isoformat())
    parser.add_argument("--if-missing",action="store_true")
    args=parser.parse_args()
    today=args.date
    if args.if_missing:
        existing=REPORTS/(today+".json")
        try:
            article=json.loads(existing.read_text(encoding="utf-8"))
            if article.get("date")==today and not article.get("demo") and complete(article) and article.get("word_count",0)>=1000 and len(article.get("practice",{}).get("items",[]))>=7:
                print(f"[daily] Existing {today} passage is complete ({article['mode']}); keep it")
                return 0
        except (OSError,ValueError,TypeError,AttributeError):
            pass
    if today!=datetime.now(HK).date().isoformat() and not args.date:
        raise ValueError("A past date requires an explicit date argument")
    previous_status={}
    try:
        from build import STATUS_PATH
        previous_status=json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        checked=datetime.fromisoformat(previous_status.get("checked_at", ""))
        if checked.astimezone(HK).date().isoformat()!=today:previous_status={}
    except (OSError,ValueError,TypeError,AttributeError):
        previous_status={}
    report=build_reading(today)
    put_report(report)
    # Preserve the real failed NEWS attempt when publishing the first reserve.
    # Otherwise a new-day RSS/dictionary failure disappears behind "published".
    failed_state=previous_status.get("state") in {
        "feed_error","no_new_stories","insufficient_evidence",
        "incomplete_dictionary","editorial_quality_rejected","build_failed"}
    if failed_state:
        from build import atomic_json, STATUS_PATH
        atomic_json(STATUS_PATH,{**previous_status,"latest_date":today,
                    "mode":"reading_feature","published_reading_at":report["updated_at"]})
    else:
        put_status("published",datetime.now(timezone.utc),latest_date=today,
               mode="reading_feature",source_count=0,
               fallback_reason="No verified current-news passage was available")
    print(f"[daily] Published clearly labelled educational fallback for {today}; "
          f"{report['word_count']} words; {len(article_words(report['essay']))} offline word forms; "
          f"{len(report['practice']['items'])} questions")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
