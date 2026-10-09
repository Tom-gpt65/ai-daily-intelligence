"""Daily question scaffolding and original source-grounded long-form text."""
from longform import compose_briefing, word_count, MIN_WORDS, MAX_WORDS

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
