"""Recreate 2026-10-08/09/10 using the APP's own offline V3 generators.

The old published documents are solely historical source snapshots. No LLM
operator-authored article text is permitted. Fail closed unless all three
generated articles pass publication checks and pairwise overlap is <16%.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build
import reading_backup
import validate_site
from content_novelty import MAX_FIVE_GRAM_OVERLAP, long_repeats, overlap
from dse_assessment_v7 import make_exam
from edition_guarantee import complete

DAYS = ("2026-10-08", "2026-10-09", "2026-10-10")
LIMIT = 0.16
HK = ZoneInfo("Asia/Hong_Kong")


def dump(path: Path, value: object):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rebuild_preview():
    assert MAX_FIVE_GRAM_OVERLAP == LIMIT, "Public V3 gate must also enforce 16%"
    originals = {
        day: json.loads((ROOT/"site/reports"/(day+".json")).read_text(encoding="utf-8"))
        for day in DAYS
    }
    original_pair = overlap(originals[DAYS[1]]["essay"], originals[DAYS[2]]["essay"])
    if originals[DAYS[0]]["mode"] != "reading_feature":
        raise RuntimeError("Never transform the 8 October educational backfill into fabricated news.")
    if any(originals[day]["mode"] not in ("source_digest", "editorial") or
           len(originals[day]["stories"]) < 3 for day in DAYS[1:]):
        raise RuntimeError("Historical RSS source snapshots are absent or insufficient.")
    # Previously published Chinese glosses serve as an offline cache, not
    # newly fabricated translations. The normal article dictionary gate runs.
    reviewed_words = {}
    for day in DAYS:
        reviewed_words.update(originals[day].get("dictionary", {}))
    make_original_vocabulary = build.make_vocabulary

    def cached_vocabulary(text, path):
        result = dict(reviewed_words)
        result.update(make_original_vocabulary(text, path))
        return result

    base_reports, base_status, base_site = build.REPORTS, build.STATUS_PATH, validate_site.SITE
    try:
        with tempfile.TemporaryDirectory(prefix="english-news-v3-history-") as directory:
            sandbox = Path(directory)/"site"
            shutil.copytree(ROOT/"site", sandbox)
            build.REPORTS = sandbox/"reports"
            build.STATUS_PATH = sandbox/"system-status.json"
            validate_site.SITE = sandbox
            build.make_vocabulary = cached_vocabulary

            # Generate 8 Oct using a DIFFERENT deterministic selection of the
            # programme's original bilingual reading library, not copied prose.
            # The seed is explicitly recorded and the historical-backfill notice
            # from the original remains unchanged.
            rebuilt8 = reading_backup.build_reading("2026-10-09", datetime.now(HK))
            rebuilt8["date"] = DAYS[0]
            rebuilt8["validation_profile"] = "v3"
            rebuilt8["practice"] = make_exam(rebuilt8["essay"], [], DAYS[0])
            rebuilt8["editorial_notice"] = originals[DAYS[0]]["editorial_notice"]
            rebuilt8["quality_note"] = originals[DAYS[0]].get("quality_note", rebuilt8["quality_note"])
            rebuilt8["processing"]["historical_backfill"] = True
            rebuilt8["processing"]["generator_seed_date"] = "2026-10-09"
            rebuilt8["generation_provenance"] = "reading_backup.build_reading (original educational library)"
            if not complete(rebuilt8):
                raise RuntimeError("8 October preview must retain complete offline translations.")
            build.put_report(rebuilt8)

            for day in DAYS[1:]:
                original = originals[day]
                source_clock = datetime.fromisoformat(day+"T23:30:00+08:00")
                # This is historical replay, NOT a claim of fresh news today.
                if not build.build_live(source_clock, None, sources=copy.deepcopy(original["stories"])):
                    state = json.loads(build.STATUS_PATH.read_text(encoding="utf-8"))
                    raise RuntimeError(f"V3 source replay rejected {day}: {state}")
                candidate_file = build.REPORTS/(day+".json")
                rebuilt = json.loads(candidate_file.read_text(encoding="utf-8"))
                rebuilt["generation_provenance"] = "build.build_live + longform.compose_briefing from original dated RSS snapshots"
                rebuilt["source_snapshot_date"] = day
                dump(candidate_file, rebuilt)

            updated_at = datetime.now(HK).isoformat()
            reports = {}
            for day in DAYS:
                target = build.REPORTS/(day+".json")
                article = json.loads(target.read_text(encoding="utf-8"))
                article["history_rebuilt_at"] = updated_at
                article["historical_rebuild"] = True
                article["rebuild_target_max_five_gram_overlap"] = LIMIT
                dump(target, article)
                reports[day] = article

            pairwise = {}
            for i, left in enumerate(DAYS):
                for right in DAYS[i+1:]:
                    score = overlap(reports[left]["essay"], reports[right]["essay"])
                    pairwise[f"{left} / {right}"] = score
                    if score >= LIMIT or long_repeats(reports[left]["essay"], reports[right]["essay"]):
                        raise RuntimeError(f"Cross-day repetition remains too high: {left}, {right}: {score:.3%}")
            index_path = build.REPORTS/"index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            for row in index:
                if row["date"] in reports:
                    report = reports[row["date"]]
                    row.update(headline=report["headline"], mode=report["mode"],
                               word_count=report["word_count"],
                               stories=len(report["stories"]), updated_at=report["updated_at"])
            index.sort(key=lambda item: item["date"], reverse=True)
            dump(index_path, index)
            errors = validate_site.validate()
            if errors:
                raise RuntimeError("Full site publication preflight FAILED: " + "; ".join(errors))

            report_lines = [
                "# V3 historical automatic regeneration — 8–10 October 2026",
                "",
                "Source: existing dated reports' RSS snapshots and the application's own reading library.",
                "The 8 October record remains an educational backfill, not claimed historical news.",
                "Articles were regenerated by Python program execution, not manually authored.",
                "",
                f"Previously measured 9/10 five-token overlap: {original_pair:.1%}",
                "Release acceptance threshold: strictly below 16.0%",
                "",
                "| Editions | New five-token overlap |",
                "|---|---:|",
            ]
            report_lines.extend(f"| {key} | {value:.1%} |" for key, value in pairwise.items())
            report_lines.extend(["", "All three dated articles: 1,000–1,550 words, source/educational labels, 7+ original reading questions, and complete offline Traditional Chinese vocabulary; validate_site: PASS.", "", "No website version, PWA cache namespace, private user data, Supabase settings or localStorage schema was altered."])
            # Transactional publication: only after all reports pass, copy
            # the generated JSON and indexed dates into the checked-out site.
            for day in DAYS:
                shutil.copy2(build.REPORTS/(day+".json"), ROOT/"site/reports"/(day+".json"))
            shutil.copy2(index_path, ROOT/"site/reports/index.json")
            (ROOT/"docs/V3_THREE_DAY_REBUILD_AUDIT.md").write_text(
                "\n".join(report_lines)+"\n", encoding="utf-8"
            )
            print("SUCCESS: three APP-generated V3 editions and strict overlap preflight")
            print("Original 9/10 overlap:", original_pair)
            for key, value in pairwise.items():
                print(f"{key}: {value:.1%}")
            return 0
    finally:
        build.REPORTS, build.STATUS_PATH, validate_site.SITE = base_reports, base_status, base_site
        build.make_vocabulary = make_original_vocabulary


if __name__ == "__main__":
    # Reconstruction never mutates the active published tree.
    destination=ROOT/'.cache/history-preview'
    destination.mkdir(parents=True,exist_ok=True)
    base_root=ROOT
    with tempfile.TemporaryDirectory(prefix='history-preview-') as name:
        sandbox=Path(name)
        shutil.copytree(base_root/'site',sandbox/'site')
        (sandbox/'docs').mkdir()
        ROOT=sandbox
        try:
            result=rebuild_preview()
            shutil.copytree(sandbox/'site/reports',destination/'reports',dirs_exist_ok=True)
            shutil.copytree(sandbox/'docs',destination/'docs',dirs_exist_ok=True)
            print('Preview retained:',destination)
        finally:
            ROOT=base_root
    raise SystemExit(result)
