"""Evidence-limited long-form HKDSE Part B2-inspired daily AI reading.

The prose clearly distinguishes reported facts (attributed to RSS source IDs)
from conditional editorial analysis. No fabricated experiments, figures, or
quotes. Original learning scaffolding is not independent news reporting.
"""
from __future__ import annotations
import hashlib
import re

MIN_WORDS=1000
TARGET_MIN=1100
TARGET_MAX=1350
MAX_WORDS=1550

def word_count(text: str) -> int:
    return len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b",text))

def category(story: dict) -> str:
    text=" ".join(str(story.get(k,"")) for k in ("title","topic")).lower()
    if any(t in text for t in ("funding","raises","investment","billion","million","acquisition")):
        return "investment"
    if any(t in text for t in ("policy","regulat","ban","rule","safety","abusive","oversight","law","governance")):
        return "governance"
    if any(t in text for t in ("benchmark","evaluation","preprint","framework","arxiv","research","study","agent")):
        return "research"
    if any(t in text for t in ("chip","computer","device","laptop","pc","hardware","infrastructure")):
        return "hardware"
    if any(t in text for t in ("virus","gene","bio","life form","protein","medical")):
        return "bioscience"
    return "technology"

LENSES={
 "investment": (
    "The financial dimension matters because capital is an expression of expectations, not proof that those expectations will be realised. "
    "An investment announcement may identify participants and a sum of money, yet it leaves open whether the business can turn resources into sustained usefulness. "
    "Readers should distinguish a transaction reported by a publisher from an independent assessment of profitability, technological superiority or market demand. "
    "Even where the headline sounds momentous, neither the scale of a funding round nor the reputation of its backers settles the question of long-term success. "
    "One might reasonably ask whose interests the announcement serves, what risks investors are accepting and which performance indicators would permit a fairer judgement."
 ),
 "research": (
    "Research language has a particular authority, although a named framework is not the same thing as a result validated under every plausible condition. "
    "A benchmark can make comparisons more systematic by specifying tasks and measurements; equally, the choice of tasks may privilege some capabilities while overlooking others. "
    "What would count as a convincing comparison: repeated results, independent replication, realistic operating conditions or an examination of failures? "
    "The answer depends on the claim being made. Readers must therefore separate the approach described in a paper from evidence that the approach consistently works outside the circumstances reported. "
    "If the source is a preprint, the distinction between dissemination and peer review is especially worth preserving."
 ),
 "hardware": (
    "Hardware announcements invite a different form of scrutiny. A new device may be positioned as capable of supporting AI workloads, but a promise of capability is distinct from measured performance for a particular user. "
    "Consider the trade-offs that a buyer or institution would need to evaluate: speed against battery life, local processing against cloud dependence, and novelty against the cost of replacing an adequate existing machine. "
    "Those are questions for comparison, not claims that any one product necessarily excels or fails. "
    "Where specifications are mentioned without reliable benchmarks, treating commercial positioning as an independent verdict would mistake marketing language for evidence. "
    "The public-interest question is how a technical change translates into benefits that can actually be demonstrated."
 ),
 "governance": (
    "Rules governing AI systems illustrate the distance between institutional intentions and actual consequences. "
    "A policy can signal what a provider wishes to discourage, yet the text alone cannot show how consistently an organisation will interpret disputes, detect violations or handle exceptions. "
    "Nor does an announced restriction, by itself, resolve the ethical disagreement about what ought to be restricted in the first place. "
    "A fair analysis would consider enforcement, transparency and accountability, including whether people affected by a decision can challenge it. "
    "Instead of assuming that stronger wording guarantees safer outcomes, the reader should identify which decisions are explicit and which operational details remain unavailable."
 ),
 "bioscience": (
    "Accounts connecting AI with the life sciences require unusually careful distinctions. Designing a hypothetical biological sequence, testing a computational proposal and demonstrating a functioning organism are not equivalent achievements. "
    "Without verifiable experimental details, moving casually between those categories would create a sensational conclusion that the available report might not justify. "
    "The ethical dimension, moreover, cannot be reduced to excitement or alarm: beneficial research, security precautions and responsible oversight must be examined as separate questions. "
    "This paragraph is an invitation to distinguish levels of evidence, not an assertion that any particular experiment succeeded. "
    "A reader should return to the source before repeating claims about physical or biological results."
 ),
 "technology": (
    "The significance of a technology story depends on the task that it addresses, the assumptions built into the proposed solution and the conditions under which it is expected to operate. "
    "A headline provides a starting point, not a complete comparison with existing alternatives. "
    "For a meaningful assessment, readers should ask whose problem is being solved, whether the stated benefit can be measured and what limitations an independent evaluator might find. "
    "Those questions are not evidence that the development is ineffective; rather, they distinguish informed curiosity from automatic endorsement. "
    "Strong reading requires an awareness that the most confident description may not be the most informative one."
 )
}


