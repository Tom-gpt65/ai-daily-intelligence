"""Transparent quality diagnostics for educational news briefings.

This module DOES NOT certify factual accuracy, HKEAA equivalence or language level.
It detects limited but objective signals before content is offered to learners.
"""
from __future__ import annotations
import re
from collections import Counter

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

MACHINE_ARTIFACTS=(
    re.compile(r"arxiv:\S+\s+announce type:",re.I),
    re.compile(r"(?i)(?:<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])"),
    re.compile(r"(?i)\b(?:as an ai language model|lorem ipsum)\b"),
    re.compile(r"(?m)^\s*(?:SYSTEM PROMPT:|ASSISTANT RESPONSE:|TODO:)\s*"),
    re.compile("\uFFFD"),
)

def contains_machine_artifacts(text: str) -> bool:
    """Reject obvious RSS metadata, prompt wrappers and broken characters."""
    return any(pattern.search(text) for pattern in MACHINE_ARTIFACTS)

def repetition_diagnostics(paragraphs: list[str]) -> dict:
    """Count occurrences, rather than unique shingles which hide repeated blocks.

    Ignore source labels and punctuation; repeating a 16-word fragment or a
    complete meaningful sentence is a publication failure, even across parts
    of paragraphs with otherwise different titles and quotations.
    """
    fragments=Counter()
    sentences=Counter()
    for paragraph in paragraphs:
        cleaned=re.sub(r"\[S\d+\]","",paragraph,flags=re.I)
        tokens=[w.lower() for w in WORDS.findall(cleaned)]
        fragments.update(tuple(tokens[i:i+16]) for i in range(max(0,len(tokens)-15)))
        for sentence in re.split(r"(?<=[.!?])\s+",cleaned):
            terms=tuple(w.lower() for w in WORDS.findall(sentence))
            if len(terms)>=10:
                sentences[terms]+=1
    return {"repeated_sentence_count":sum(n-1 for n in sentences.values() if n>1),
            "repeated_sixteen_word_fragments":sum(n-1 for n in fragments.values() if n>1)}

def outline_issues(paragraphs: list[str], sources: list[dict]) -> list[str]:
    """Verify the actual construction, never trust a saved quality flag."""
    from source_outline import compose
    expected=compose(sources)
    return [] if expected and paragraphs==expected else ["source_outline_mismatch"]

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
        "machine_text_artifacts":contains_machine_artifacts(text),
        **repetition_diagnostics(paragraphs),
    }
    issues=[]
    if contains_machine_artifacts(text): issues.append("machine_text_artifact")
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
    if indicators['repeated_sentence_count']:
        issues.append('repeated_meaningful_sentence')
    if indicators['repeated_sixteen_word_fragments']:
        issues.append('repeated_content_fragment')
    if any(re.match(r"(?i)^\s*(finally|in conclusion|ultimately)\b",p) for p in paragraphs[:-2]):
        issues.append('premature_concluding_transition')
    if len(sentence_lengths)>=8 and long_sentences<2:
        issues.append("limited_complex_sentence_practice")
    return {
        "training_structure_pass":not issues,
        "diagnostics":indicators,
        "issues":issues,
        "notice":"Heuristic writing checks only; not independent fact-checking or an HKEAA grade."
    }
