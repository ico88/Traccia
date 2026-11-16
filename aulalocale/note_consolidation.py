"""Incremental note planning and bounded thematic consolidation; no cloud services."""
from copy import deepcopy
import re

RECIPE='thematic-v2'


def content(chapter):
    return {key:chapter.get(key) for key in ['title','text','sources','manual']}


def changes(old,chapters):
    previous={c['id']:c for c in old};current={c['id']:c for c in chapters}
    result=[]
    for chapter in chapters:
        before=previous.get(chapter['id'])
        state='protected' if chapter.get('manual') else 'added' if before is None else 'unchanged' if content(before)==content(chapter) else 'updated'
        result.append({'chapter_id':chapter['id'],'kind':state,'previous':deepcopy(before) if state=='updated' else None})
    return {'chapters':result,'removed':[{'chapter_id':c['id'],'title':c['title']} for c in old if c['id'] not in current]}


def plan(old,transcripts):
    revisions={t['lesson_id']:t['id'] for t in transcripts}
    known={}
    for chapter in old:
        # Older question drafts may still carry coverage metadata; their excerpts
        # never establish that the complete source lecture was summarized.
        if chapter.get('generation',{}).get('question_id'):continue
        for lid,rid in chapter.get('generation',{}).get('covered_revisions',{}).items():known.setdefault(lid,set()).add(rid)
    changed={lid for lid,rid in revisions.items() if rid not in known.get(lid,set())}
    # Rebuild connected machine-written chapters when any cited lesson changes.
    affected=set(changed)
    while True:
        expanded=affected | {ref['lesson_id'] for c in old if not c.get('manual') and any(r['lesson_id'] in affected for r in c['sources']) for ref in c['sources']}
        if expanded==affected:break
        affected=expanded
    kept=[deepcopy(c) for c in old if c.get('manual') or not any(r['lesson_id'] in affected for r in c['sources'])]
    return kept,[t for t in transcripts if t['lesson_id'] in affected],revisions


def ref_key(ref):return (ref['lesson_id'],ref['revision_id'],ref['segment_id'])


def candidates(chapters,incoming):
    # BM25-style retrieval weights uncommon topic words and chapter titles.
    # It bounds the local model context; it is not a semantic similarity certificate.
    from collections import Counter
    import math,unicodedata
    stop={'della','delle','degli','nella','nelle','sono','come','questo','questa','the','and','that','with','from','this','these','those','for','del','dei','per','una','uno'}
    def words(text):
        text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
        return [w for w in re.findall(r'\w{3,}',text) if w not in stop]
    options=[(i,c) for i,c in enumerate(chapters) if not c.get('manual') and len(c['text'])+len(incoming['text'])<=3500]
    if not options:return []
    docs=[Counter(words(c['title'])*3+words(c['text'])) for _,c in options];query=set(words(incoming['title'])*3+words(incoming['text']));average=sum(sum(d.values()) for d in docs)/len(docs) or 1
    frequency=Counter(word for d in docs for word in d)
    def rank(index):
        d=docs[index];length=sum(d.values());return sum(math.log(1+(len(docs)-frequency[w]+.5)/(frequency[w]+.5))*d[w]*2.2/(d[w]+1.2*(.25+.75*length/average)) for w in query if d[w])
    return [options[i] for i in sorted(range(len(options)),key=rank,reverse=True)[:12]]


def consolidate(chapters,incoming,ask,source_text):
    options=candidates(chapters,incoming)
    if not options:chapters.append(incoming);return
    # Routing is model-assisted; lexical retrieval only bounds the context.
    payload={'existing':[{'id':i+1,'title':c['title'],'text':c['text'][:400]} for i,(_,c) in enumerate(options)],'incoming':{'title':incoming['title'],'text':incoming['text']}}
    route=ask('route',payload,len(options))
    target=route.get('target')
    if type(target) is not int or not 0<=target<=len(options):raise ValueError('Destinazione tematica non valida. Nessuna proposta salvata.')
    if target==0:chapters.append(incoming);return
    index,existing=options[target-1]
    refs=list({ref_key(ref):ref for ref in existing['sources']+incoming['sources']}.values())
    if any(ref_key(ref) not in source_text for ref in refs):chapters.append(incoming);return
    payload={'existing':{'title':existing['title'],'text':existing['text']},'incoming':{'title':incoming['title'],'text':incoming['text']},'sources':[{'id':i+1,'text':source_text[ref_key(ref)]} for i,ref in enumerate(refs)]}
    import json
    if len(json.dumps(payload,ensure_ascii=False))>12000:chapters.append(incoming);return
    answer=ask('merge',payload,len(refs));action=answer.get('action')
    if action=='separate':chapters.append(incoming);return
    if action=='conflict':incoming['possible_conflict_with']=existing['id'];chapters.append(incoming);return
    if action!='merge':raise ValueError('Risposta di consolidamento non valida.')
    citations=answer.get('citations',[])
    if not citations or any(type(n) is not int or not 1<=n<=len(refs) for n in citations):raise ValueError('Riferimenti del consolidamento non validi.')
    cited={ref_key(refs[n-1]) for n in citations}
    if not cited.intersection(map(ref_key,existing['sources'])) or not cited.intersection(map(ref_key,incoming['sources'])):
        raise ValueError('Il consolidamento deve citare entrambe le fonti.')
    title=str(answer.get('title','')).strip();text=str(answer.get('text','')).strip()
    if not title or not text or len(text)>4000:raise ValueError('Consolidamento incompleto o troppo lungo.')
    # Preserve every input reference for traceability, and the identity of the chapter.
    updated={**existing,'title':title[:200],'text':text,'sources':refs,'manual':False,'generation':incoming['generation']}
    updated.pop('reviewed_at',None)
    chapters[index]=updated


def conflict_label(chapter,chapters):
    target=chapter.get('possible_conflict_with')
    if not target:return None
    other=next((c for c in chapters if c['id']==target),None)
    return 'Possibile contrasto'+(' con “'+other['title']+'”' if other else ' con un’altra sezione')+': confrontare entrambe le fonti.'
