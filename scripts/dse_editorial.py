"""Unendorsed HKDSE Part B2-style, evidence-limited current-affairs reading practice.
Articles contain attributed RSS information and original analytical study material;
they do not reproduce HKEAA papers or claim fact-checking."""
import re

def word_count(text):
    return len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b",text))

def compose_briefing(stories):
    if not stories:return []
    entries=list(stories[:5])
    paragraphs=[
        "The latest wave of artificial-intelligence reporting poses a deceptively difficult question: how much can readers infer from an announcement before examining the evidence behind it? For a technology whose ambitions extend from research laboratories to ordinary workplaces, the distinction matters. A headline may identify an important development, yet the consequences it appears to promise remain provisional until their scope, limitations and practical relevance have been established. Today's selection is therefore best read not as a catalogue of breakthroughs but as an invitation to examine how technological claims acquire credibility."
    ]
    transitions=["One strand of this debate emerges from","A rather different concern surfaces in",
                 "The contrast becomes more apparent in","Another dimension is raised by","Rounding out the picture is"]
    endings=[
      "Without the original evidence, any conclusion must remain qualified.",
      "Its wider consequences cannot be established from an abbreviated extract.",
      "Its importance does not establish the consequences suggested by its headline.",
      "An unresolved question deserves investigation rather than an immediate verdict.",
      "The crucial issue is which consequences can genuinely be inferred."
    ]
    for i,s in enumerate(entries):
        title=str(s.get("title","an AI development")).strip()
        publisher=str(s.get("publisher") or "the cited publisher")
        excerpt=re.sub(r"<[^>]*>"," ",str(s.get("excerpt") or ""))
        excerpt=re.sub(r"(?i)(register now|subscribe now|click here|read more|grab a second of the same pass).*","",excerpt)
        excerpt=' '.join(excerpt.split()[:18]).rstrip(".,; ")
        details=(" Its short description mentions "+excerpt+".") if excerpt else " The feed supplies little further context."
        paragraphs.append(
            f"{transitions[i]} {publisher}'s report, ‘{title}’ [{s.get('id',f'S{i+1}')}]."
            +details+" This is an attributed account, not an independently verified account of results. "+endings[i]
        )
    paragraphs.extend([
        "Seen side by side, these accounts resist a single, uncomplicated verdict. Some titles emphasise possibility; others draw attention to constraints, institutional choices or unresolved risks. Although such distinctions can sharpen a reader's sense of what is at stake, they cannot substitute for checking how claims were obtained. A commercial announcement, for example, may establish what an organisation says it intends to offer without showing how reliably the product works in different settings. Equally, a research abstract may describe a promising method without demonstrating that its findings will generalise beyond the conditions in which it was evaluated.",
        "A cautious stance is not the same as blanket scepticism. The former asks what would count as convincing evidence; the latter risks rejecting evidence before considering it. Readers should therefore distinguish a source's stated claim, the supporting information actually supplied, and any wider interpretation they themselves add. Where the description is abbreviated, the appropriate response is to acknowledge uncertainty rather than conceal it behind impressive terminology. This method of reading also helps reveal the writer's tone: measured and inquisitive rather than triumphalist or dismissive.",
        "Ultimately, understanding AI news requires more than recognising prominent companies or technical terms. The most defensible judgement is often provisional: it identifies what can presently be said, specifies what cannot, and explains which further facts might alter the conclusion. Consulting the linked originals matters precisely because the short extracts used here cannot settle those questions. A reader who can distinguish evidence from implication has gained something more enduring than another list of headlines: a way to evaluate tomorrow's news as well."
    ])
    if word_count(' '.join(paragraphs))<550:
        paragraphs.insert(-1,
         "Because descriptions are necessarily selective, omissions may be as important as what is emphasised. A responsible comparison should ask whose interests are represented, whether contrary evidence is available, and which assumptions the discussion leaves unstated. This is not a reason to dismiss the reports; instead, it is an invitation to treat apparently conclusive language with care while seeking information capable of challenging the original interpretation."
        )
    return paragraphs

def make_practice(stories,mode="source_digest"):
    ids=[str(s.get("id",f"S{i+1}")) for i,s in enumerate(stories[:2])]
    refs=["["+x+"]" for x in ids] + ["[S2]"]*2
    items=[]
    if mode=="source_digest":
        mc=[
          ("Main idea / writer's purpose","Which statement best conveys the central argument of the passage?",
           ["All technological announcements should be rejected.","A headline alone cannot establish the full significance of a development.","Only academic research can provide reliable information.","Newspapers and technology companies have identical purposes."],1,
           "The opening and conclusion distinguish announcements from evidence.","Opening and final paragraphs"),
          ("Vocabulary in context","In the final paragraph, 'provisional' is closest in meaning to ...",
           ["officially approved","temporary and open to revision","completely unsupported","unlikely to be challenged"],1,
           "A provisional conclusion may change when more facts appear.","Final paragraph"),
          ("Inference","What can reasonably be inferred from the comparison between a commercial announcement and a research abstract?",
           ["Both automatically prove their claims.","A stated intention is identical to effectiveness.","Different sources require different supporting evidence.","Research abstracts should never be consulted."],2,
           "The paragraph points out different evidential gaps.","Comparative analysis paragraph"),
          ("Tone and attitude","How would you best describe the writer's attitude towards the reports?",
           ["Unreservedly enthusiastic","Cautious and analytical","Hostile and accusatory","Humorous and dismissive"],1,
           "Terms such as qualified, uncertainty and measured indicate caution.","Final two paragraphs")
        ]
        items=[{"id":f"Q{i+1}","type":"mc","skill":skill,"marks":1,"stem":stem,"options":options,"answer":correct,"explanation":why,"evidence":evidence}
               for i,(skill,stem,options,correct,why,evidence) in enumerate(mc)]
    items += [
      {"id":"Q5","type":"short","skill":"Short response / evidence","marks":2,
       "stem":"Identify TWO reasons why a reader should avoid treating an RSS summary as conclusive evidence. Answer in your own words.",
       "guidance":["One mark for each distinct valid reason supported by the passage.","Accept missing methods/limitations, shortened context, uncertain outcomes or lack of independent testing."],
       "evidence":"Opening and analytical paragraphs"},
      {"id":"Q6","type":"short","skill":"Writer's technique","marks":2,
       "stem":"Explain how the writer uses contrast to develop the argument. Refer to ONE relevant comparison.",
       "guidance":["One mark for identifying a relevant contrast (such as announcement versus outcome).","One mark for showing how it reinforces the need for qualified judgement."],
       "evidence":"Comparative paragraph"},
      {"id":"Q7","type":"extended","skill":"Cross-source synthesis (B2-style)","marks":4,
       "stem":f"Compare the information in {refs[0] if ids else '[S1]'} and {refs[1]}. What can be inferred, and what cannot be concluded without further verification? (60–90 words.)",
       "guidance":["Identify the focus of each source (2 marks).","Make a coherent comparison referencing both (1 mark).","Specify an evidential limitation without fabricating findings (1 mark)."],
       "evidence":"Two attributed story paragraphs and links to original reporting"}
    ]
    return {"label":"HKDSE Paper 1 Part B2-style practice","official":False,
            "instructions":"Independent exercises inspired by HKEAA assessment skills, not official exam questions.",
            "items":items}
