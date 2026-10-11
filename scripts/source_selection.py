"""History-aware selection from a bounded RSS event pool, with rejection evidence."""
from __future__ import annotations
import json
from itertools import combinations
from urllib.parse import urlsplit
from source_outline import context_key, compose, RULES
from content_novelty import recent_articles, audit, reused_analysis_fragments


def select(pool,now,reports,diagnostics):
    from build import validate_candidate_sources,parse_entry_date,title_signature,safe_url,source_evidence_metrics,TZ
    if not isinstance(pool,list) or not 1<=len(pool)<=30:
        raise ValueError('Invalid bounded candidate pool')
    day=now.astimezone(TZ).date().isoformat()
    archive=recent_articles(reports,day)
    def identity_keys(s):
        p=urlsplit(safe_url(s['url']))
        return {('url',p.netloc.lower(),p.path),('title',title_signature(s['title']))}
    used=set()
    history_paths=(list(reports.glob('????-??-??.json'))+list((reports/'archive-revisions').glob('*/*.json'))
                   +list((reports.parent.parent/'content-history/retired').glob('????-??-??*.json')))
    for path in history_paths:
        previous=json.loads(path.read_text('utf-8'))
        if previous.get('date','')<day:
            for s in previous.get('stories',[]):used.update(identity_keys(s))
    valid=[];rejected=[];seen=set();unused=[];keys=set()
    for s in pool:
        candidate={**s,'id':'S1'}
        candidate.pop('score',None)
        if not validate_candidate_sources([candidate]): raise ValueError('Malformed candidate pool source')
        names=identity_keys(s)
        age=(now-parse_entry_date({'published':s['published']})).total_seconds()
        reason=None
        if not -1800<=age<=36*3600: reason='expired_or_future_source'
        elif names & (used|seen): reason='reissued_source_identity'
        seen.update(names)
        key=context_key(s)
        if reason:
            rejected.append({'title':s['title'],'url':s['url'],'reason':reason});continue
        valid.append(candidate)
        if key is None: reason='unsupported_legacy_context'
        elif key in keys: reason='duplicate_legacy_context'
        elif any(reused_analysis_fragments(['scope',RULES[key][2],RULES[key][3]],r['essay']) for r in archive):
            reason='legacy_analysis_already_published'
        if reason: rejected.append({'title':s['title'],'url':s['url'],'reason':reason})
        else: unused.append(candidate);keys.add(key)
    if 'stories_selected' in diagnostics:
        diagnostics['rss_initial_stories_selected']=diagnostics['stories_selected']
    def numbered(rows):
        diagnostics['stories_selected']=len(rows)
        return [{**s,'id':f'S{i}'} for i,s in enumerate(rows,1)]
    diagnostics['candidate_pool_count']=len(pool)
    diagnostics['selection_rejections']=rejected
    # Evaluate at most 80 genuinely different event subsets. There is no
    # synonym/date/style rotation of a rejected article.
    tries=0
    for count in (5,4,3):
        for rows in combinations(unused[:12],count):
            tries+=1
            if tries>80: break
            batch=numbered(rows)
            if max(sum(s['publisher']==p for s in batch) for p in {s['publisher'] for s in batch})>2: continue
            essay=compose(batch)
            if essay and source_evidence_metrics(batch)['sufficient'] and audit({'date':day,'mode':'source_digest','headline':'AI evidence review: from '+RULES[context_key(batch[0])][1].split(':')[0].lower()+' to '+RULES[context_key(batch[-1])][1].split(':')[0].lower(),'writing_style':'evidence_audit','stories':batch,'essay':essay},archive)['pass']:
                diagnostics['selection_path']='unused_legacy_analysis';diagnostics['selection_subsets_checked']=tries
                return batch
        if tries>80: break
    # Open-ended analysis can handle new subjects. Preserve source diversity
    # and informative extracts instead of letting a thin high-scoring title
    # crowd out the only substantial evidence.
    valid.sort(key=lambda s:-len(s['excerpt'].split()))
    chosen=[];counts={}
    for s in valid:
        if counts.get(s['publisher'],0)>=2: continue
        chosen.append(s);counts[s['publisher']]=counts.get(s['publisher'],0)+1
        # Three informative sources support eight developed paragraphs and
        # seven questions while bounding CPU authoring on the free runner.
        if len(chosen)==3: break
    diagnostics['selection_path']='source_conditioned_analysis'
    diagnostics['selection_subsets_checked']=tries
    return numbered(chosen)
