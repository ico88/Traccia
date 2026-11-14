'use strict';
let currentTranscript = null, transcriptDirty = false, studyTimer = null;
let transcriptPage = 0, historicalTranscript = false, transcriptHead = null;
const TRANSCRIPT_PAGE_SIZE = 40;
let reviewCursor=null, previewRange=null, transcriptSaving=false;
let activeStudyJob = null, activeView = 'library', notesTimer = null, modelsTimer = null;
let currentNotes = null, editingChapter = null;
function mayLeaveTranscript() { return !transcriptDirty || window.confirm('Ci sono correzioni non salvate. Vuoi abbandonarle?'); }
const readableTime = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2,'0')}`;
function resetStudy() {
  clearTimeout(studyTimer); reviewCursor=null;previewRange=null;$('transcription-source').value='original';$('transcript-search').value='';$('only-unreviewed').checked=false;$('repeat-passage').checked=false; transcriptPage=0;historicalTranscript=false;transcriptHead=null;$('transcript-pagination').hidden=true;$('transcript-history').replaceChildren();$('transcript-history').disabled=true; currentTranscript = null; transcriptDirty = false; activeStudyJob = null;
  $('transcript-segments').replaceChildren(); $('transcript-review-summary').textContent='';$('transcript-provenance').textContent='';$('next-unreviewed').disabled=true; $('save-transcript').hidden = true;
  $('study-progress').hidden = true; $('cancel-study').hidden = true;
  $('transcript-revision').textContent = ''; $('transcript-status').textContent = 'Trascrizione italiana con timestamp e correzioni manuali.';
  $('transcribe-lesson').disabled = false; $('transcribe-lesson').hidden = false; $('transcribe-lesson').textContent='Trascrivi sul dispositivo';
}
function showStudyView(view) {
  activeView = view; clearTimeout(notesTimer); clearTimeout(modelsTimer);
  for (const name of ['library','notes','models']) $(name+'-view').hidden = name !== view;
  $('view-library').setAttribute('aria-pressed',String(view === 'library'));
  $('view-notes').setAttribute('aria-pressed',String(view === 'notes'));
}
$('view-library').onclick = () => showStudyView('library');
$('view-notes').onclick = () => { showStudyView('notes'); loadNotes().catch(e=>notify(e.message,true)); };
$('show-models').onclick = () => { showStudyView('models'); loadModels().catch(e=>notify(e.message,true)); };
function seekTo(seconds) {
  const player=$('player');
  if (player.readyState >= 1) player.currentTime=seconds;
  else player.addEventListener('loadedmetadata',()=>{player.currentTime=seconds;},{once:true});
}
function reviewedSegments(){return new Set(currentTranscript?.metadata.reviewed_segment_ids || []);}
function visibleSegments(){
  if(!currentTranscript)return [];
  const query=$('transcript-search').value.trim().toLocaleLowerCase('it'),reviewed=reviewedSegments();
  return currentTranscript.segments.filter(s=>(!$('only-unreviewed').checked || !reviewed.has(s.id)) && (!query || s.text.toLocaleLowerCase('it').includes(query)));
}
function renderReviewSummary(){
  if(!currentTranscript){$('transcript-review-summary').textContent='';$('transcript-provenance').textContent='';return;}
  const count=reviewedSegments().size,total=currentTranscript.segments.length;
  $('transcript-review-summary').textContent=`${count} di ${total} passaggi rivisti all’ascolto${transcriptDirty?' · modifiche da salvare':''}`;
  $('transcript-provenance').textContent=`Whisper Turbo · ${currentTranscript.metadata.source==='enhanced'?'audio migliorato':currentTranscript.metadata.source==='original'?'originale normalizzato':'origine non registrata'} · ${historicalTranscript?'revisione storica':currentTranscript.metadata.manual?'revisione manuale protetta':'testo automatico da controllare'}`;
  $('next-unreviewed').disabled=historicalTranscript || count===total;
}
async function listenSegment(segment){
  reviewCursor=segment.id;previewRange={start:segment.start,end:segment.end};seekTo(segment.start);
  try{await $('player').play();}catch{notify('Premi Play per riascoltare il passaggio.',true);}
}
function renderTranscript() {
  $('transcript-segments').replaceChildren();
  renderReviewSummary();if (!currentTranscript) return;
  $('transcript-revision').textContent=(historicalTranscript?'Storica · ':'Revisione ')+currentTranscript.revision;
  $('transcribe-lesson').hidden=false; $('transcribe-lesson').textContent=currentTranscript.metadata.manual?'Revisione corretta · protetta':'Ritrascrivi con il modello attuale'; $('save-transcript').hidden=historicalTranscript; $('save-transcript').disabled=transcriptSaving || !transcriptDirty;
  const filtered=visibleSegments(),count=filtered.length; transcriptPage=Math.min(transcriptPage,Math.max(0,Math.ceil(count/TRANSCRIPT_PAGE_SIZE)-1));
  $('transcript-pagination').hidden=count<=TRANSCRIPT_PAGE_SIZE; $('transcript-prev').disabled=transcriptPage===0; $('transcript-next').disabled=(transcriptPage+1)*TRANSCRIPT_PAGE_SIZE>=count;
  $('transcript-page-info').textContent=`${count?transcriptPage*TRANSCRIPT_PAGE_SIZE+1:0}–${Math.min(count,(transcriptPage+1)*TRANSCRIPT_PAGE_SIZE)} di ${count}`;
  if(!count){const empty=document.createElement('p');empty.className='small';empty.textContent='Nessun passaggio corrisponde ai filtri.';$('transcript-segments').append(empty);}
  for (const segment of filtered.slice(transcriptPage*TRANSCRIPT_PAGE_SIZE,(transcriptPage+1)*TRANSCRIPT_PAGE_SIZE)) {
    const row=document.createElement('div');row.className='transcript-segment';row.dataset.start=segment.start;row.dataset.end=segment.end;
    const time=document.createElement('button');time.type='button';time.textContent=readableTime(segment.start);time.setAttribute('aria-label',`Ascolta da ${readableTime(segment.start)}`);time.onclick=()=>listenSegment(segment);
    const text=document.createElement('textarea');text.value=segment.text;text.rows=2;text.readOnly=historicalTranscript || transcriptSaving;text.maxLength=20000;text.setAttribute('aria-label',`Testo a ${readableTime(segment.start)}`);
    const review=document.createElement('label');review.className='passage-review';
    const check=document.createElement('input');check.type='checkbox';check.checked=reviewedSegments().has(segment.id);check.disabled=historicalTranscript || transcriptSaving;check.setAttribute('aria-label',`Rivisto all’ascolto a ${readableTime(segment.start)}`);review.append(check,document.createTextNode('Rivisto all’ascolto'));
    check.onchange=()=>{const ids=reviewedSegments();check.checked?ids.add(segment.id):ids.delete(segment.id);currentTranscript.metadata.reviewed_segment_ids=[...ids];transcriptDirty=true;$('transcribe-lesson').disabled=true;$('save-transcript').disabled=false;renderReviewSummary();if($('only-unreviewed').checked)renderTranscript();};
    text.oninput=()=>{segment.text=text.value;const ids=reviewedSegments();ids.delete(segment.id);currentTranscript.metadata.reviewed_segment_ids=[...ids];check.checked=false;transcriptDirty=true;$('transcribe-lesson').disabled=true;$('save-transcript').disabled=false;renderReviewSummary();};
    const body=document.createElement('div');body.append(text,review);row.append(time,body);$('transcript-segments').append(row);
  }
}
async function loadStudy() {
  clearTimeout(studyTimer);if (!currentLesson)return;
  const id=currentLesson.id;
  const [transcript,jobs,revisions]=await Promise.all([request(`/api/v1/lessons/${id}/transcript`,{allowMissing:true}),request(`/api/v1/lessons/${id}/study-jobs`),request(`/api/v1/lessons/${id}/transcript/revisions`)]);
  if (!currentLesson || currentLesson.id!==id)return;
  transcriptHead=transcript;
  $('transcript-history').replaceChildren(); $('transcript-history').disabled=!revisions.length;
  for(const revision of revisions){const option=document.createElement('option');option.value=revision.id;option.textContent=`${revision.revision} · ${revision.metadata.manual?'correzioni manuali':revision.metadata.model || 'automatica'}`;option.selected=Boolean(currentTranscript && currentTranscript.id===revision.id);$('transcript-history').append(option);}
  if (transcript && !transcriptDirty && !historicalTranscript && (!currentTranscript || currentTranscript.id!==transcript.id)) {currentTranscript=transcript;renderTranscript();$('transcript-history').value=transcript.id;}
  activeStudyJob=jobs.find(job=>['queued','running','interrupted'].includes(job.status)) || null;
  $('transcribe-lesson').disabled=Boolean(transcriptDirty || transcriptSaving || activeStudyJob || historicalTranscript || currentTranscript && currentTranscript.metadata.manual);
  $('cancel-study').hidden=!activeStudyJob; $('study-progress').hidden=!activeStudyJob;
  if (activeStudyJob) {
    $('study-progress').value=activeStudyJob.progress;
    $('transcript-status').textContent=activeStudyJob.status==='queued'?'In coda: attendo il motore locale.':`Trascrizione in corso · ${Math.floor(activeStudyJob.progress)}%. L’avanzamento si aggiorna al termine di ogni blocco.`;
    studyTimer=setTimeout(()=>loadStudy().catch(e=>notify(e.message,true)),2000);
  } else if (currentTranscript) $('transcript-status').textContent=historicalTranscript?'Revisione storica in sola lettura. Scegli l’ultima revisione per modificare.':'Testo automatico da verificare ascoltando i timestamp. Le correzioni vengono salvate in una nuova revisione.';
  else $('transcript-status').textContent=jobs[0] && jobs[0].status==='failed'?jobs[0].error:'Whisper Turbo · italiano · elaborazione sul dispositivo. Installa il modello nella sezione Modelli locali.';
}
$('transcribe-lesson').onclick=async()=>{
  if (!currentLesson)return;
  if(transcriptDirty){notify('Salva le correzioni prima di avviare un altro lavoro.',true);return;}
  $('transcribe-lesson').disabled=true;
  try {await request(`/api/v1/lessons/${currentLesson.id}/transcribe`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:'it',base_revision:currentTranscript?currentTranscript.id:null,audio_job_id:$('transcription-source').value==='enhanced' && currentAudioJob?currentAudioJob.id:null})});await loadStudy();}
  catch(e){notify(e.message,true);$('transcribe-lesson').disabled=false;}
};
$('cancel-study').onclick=async()=>{if(activeStudyJob)try{await request(`/api/v1/study-jobs/${activeStudyJob.id}/cancel`,{method:'POST'});await loadStudy();}catch(e){notify(e.message,true);}};
$('save-transcript').onclick=async()=>{
  if(!currentTranscript || !currentLesson)return;
  const lessonId=currentLesson.id, base=currentTranscript.id;
  transcriptSaving=true;renderTranscript();
  try {
    const result=await request(`/api/v1/lessons/${lessonId}/transcript`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:base,reviewed_segment_ids:[...reviewedSegments()],segments:currentTranscript.segments.map(({id,text})=>({id,text}))})});
    if(currentLesson && currentLesson.id===lessonId){currentTranscript=result;transcriptDirty=false;renderTranscript();await loadStudy();}
    notify('Correzioni salvate in una nuova revisione. Le dispense già generate possono richiedere un aggiornamento.');
  }catch(e){notify(e.message,true);}
  finally{transcriptSaving=false;if(currentLesson && currentLesson.id===lessonId)renderTranscript();}
};
$('player').addEventListener('timeupdate',()=>{
  const position=$('player').currentTime;
  if(previewRange && position>=previewRange.end){if($('repeat-passage').checked)seekTo(previewRange.start);else{$('player').pause();previewRange=null;}}
  for(const row of document.querySelectorAll('.transcript-segment'))row.classList.toggle('active',Number(row.dataset.start)<=position && Number(row.dataset.end)>position);
});
async function loadModels(){
  clearTimeout(modelsTimer);const result=await request('/api/v1/models');if(activeView!=='models')return;
  $('model-list').replaceChildren();let pending=false;
  for(const model of result.models){
    const card=document.createElement('article');card.className='model-card';
    const details=document.createElement('div'), title=document.createElement('h3'),meta=document.createElement('p'),status=document.createElement('p');
    title.textContent=model.name;meta.textContent=`${(model.bytes<1048576?(model.bytes/1024).toFixed(0)+' KiB':(model.bytes/1073741824).toFixed(2)+' GiB')} · ${model.license} · download verificato`;
    const names={installed:'Installato · pronto per lavorare offline',not_installed:'Da scaricare',queued:'In attesa di download',downloading:'Download in corso',verifying:'Verifica integrità',failed:model.error};
    status.textContent=names[model.status] || model.status;
    if(!result.runtimes[model.task])status.textContent+=' · runtime nativo da installare (vedi README)';
    details.append(title,meta,status);
    const active=['queued','downloading','verifying'].includes(model.status);pending ||= active;
    if(active){const progress=document.createElement('progress');progress.max=model.bytes;progress.value=model.downloaded;progress.setAttribute('aria-label',`Download ${model.name}`);details.append(progress);}
    const button=document.createElement('button');button.textContent=model.status==='installed'?'Installato':active?'Download…':'Scarica modello';button.disabled=active || model.status==='installed';
    button.onclick=async()=>{button.disabled=true;try{await request(`/api/v1/models/${model.id}/download`,{method:'POST'});await loadModels();}catch(e){notify(e.message,true);button.disabled=false;}};
    card.append(details,button);$('model-list').append(card);
  }
  if(pending)modelsTimer=setTimeout(()=>loadModels().catch(e=>notify(e.message,true)),1500);
}
async function openSource(ref){
  const lesson=lessons.find(item=>item.id===ref.lesson_id);if(!lesson){notify('Lezione sorgente non presente nella lista.',true);return;}
  showStudyView('library');if(!await openLesson(lesson))return;
  if(currentTranscript && currentTranscript.id!==ref.revision_id){currentTranscript=await request(`/api/v1/transcripts/${ref.revision_id}`);historicalTranscript=true;renderTranscript();$('transcript-history').value=currentTranscript.id;$('transcript-status').textContent='Fonte della dispensa: revisione storica in sola lettura.';}
  if(currentTranscript){const index=currentTranscript.segments.findIndex(s=>s.id===ref.segment_id);if(index>=0){transcriptPage=Math.floor(index/TRANSCRIPT_PAGE_SIZE);renderTranscript();}}
  seekTo(ref.start);$('player-panel').scrollIntoView({behavior:'smooth',block:'start'});
}
function renderChapter(chapter,editable,allChapters=currentNotes?.chapters || []){
  const card=document.createElement('article');card.className='chapter-card';card.dataset.chapterId=chapter.id;
  const heading=document.createElement('div');heading.className='chapter-heading';const title=document.createElement('h3');title.textContent=chapter.title;heading.append(title);
  if(editable){const button=document.createElement('button');button.className='text-button';button.textContent=chapter.manual?'Modifica · protetta':'Modifica';button.onclick=()=>{editingChapter=chapter;$('chapter-title').value=chapter.title;$('chapter-text').value=chapter.text;$('chapter-dialog').showModal();};heading.append(button);}
  const text=document.createElement('p');text.className='chapter-text';text.textContent=chapter.text;
  const sources=document.createElement('div');sources.className='sources';
  for(const ref of chapter.sources){const link=document.createElement('button');link.className='source-link';link.textContent=`↗ ${readableTime(ref.start)} · fonte`;link.title=(lessons.find(l=>l.id===ref.lesson_id)||{}).title||'Lezione';link.onclick=()=>openSource(ref).catch(e=>notify(e.message,true));const printed=document.createElement('span');printed.className='print-citation';printed.textContent=`Fonte: ${(lessons.find(l=>l.id===ref.lesson_id)||{}).title||ref.lesson_id}, ${readableTime(ref.start)} · revisione ${ref.revision_id}`;sources.append(link,printed);}
  card.append(heading,text,sources);
  if(chapter.possible_conflict_with){const warning=document.createElement('p');warning.className='conflict-notice';const other=allChapters.find(c=>c.id===chapter.possible_conflict_with);warning.textContent=`Possibile contrasto${other?' con “'+other.title+'”':''}: confronta entrambe le fonti. Nessuna versione è stata scelta automaticamente.`;if(other){const jump=document.createElement('button');jump.className='text-button';jump.textContent='Vai alla sezione da confrontare';jump.onclick=()=>card.parentElement.querySelector(`[data-chapter-id="${other.id}"]`)?.scrollIntoView({behavior:'smooth',block:'center'});warning.append(jump);}card.append(warning);}
if(chapter.reviewed_at || chapter.manual){const state=document.createElement('p');state.className='small';state.textContent=chapter.manual?'Sezione modificata manualmente · protetta':'Sezione controllata dallo studente';card.append(state);}return card;
}
async function loadNotes(){
  clearTimeout(notesTimer);if(!selected){$('notes-status').textContent='Crea o scegli una materia per iniziare.';return;}
  const id=selected,result=await request(`/api/v1/subjects/${id}/notes`);if(selected!==id || activeView!=='notes')return;
  currentNotes=result.current;$('generate-outline').hidden=!currentNotes;$('notes-content').replaceChildren();$('notes-proposals').replaceChildren();
  const active=result.jobs.find(job=>['queued','running','interrupted'].includes(job.status));
  $('generate-notes').disabled=Boolean(active);
  $('notes-status').textContent=active?`Aggiornamento in preparazione · ${Math.floor(active.progress)}%`:result.current && result.current.stale?'Alcune fonti sono cambiate. Prepara un aggiornamento e controlla i riferimenti.':!currentNotes?'Trascrivi una lezione, poi prepara la prima proposta.':`Dispensa salvata · ${new Date(currentNotes.created_at).toLocaleString('it-IT')}`;
  if(!active && result.jobs[0] && result.jobs[0].status==='failed')$('notes-status').textContent=result.jobs[0].error;
  const proposal=result.proposals.find(p=>(p.parent_id || null)===(currentNotes?currentNotes.id:null));
  if(proposal && !active) $('notes-status').textContent='Proposta pronta: controlla le sezioni e i riferimenti prima di accettarla.';
  if(proposal){
    const box=document.createElement('section');box.className='proposal-card';const title=document.createElement('h3');title.textContent='Aggiornamento da verificare';const description=document.createElement('p');description.textContent=`${proposal.chapters.length} sezioni nella proposta. Le sezioni invariate e le correzioni manuali vengono conservate; controlla le aggiunte, gli aggiornamenti e le eventuali sostituzioni.`;
    const changeMap=new Map((proposal.changes?.chapters || []).map(item=>[item.chapter_id,item]));
    const required=proposal.chapters.filter(c=>!c.manual && !['unchanged','protected'].includes(changeMap.get(c.id)?.kind)),checked=new Set(),removed=proposal.changes?.removed || [],removedChecked=new Set();
    const button=document.createElement('button'),progress=document.createElement('p');progress.className='small';
    const update=()=>{button.textContent=proposal.blocking_stale?'Fonti cambiate · rigenera':'Accetta sezioni controllate';button.disabled=proposal.blocking_stale || checked.size!==required.length || removedChecked.size!==removed.length;progress.textContent=`${checked.size} di ${required.length} sezioni nuove o aggiornate controllate${removed.length?` · ${removedChecked.size} di ${removed.length} sostituzioni controllate`:''}. Confronta il testo con le fonti prima di confermare.`;};update();
    button.onclick=async()=>{button.disabled=true;try{await request(`/api/v1/subjects/${id}/notes/${proposal.id}/accept`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewed_chapter_ids:[...checked],reviewed_removed_chapter_ids:[...removedChecked]})});await loadNotes();}catch(e){notify(e.message,true);update();}};
    box.append(title,description);
    for(const chapter of proposal.chapters){const card=renderChapter(chapter,false,proposal.chapters),change=changeMap.get(chapter.id);const state=document.createElement('p');state.className='change-label';state.textContent=({added:'Nuova sezione',updated:'Sezione aggiornata',unchanged:'Invariata',protected:'Correzioni manuali conservate'})[change?.kind] || 'Sezione da controllare';card.prepend(state);
      if(change?.previous){const before=document.createElement('details'),summary=document.createElement('summary'),text=document.createElement('p');summary.textContent='Confronta con la versione attuale';text.className='chapter-text';text.textContent=change.previous.title+'\n\n'+change.previous.text;before.append(summary,text);card.append(before);}
      if(required.some(c=>c.id===chapter.id)){const label=document.createElement('label');label.className='chapter-review';const check=document.createElement('input');check.type='checkbox';check.setAttribute('aria-label',`Ho controllato la sezione ${chapter.title} e i riferimenti`);check.onchange=()=>{check.checked?checked.add(chapter.id):checked.delete(chapter.id);update();};label.append(check,document.createTextNode('Ho controllato questa sezione e i riferimenti'));card.append(label);}box.append(card);}
    if(removed.length){const list=document.createElement('section');list.className='replaced-chapters';const heading=document.createElement('h4');heading.textContent='Sezioni precedenti che verranno sostituite';list.append(heading);for(const item of removed){const label=document.createElement('label');label.className='chapter-review';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.onchange=()=>{checkbox.checked?removedChecked.add(item.chapter_id):removedChecked.delete(item.chapter_id);update();};label.append(checkbox,document.createTextNode('Ho controllato la sostituzione di: '+item.title));list.append(label);}box.append(list);}
    box.append(progress,button);$('notes-proposals').append(box);
  }
  if(currentNotes)for(const chapter of currentNotes.chapters)$('notes-content').append(renderChapter(chapter,true));
  $('export-notes').hidden=!currentNotes;$('export-notes').href=`/api/v1/subjects/${id}/notes/export`;$('export-notes').textContent='Esporta Markdown ↗';$('print-notes').hidden=!currentNotes;$('export-study').hidden=!currentNotes;$('export-study').href=`/api/v1/subjects/${id}/study-export`;
  await loadMaterials(id);
  if(active)notesTimer=setTimeout(()=>loadNotes().catch(e=>notify(e.message,true)),2000);
}
$('generate-notes').onclick=async()=>{if(!selected)return;$('generate-notes').disabled=true;try{await request(`/api/v1/subjects/${selected}/notes/generate`,{method:'POST'});await loadNotes();}catch(e){notify(e.message,true);$('generate-notes').disabled=false;}};
$('chapter-form').onsubmit=async event=>{event.preventDefault();if(!currentNotes || !editingChapter)return;const button=event.submitter;button.disabled=true;try{await request(`/api/v1/subjects/${selected}/notes`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:currentNotes.id,chapter_id:editingChapter.id,title:$('chapter-title').value,text:$('chapter-text').value})});$('chapter-dialog').close();await loadNotes();}catch(e){notify(e.message,true);}finally{button.disabled=false;}};
$('print-notes').onclick=()=>window.print();
window.addEventListener('beforeunload',event=>{if(transcriptDirty){event.preventDefault();event.returnValue='';}});

async function loadMaterials(id){
  const images=await request(`/api/v1/subjects/${id}/materials`);if(selected!==id || activeView!=='notes')return;
  $('materials-list').replaceChildren();
  for(const material of images){const figure=document.createElement('figure');const img=document.createElement('img');img.src=`/api/v1/materials/${material.id}/image`;img.alt=material.caption||'Immagine del corso';img.loading='lazy';const caption=document.createElement('figcaption');caption.textContent=material.caption.replace(/^Mappa dei capitoli \(indice, non relazioni causali\) · revisione [a-f0-9-]+/,'Mappa dei capitoli della dispensa');figure.append(img,caption);$('materials-list').append(figure);}
}
$('material-file').onchange=async()=>{
  const file=$('material-file').files[0];if(!file || !selected)return;
  if(file.size>20*1024*1024){notify('L’immagine supera 20 MiB.',true);return;}
  const id=selected,form=new FormData();form.append('file',file);form.append('caption',$('material-caption').value.trim());$('material-file').disabled=true;
  try{await request(`/api/v1/subjects/${id}/materials`,{method:'POST',body:form});$('material-caption').value='';if(selected===id)await loadMaterials(id);notify('Immagine aggiunta ai materiali della materia.');}
  catch(e){notify(e.message,true);}finally{$('material-file').value='';$('material-file').disabled=false;}
};

$('transcript-prev').onclick=()=>{transcriptPage=Math.max(0,transcriptPage-1);renderTranscript();};
$('transcript-next').onclick=()=>{transcriptPage++;renderTranscript();};
$('transcript-history').onchange=async()=>{
  if(!currentLesson || !mayLeaveTranscript()){$('transcript-history').value=currentTranscript?currentTranscript.id:'';return;}
  const id=$('transcript-history').value,lid=currentLesson.id;
  try{const record=await request(`/api/v1/transcripts/${id}`);if(!currentLesson || currentLesson.id!==lid)return;currentTranscript=record;transcriptDirty=false;historicalTranscript=Boolean(transcriptHead && transcriptHead.id!==record.id);transcriptPage=0;renderTranscript();await loadStudy();}
  catch(e){notify(e.message,true);}
};

$('generate-outline').onclick=async()=>{
  if(!selected || !currentNotes)return;const id=selected,button=$('generate-outline');button.disabled=true;
  try{await request(`/api/v1/subjects/${id}/materials/outline`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:currentNotes.id})});await loadMaterials(id);notify('Mappa dei capitoli creata e collegata alla revisione della dispensa.');}
  catch(e){notify(e.message,true);}finally{button.disabled=false;}
};

$('transcript-search').oninput=()=>{transcriptPage=0;renderTranscript();};
$('only-unreviewed').onchange=()=>{transcriptPage=0;renderTranscript();};
$('next-unreviewed').onclick=()=>{
  if(!currentTranscript)return;
  const all=currentTranscript.segments,reviewed=reviewedSegments(),cursor=all.findIndex(s=>s.id===reviewCursor);
  const next=all.find((s,i)=>i>cursor && !reviewed.has(s.id)) || all.find(s=>!reviewed.has(s.id));
  if(!next)return;previewRange=null;$('transcript-search').value='';reviewCursor=next.id;
  const filtered=visibleSegments();transcriptPage=Math.floor(filtered.findIndex(s=>s.id===next.id)/TRANSCRIPT_PAGE_SIZE);renderTranscript();seekTo(next.start);
  const field=document.querySelector(`.transcript-segment[data-start="${next.start}"] textarea`);if(field){field.focus();field.scrollIntoView({block:'nearest'});}
};