# A source list can contain several developments in the same domain. Repeating
# the identical paragraph would produce artificial length rather than teaching
# a reader to distinguish the evidence actually supplied by each source.
ALTERNATE_ANGLES=[
 "A further question concerns how a claim would appear to an observer with different priorities. One stakeholder might value speed, another reproducibility, and a third the ability to challenge a decision. These perspectives need not conflict, but they should not be compressed into a single undifferentiated assessment either. Readers should trace the precise wording of this report, identify whose perspective it privileges and ask whether a competing interpretation could also fit the limited evidence. That exercise exposes the assumptions connecting a reported development to a broader claim, and it makes the argument more than a rehearsal of institutional publicity.",
 "The method by which evidence is communicated is almost as important as the evidence itself. A brief source extract is necessarily selective: it may illuminate the purpose of an initiative while omitting measurements, limitations or the people who would experience the consequences. It would be unreasonable to infer dishonesty merely from that absence; equally, it would be careless to treat what has not been described as if it were already proved. The useful analytical move is to state a testable question, explain which information could answer it and avoid allowing a confident headline to do the work of an argument.",
 "The distinction between immediate significance and lasting consequence deserves separate attention. An announcement can matter today because it changes available options or public expectations, even if its future effects remain uncertain. That observation neither guarantees success nor renders the development trivial. For a more defensible judgement, a reader should ask what short-term event the publisher has actually documented and what long-term change is merely being anticipated. The two may eventually coincide, but their relationship requires explanation. Examining that relationship is a useful exercise in concession, qualification and causal reasoning.",
 "The language used to describe responsibility can conceal differences between technical capacity, organisational incentives and human judgement. Those dimensions interact, but none can be substituted for another: a tool may function as intended without being suitable for every purpose, while an institution may articulate worthy principles without providing sufficient evidence of consistent practice. The reader should therefore locate the precise claim within its domain before drawing a wider conclusion. Where a source offers only a compressed description, curiosity is appropriate, whereas certainty about unreported outcomes is not. The central reading skill is calibrated interpretation."
]

LEADS=[
 "AI news is often written in the language of arrival: a technology has emerged, a company has advanced, or a new rule has been announced. Yet the difference between a development and an interpretation of that development is fundamental. In this edition, the cited reports concern distinct aspects of artificial intelligence, and a careful reading must resist the temptation to compress them into one uncomplicated narrative of progress. The challenge is to identify precisely what each source says before considering what, if anything, may reasonably follow from it. Such disciplined inference is central both to informed public judgement and to demanding English comprehension.",
 "Behind every confident technology headline lies an evidential question. What has actually happened, who is making the claim and which important details remain unreported? These questions become harder when the subject shifts rapidly between commercial investment, research, products and institutional governance. This reading exercise approaches the day's reporting as a set of contrasting texts rather than a sequence of victories. Its argument is deliberately qualified: important developments deserve attention, but their significance must be established through careful interpretation rather than the force of a headline alone.",
 "The vocabulary of artificial intelligence is saturated with ambition, from new capabilities to sweeping visions of social change. A sophisticated reader, however, must distinguish between describing an ambition and demonstrating its consequences. The reports gathered here are not interchangeable, and their differences deserve more attention than their shared association with AI. Some concern organisations and incentives; others raise questions about methodology, technology or institutional responsibility. Examining these contrasts reveals how a story's purpose shapes the evidence it offers and the conclusions a reader is entitled to draw."
]

INTROS=[
 "One perspective arises from",
 "The commercial and institutional landscape also appears in",
 "A contrasting dimension becomes visible in",
 "A separate question is raised by",
 "Finally, another part of the debate is illustrated by"
]

FACT_NOTE=(
 "The available RSS extract adds a short description, but not the complete article; the account below accordingly treats the publisher's wording as a reported claim rather than an independently established result. ",
 "The abbreviated description supplies only a limited view of the event, making it especially important to distinguish the content attributed to the source from assumptions introduced by the reader. ",
 "Although the headline establishes the subject of the report, the excerpt does not provide an independent audit of its effects; the following questions should therefore be read as critical analysis rather than additional reporting. ",
 "The feed gives a starting point for evaluating the claim, not an exhaustive record of the underlying evidence. This distinction matters where the apparent implications exceed the material actually available. ",
 "Only an abbreviated source description is present here. The wider consequences discussed below are questions for further investigation, not facts established by this edition. "
)

