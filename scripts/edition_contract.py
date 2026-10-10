"""Shared reading acceptance for publication, monitoring and recovery.

No network, private data or manual prose. Structural checks do not prove facts.
"""
from __future__ import annotations
import re
import json
import hashlib
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo
from edition_guarantee import complete
from content_novelty import audit_history

HK = ZoneInfo("Asia/Hong_Kong")
ROOT = Path(__file__).resolve().parents[1]
TOKENS = re.compile(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b")


def issues(report, row=None, reports=None):
    errors = []
    if not isinstance(report, dict):
        return ["invalid_article"]
    try:
        day = date.fromisoformat(report["date"])
        stamp = datetime.fromisoformat(report["updated_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Missing timezone")
    except (KeyError, ValueError, TypeError, AttributeError):
        return ["invalid_date_or_revision"]
    mode = report.get("mode")
    if day.isoformat() > '2026-10-10' and report.get('validation_profile') != 's1':
        errors.append('new_edition_requires_s1_originality')
    if report.get("demo") or mode not in {"reading_feature", "source_digest", "editorial"}:
        errors.append("invalid_mode")
    essay = report.get("essay")
    if not isinstance(essay, list) or not 5 <= len(essay) <= 15 or not all(isinstance(p, str) for p in essay):
        return errors + ["invalid_prose"]
    body = " ".join(essay)
    count = len(TOKENS.findall(body))
    if not 1000 <= count <= 1550 or report.get("word_count") != count:
        errors.append("invalid_word_count")
    if not complete(report):
        errors.append("incomplete_dictionary")
    from editorial_quality import contains_machine_artifacts
    if contains_machine_artifacts(body):
        errors.append("machine_artifacts")
    sources = report.get("stories")
    if mode == "reading_feature":
        if sources != [] or not report.get("subtitle") or not report.get("editorial_notice"):
            errors.append("unlabelled_educational_reading")
    elif mode in {"source_digest", "editorial"}:
        source_clock=stamp
        historic=False
        if report.get('historical_rebuild') and report.get('content_generation_profile')=='source_outline_v2':
            try:
                base=Path(reports) if reports is not None else ROOT/'site/reports'
                preserved=base/'archive-revisions/s1-original'/(day.isoformat()+'.json')
                raw=preserved.read_bytes().replace(b'\r\n',b'\n')
                original=json.loads(raw)
                source_clock=datetime.fromisoformat(report['historical_source_reference_at'])
                if (report.get('source_snapshot_date')!=day.isoformat() or original['date']!=day.isoformat()
                        or original['stories']!=report.get('stories')
                        or report.get('original_revision_sha256')!=hashlib.sha256(raw).hexdigest()
                        or source_clock.tzinfo is None or source_clock.astimezone(HK).date()!=day
                        or stamp<source_clock or report.get('history_rebuilt_at')!=report['updated_at']):
                    raise ValueError('Unproved historical source revision')
                historic=True
            except (OSError, ValueError, TypeError, KeyError):
                errors.append('unproved_historical_source_revision')
        from build import validate_candidate_sources, source_evidence_metrics, parse_entry_date
        if not isinstance(sources, list) or len(sources) < 3 or not validate_candidate_sources(sources):
            errors.append("invalid_news_sources")
        else:
            if not source_evidence_metrics(sources)["sufficient"]:
                errors.append("insufficient_evidence")
            # Historical V3 reconstruction stored its reconstruction time as
            # updated_at; original source_snapshot_date remains disclosed.
            if report.get('validation_profile') == 's1' and any(not -1800 <= (source_clock-parse_entry_date({"published":s["published"]})).total_seconds() <= 36*3600 for s in sources):
                errors.append("expired_or_future_sources")
            if set(re.findall(r"\[(S\d+)\]", body)) != {s["id"] for s in sources}:
                errors.append("invalid_citations")
        if report.get('validation_profile') == 's1' and not historic and stamp.astimezone(HK).date() != day:
            errors.append("news_date_revision_mismatch")
        from editorial_quality import inspect, outline_issues
        checked=inspect(essay,sources if isinstance(sources,list) else [])
        hard={'repeated_meaningful_sentence','repeated_content_fragment','premature_concluding_transition','near_duplicate_paragraph_padding'}
        errors.extend(sorted(hard.intersection(checked['issues'])))
        if report.get('content_generation_profile')=='source_outline_v2':
            errors.extend(outline_issues(essay,sources if isinstance(sources,list) else []))
        elif day.isoformat()>'2026-10-10':
            errors.append('new_news_requires_source_outline_v2')
    practice = report.get("practice")
    items = practice.get("items") if isinstance(practice, dict) else None
    if not isinstance(items, list) or len(items) < 7 or practice.get("official") is True:
        errors.append("missing_practice")
    else:
        if report.get('content_generation_profile')=='source_outline_v2':
            from dse_assessment_v7 import assessment_revision
            if report.get('practice_revision')!=assessment_revision(items):
                errors.append('question_revision_mismatch')
        for q in items:
            if not isinstance(q, dict) or not isinstance(q.get("paragraph"), int) or not 1 <= q["paragraph"] <= len(essay) or not q.get("evidence_quote"):
                errors.append("invalid_question_evidence")
                break
            if report.get("validation_profile") in {"v2", "v3", "s1"}:
                locations = [int(n)-1 for n in re.findall(r"Paragraph (\d+)", str(q.get("evidence", "")))] or [q["paragraph"]-1]
                passages = [re.sub(r"\s+", " ", essay[n]) for n in locations if 0 <= n < len(essay)]
                if any(not fragment.strip() or not any(fragment.strip() in p for p in passages) for fragment in str(q["evidence_quote"]).split(" / ")):
                    errors.append("absent_question_quote")
                    break
    if isinstance(row, dict):
        for key in ("date", "word_count", "updated_at", "mode"):
            if row.get(key) != report.get(key):
                errors.append("index_"+key+"_mismatch")
        if isinstance(sources, list) and row.get("stories") != len(sources):
            errors.append("index_sources_mismatch")
    if report.get("validation_profile") == "s1":
        saved = report.get("novelty", {})
        if not isinstance(saved, dict):
            saved = {}
        if saved.get("pass") is not True or saved.get("threshold") != 0.16 or not isinstance(saved.get("max_overlap"), (int, float)) or not 0 <= saved["max_overlap"] < 0.16:
            errors.append("missing_strict_originality_audit")
        if reports is not None:
            try:
                fresh = audit_history(report, reports)
                if not fresh["pass"]:
                    errors.append("repetitive_content:"+",".join(fresh["issues"]))
            except (OSError, ValueError, KeyError, TypeError):
                errors.append("history_unavailable")
    return sorted(set(errors))
