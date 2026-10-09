"""Transparent quality diagnostics for educational news briefings.

This module DOES NOT certify factual accuracy, HKEAA equivalence or language level.
It detects limited but objective signals before content is offered to learners.
"""
from __future__ import annotations
import re

WORDS=re.compile(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b")
GENERIC=(
    "should not be mistaken for",
    "cannot be established from",
    "without further evidence",
    "the original evidence",
    "further examination",
    "does not establish",
    "uncertainty rather than",
    "independently verified",
)

def repeated_paragraph_similarity(paragraphs: list[str]) -> float:
    """Highest pairwise four-word shingle overlap, ignoring source-ID labels.

    Catches copy-paste padding where headings/citations vary slightly. Scores
    are heuristic and never certify the factual accuracy of the remaining text.
    """
    shingles=[]
    for paragraph in paragraphs:
        cleaned=re.sub(r"\[S\d+\]","",paragraph,flags=re.I)
        tokens=[w.lower() for w in WORDS.findall(cleaned)]
        shingles.append({
            tuple(tokens[i:i+4]) for i in range(max(0,len(tokens)-3))
        })
    highest=0.0
    for i,first in enumerate(shingles):
        if len(first)<12:
            continue
        for second in shingles[i+1:]:
            if len(second)<12:
                continue
            union=len(first|second)
            if union:
                highest=max(highest,len(first&second)/union)
    return round(highest,3)

def inspect(paragraphs: list[str], sources: list[dict]) -> dict:
    text="\n".join(paragraphs)
    counts=[len(WORDS.findall(p)) for p in paragraphs]
    count=sum(counts)
    ids={s.get("id") for s in sources if s.get("id")}
    cited=set(re.findall(r"\[(S\d+)\]",text))
    source_paragraphs=sum(any(f"[{code}]" in p for code in ids) for p in paragraphs)
    lower=text.lower()
    generic_hits=sum(lower.count(term) for term in GENERIC)
    sentence_lengths=[len(WORDS.findall(s)) for s in re.split(r"(?<=[.!?])\s+",text) if len(WORDS.findall(s))>3]
    long_sentences=sum(n>=24 for n in sentence_lengths)
    repeated_similarity=repeated_paragraph_similarity(paragraphs)
    indicators={
        "word_count":count,
        "paragraph_count":len(paragraphs),
        "cited_sources":len(ids&cited),
        "available_sources":len(ids),
        "source_linked_paragraphs":source_paragraphs,
        "generic_caution_phrases":generic_hits,
        "long_sentence_count":long_sentences,
        "maximum_repeated_paragraph_similarity":repeated_similarity,
    }
    issues=[]
    if not 1000<=count<=1550: issues.append("article_length_outside_training_target")
    if len(paragraphs)<5: issues.append("insufficient_paragraph_structure")
    if len(ids&cited)<min(3,len(ids)): issues.append("insufficient_explicit_source_attribution")
    if len(ids)>=3 and source_paragraphs<3: issues.append("insufficient_event_specific_paragraphs")
    if sum(p.lstrip().lower().startswith("according to") for p in paragraphs)>1:
        issues.append("repetitive_paragraph_openings")
    if len(paragraphs)>0 and generic_hits>len(paragraphs):
        issues.append("generic_qualification_overuse")
    if repeated_similarity>=0.68:
        issues.append("near_duplicate_paragraph_padding")
    if len(sentence_lengths)>=8 and long_sentences<2:
        issues.append("limited_complex_sentence_practice")
    return {
        "training_structure_pass":not issues,
        "diagnostics":indicators,
        "issues":issues,
        "notice":"Heuristic writing checks only; not independent fact-checking or an HKEAA grade."
    }