CROSS=[
 "These differences also expose a problem of comparability. The first account, [{first}], concerns {area_first}, whereas [{second}] turns to {area_second}. A headline about one kind of development cannot be assessed using precisely the same measure as a headline about another. An investment may invite questions about incentives and commercial performance; a proposed research framework invites scrutiny of methods and reproducibility. That contrast does not automatically favour either source. Instead, it shows why readers should specify what they are trying to evaluate before judging the strength of an account. Otherwise, attractive terminology risks taking the place of a defensible comparison.",
 "A further difficulty concerns the relationship between audience and purpose. Material intended to announce a development, discuss an experiment or explain a rule may select different details, not necessarily because its authors are dishonest, but because each text has a different communicative task. The reader's responsibility is to notice that selection. Which voices are represented? What relevant evidence is absent? Could a stakeholder with different interests interpret the same announcement differently? These questions encourage scepticism without cynicism: the absence of detail is a reason to consult additional sources, not permission to invent whichever explanation seems most persuasive.",
 "Language itself can change the impression created by evidence. Expressions such as 'may', 'could' and 'appears to' preserve uncertainty; definitive verbs, by contrast, can imply that a disputed conclusion has already been settled. Conditional constructions are useful precisely because they make a hypothesis distinguishable from an observed result. A reader preparing for an advanced examination should also consider how concession works: acknowledging a genuine possibility before introducing a qualification often strengthens an argument by addressing an anticipated objection. The rhetorical effect is analytical rather than evasive, provided that caution is tied to a specific limitation in the evidence."
]

EXTRA=[
 "What makes these reports useful for reading practice is their variety of implicit claims. In the accounts labelled [{first}] and [{second}], the relevant questions differ, yet both require attention to how information is selected and presented. An effective response to a comprehension question should first identify the writer's stated point, then explain the inference that follows, while acknowledging where the source stops short. Paraphrasing is preferable to copying a headline wholesale, because the task is to show understanding of the relationship between ideas. At the same time, originality must not become speculation: sophisticated vocabulary cannot rescue an answer that introduces unsupported facts.",
 "The broader policy question should not be confused with the narrower technical one. Even if a system were shown to perform well under a particular evaluation, it would not follow that every application of that system was ethically or socially desirable. Conversely, concern about governance does not prove that a technology lacks useful capabilities. Maintaining those distinctions helps the reader avoid false dilemmas. The important skill is to identify exactly where an argument changes level, moving from what a tool can do to what an organisation or society ought to permit. That shift often determines which evidence would be relevant to a fair conclusion."
]

ENDING=(
 "Ultimately, the value of a daily AI briefing lies not in the number of confident claims it repeats, but in the quality of the questions it enables readers to ask. A useful judgement identifies a stated development, names the evidence on which it rests and clarifies the uncertainties that could alter its significance. Consulting the linked original reports is indispensable because an RSS summary cannot establish everything about a story. The intellectual habit worth cultivating is neither automatic enthusiasm nor reflexive suspicion, but proportionate confidence: say what the source supports, explain why it matters, and remain prepared to revise the conclusion."
)

def compose_briefing(stories: list[dict]) -> list[str]:
    entries=[s for s in stories if s.get("id") and s.get("title")][:5]
    if len(entries)<3:
        return []  # Do not pad two headlines into a fake long-form feature.
    digest=hashlib.sha256("|".join(str(s["title"]) for s in entries).encode("utf-8")).digest()
    paragraphs=[LEADS[digest[0]%len(LEADS)]]
    category_occurrences={}
    for i,story in enumerate(entries):
        topic=category(story)
        occurrence=category_occurrences.get(topic,0)
        category_occurrences[topic]=occurrence+1
        analytical_lens=LENSES[topic] if occurrence==0 else ALTERNATE_ANGLES[(occurrence-1+i)%len(ALTERNATE_ANGLES)]
        title=str(story["title"]).strip().replace("\n"," ")
        publisher=str(story.get("publisher") or "the linked publisher").strip()
        anchor=f"[{story['id']}]"
        paragraphs.append(
            f"{INTROS[i]} {publisher}'s account, ‘{title}’ {anchor}. "
            +FACT_NOTE[i]+analytical_lens
        )
    first,second=entries[0],entries[1]
    areas={"investment":"commercial financing","research":"scientific evaluation",
           "hardware":"computing devices","governance":"policy and accountability",
           "bioscience":"biological research","technology":"technological development"}
    for idx,tmpl in enumerate(CROSS):
        if idx==0 and category(first)==category(second):
            paragraphs.append(
                f"The first two accounts, [{first['id']}] and [{second['id']}], both address "
                f"{areas[category(first)]}, but that common label does not make them equivalent. "
                "Each is a separate claim, and the details by which it might be tested need to be "
                "identified rather than assumed. Readers should compare what each headline "
                "specifically emphasises, which information its short extract supplies and how "
                "any missing context could affect interpretation. An apparently shared topic "
                "is therefore a starting point for comparison, not proof of identical methods, "
                "achievements or consequences. The comparison becomes meaningful only when "
                "it preserves those differences."
            )
        else:
            paragraphs.append(tmpl.format(first=first["id"],second=second["id"],
                                          area_first=areas[category(first)],area_second=areas[category(second)]))
    if len(entries)<5:
        paragraphs.append(EXTRA[0].format(first=first["id"],second=second["id"]))
    if len(entries)<4:
        paragraphs.append(EXTRA[1])
    paragraphs.append(ENDING)
    return paragraphs
