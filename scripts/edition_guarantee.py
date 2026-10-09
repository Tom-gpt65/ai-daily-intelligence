"""Hard, deterministic word-by-word offline-dictionary gate for all future editions.

Never mark an article as dictionary-complete if any clickable English token has
no actual Traditional Chinese meaning. A non-news educational fallback has a
reviewed fixed bilingual lexicon and does not need any external service.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOKENS=re.compile(r"\b[A-Za-z]+(?:['’\-][A-Za-z]+)*\b")
CJK=re.compile(r"[\u3400-\u9fff]")

def article_words(paragraphs):
    return {w.lower() for paragraph in paragraphs if isinstance(paragraph,str)
            for w in TOKENS.findall(paragraph)}

def actual_meaning(value):
    return (isinstance(value,dict) and isinstance(value.get("translation"),str)
            and bool(CJK.search(value["translation"]))
            and not any(bad in value["translation"] for bad in ("待查", "未收錄", "請查詢", "未提供")))

def load_glossary(name):
    try:
        words=json.loads((ROOT/"site"/name).read_text(encoding="utf-8"))
        return words if isinstance(words,dict) else {}
    except (OSError,TypeError,ValueError):
        return {}

def fill_dictionary(paragraphs, existing, translator=None):
    """Fill exact clickable word forms; no English-only or empty placeholders."""
    words=article_words(paragraphs)
    output=dict(existing) if isinstance(existing,dict) else {}
    glossaries=(load_glossary("news-glossary.json"),load_glossary("reading-glossary.json"),load_glossary("offline-glossary.json"))
    for word in words:
        if actual_meaning(output.get(word)):
            continue
        for glossary in glossaries:
            meaning=glossary.get(word)
            if isinstance(meaning,str) and CJK.search(meaning):
                output[word]={"translation":meaning,"phonetic":"",
                              "part_of_speech":"","definition":""}
                break
        if actual_meaning(output.get(word)):
            continue
        # Conservative suffix candidate only. The displayed surface remains
        # the dictionary key, so even 'concerns' is guaranteed offline.
        stems=[word]
        if len(word)>4:
            if word.endswith("ies"):stems.append(word[:-3]+"y")
            if word.endswith("ing"):stems.extend([word[:-3],word[:-3]+"e"])
            if word.endswith("ed"):stems.extend([word[:-2],word[:-1]])
            if word.endswith("es"):stems.append(word[:-2])
            if word.endswith("s"):stems.append(word[:-1])
            if word.endswith("ly"):stems.append(word[:-2])
        for root in stems[1:]:
            item=output.get(root)
            if actual_meaning(item):
                output[word]={**item}
                break
            for glossary in glossaries:
                meaning=glossary.get(root)
                if isinstance(meaning,str) and CJK.search(meaning):
                    output[word]={"translation":meaning,"phonetic":"",
                                  "part_of_speech":"","definition":""}
                    break
            if actual_meaning(output.get(word)):break
    missing=sorted(word for word in words if not actual_meaning(output.get(word)))
    if missing and translator is not None:
        # The optional local model can fill genuine lexical gaps during news
        # generation. Never use it on the client and never silently accept
        # generic placeholders or missing/English-only meanings.
        for start in range(0,len(missing),60):
            batch=missing[start:start+60]
            try:
                response=translator(
                    "Translate each English word into a short Traditional Chinese dictionary "
                    "meaning. Return ONLY a JSON object using the original words as keys. "
                    "Do not omit words, fabricate parts of speech or add instructions. "
                    "Words may be inflected or proper nouns; use a factual description for "
                    "names without inventing an official Chinese name.\n"
                    +json.dumps(batch,ensure_ascii=False),timeout=300)
                proposed=json.loads(response)
                if not isinstance(proposed,dict):continue
                for word in batch:
                    val=proposed.get(word)
                    if isinstance(val,str) and 1<=len(val.strip())<=90 and CJK.search(val) and not any(bad in val for bad in ("待查", "未知", "無法", "請查詢")):
                        output[word]={"translation":val.strip(),"phonetic":"",
                                      "part_of_speech":"","definition":""}
            except (ValueError,OSError,TypeError,KeyError):
                pass
        missing=sorted(word for word in words if not actual_meaning(output.get(word)))
    return output,missing

def complete(report):
    if not isinstance(report,dict) or not isinstance(report.get("essay"),list):
        return False
    words=article_words(report["essay"])
    dictionary=report.get("dictionary",{})
    return bool(words) and all(actual_meaning(dictionary.get(w)) for w in words)
