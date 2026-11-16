'use strict';
let currentTranscript = null, transcriptDirty = false, studyTimer = null;
let transcriptPage = 0, historicalTranscript = false, transcriptHead = null;
const TRANSCRIPT_PAGE_SIZE = 40;
let reviewCursor=null, previewRange=null, transcriptSaving=false;
let activeStudyJob = null, activeView = 'library', notesTimer = null, modelsTimer = null;
let currentNotes = null, editingChapter = null, historicalNotes=null;
function mayLeaveTranscript() { return (!transcriptDirty && !window.aulalocaleSpeakersDirty && !(typeof workspaceHasUnsavedChanges==='function' && workspaceHasUnsavedChanges())) || window.confirm(T('Ci sono correzioni non salvate. Vuoi abbandonarle?')); }
const readableTime = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2,'0')}`;
function resetStudy() {
  if(typeof resetSpeakers==='function')resetSpeakers();
  clearTimeout(studyTimer); reviewCursor=null;previewRange=null;$('transcription-source').value='original';$('transcript-search').value='';$('only-unreviewed').checked=false;$('repeat-passage').checked=false; transcriptPage=0;historicalTranscript=false;transcriptHead=null;$('transcript-pagination').hidden=true;$('transcript-history').replaceChildren();$('transcript-history').disabled=true; currentTranscript = null; transcriptDirty = false; activeStudyJob = null;
  $('transcript-segments').replaceChildren(); $('transcript-review-summary').textContent='';$('transcript-provenance').textContent='';$('next-unreviewed').disabled=true; $('save-transcript').hidden = true;
  $('study-progress').hidden = true; $('cancel-study').hidden = true;
  if(typeof updateTranscriptExport==='function')updateTranscriptExport();
  $('transcript-revision').textContent = ''; $('transcript-status').textContent = T('Trascrizione italiana con timestamp e correzioni manuali.');
  $('transcribe-lesson').disabled = false; $('transcribe-lesson').hidden = false; $('transcribe-lesson').textContent=T('Trascrivi sul dispositivo');
}
function showStudyView(view) {
  if(view!=='library')$('preview-player').pause();
  activeView = view; clearTimeout(notesTimer); clearTimeout(modelsTimer);
  for (const name of ['library','notes','models','search','templates','preferences']) if($(name+'-view'))$(name+'-view').hidden = name !== view;
  $('view-library').setAttribute('aria-pressed',String(view === 'library'));
  $('view-notes').setAttribute('aria-pressed',String(view === 'notes'));
  for(const name of ['search','templates','preferences'])if($('view-'+name))$('view-'+name).setAttribute('aria-pressed',String(view===name));
  if(typeof workspaceRoute==='function')workspaceRoute(view);
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
  const query=$('transcript-search').value.trim().toLocaleLowerCase(I18n.locale),reviewed=reviewedSegments();
  return currentTranscript.segments.filter(s=>(!$('only-unreviewed').checked || !reviewed.has(s.id)) && (!query || s.text.toLocaleLowerCase(I18n.locale).includes(query)));
}
function renderReviewSummary(){
  if(!currentTranscript){$('transcript-review-summary').textContent='';$('transcript-provenance').textContent='';return;}
  const count=reviewedSegments().size,total=currentTranscript.segments.length;
  $('transcript-review-summary').textContent=T`${count} di ${total} passaggi rivisti all’ascolto${transcriptDirty?T(' · modifiche da salvare'):''}`;
  $('transcript-provenance').textContent=T`Whisper Turbo · ${currentTranscript.metadata.source==='enhanced'?T('audio migliorato'):currentTranscript.metadata.source==='original'?T('originale normalizzato'):T('origine non registrata')} · ${historicalTranscript?T('revisione storica'):currentTranscript.metadata.manual?T('revisione manuale protetta'):T('testo automatico da controllare')}`;
  $('next-unreviewed').disabled=historicalTranscript || count===total;
}
async function listenSegment(segment){
  reviewCursor=segment.id;previewRange={start:segment.start,end:segment.end};seekTo(segment.start);
  try{await $('player').play();}catch{notify(T('Premi Play per riascoltare il passaggio.'),true);}
}
function renderTranscript() {
  if(typeof updateTranscriptExport==='function')updateTranscriptExport();
  $('transcript-segments').replaceChildren();
  renderReviewSummary();if (!currentTranscript) return;
  $('transcript-revision').textContent=(historicalTranscript?T('Storica · '):T('Revisione '))+currentTranscript.revision;
  $('transcribe-lesson').hidden=false; $('transcribe-lesson').textContent=currentTranscript.metadata.manual?T('Revisione corretta · protetta'):T('Ritrascrivi con il modello attuale'); $('save-transcript').hidden=historicalTranscript; $('save-transcript').disabled=transcriptSaving || !transcriptDirty;
  const filtered=visibleSegments(),count=filtered.length; transcriptPage=Math.min(transcriptPage,Math.max(0,Math.ceil(count/TRANSCRIPT_PAGE_SIZE)-1));
  $('transcript-pagination').hidden=count<=TRANSCRIPT_PAGE_SIZE; $('transcript-prev').disabled=transcriptPage===0; $('transcript-next').disabled=(transcriptPage+1)*TRANSCRIPT_PAGE_SIZE>=count;
  $('transcript-page-info').textContent=T`${count?transcriptPage*TRANSCRIPT_PAGE_SIZE+1:0}–${Math.min(count,(transcriptPage+1)*TRANSCRIPT_PAGE_SIZE)} di ${count}`;
  if(!count){const empty=document.createElement('p');empty.className='small';empty.textContent=T('Nessun passaggio corrisponde ai filtri.');$('transcript-segments').append(empty);}
  for (const segment of filtered.slice(transcriptPage*TRANSCRIPT_PAGE_SIZE,(transcriptPage+1)*TRANSCRIPT_PAGE_SIZE)) {
    const row=document.createElement('div');row.className='transcript-segment';row.dataset.start=segment.start;row.dataset.end=segment.end;
    const time=document.createElement('button');time.type='button';time.textContent=readableTime(segment.start);time.setAttribute('aria-label',T`Ascolta da ${readableTime(segment.start)}`);time.onclick=()=>listenSegment(segment);
    const text=document.createElement('textarea');text.value=segment.text;text.rows=2;text.readOnly=historicalTranscript || transcriptSaving;text.maxLength=20000;text.setAttribute('aria-label',T`Testo a ${readableTime(segment.start)}`);
    const review=document.createElement('label');review.className='passage-review';
    const check=document.createElement('input');check.type='checkbox';check.checked=reviewedSegments().has(segment.id);check.disabled=historicalTranscript || transcriptSaving;check.setAttribute('aria-label',T`Rivisto all’ascolto a ${readableTime(segment.start)}`);review.append(check,document.createTextNode(T('Rivisto all’ascolto')));
    check.onchange=()=>{const ids=reviewedSegments();check.checked?ids.add(segment.id):ids.delete(segment.id);currentTranscript.metadata.reviewed_segment_ids=[...ids];transcriptDirty=true;$('transcribe-lesson').disabled=true;$('save-transcript').disabled=false;renderReviewSummary();if($('only-unreviewed').checked)renderTranscript();};
    text.oninput=()=>{segment.text=text.value;const ids=reviewedSegments();ids.delete(segment.id);currentTranscript.metadata.reviewed_segment_ids=[...ids];check.checked=false;transcriptDirty=true;$('transcribe-lesson').disabled=true;$('save-transcript').disabled=false;renderReviewSummary();};
    const body=document.createElement('div');if(typeof speakerForSegment==='function'){const name=speakerForSegment(segment);if(name){const voice=document.createElement('span');voice.className='voice-tag';voice.textContent=name;body.append(voice);}}body.append(text,review);row.append(time,body);$('transcript-segments').append(row);
  }
}
async function loadStudy() {
  clearTimeout(studyTimer);if (!currentLesson)return;
  const id=currentLesson.id;
  const [transcript,jobs,revisions]=await Promise.all([request(`/api/v1/lessons/${id}/transcript`,{allowMissing:true}),request(`/api/v1/lessons/${id}/study-jobs`),request(`/api/v1/lessons/${id}/transcript/revisions`)]);
  if (!currentLesson || currentLesson.id!==id)return;
  transcriptHead=transcript;
  $('transcript-history').replaceChildren(); $('transcript-history').disabled=!revisions.length;
  for(const revision of revisions){const option=document.createElement('option');option.value=revision.id;option.textContent=`${revision.revision} · ${revision.metadata.manual?T('correzioni manuali'):revision.metadata.model || 'automatica'}`;option.selected=Boolean(currentTranscript && currentTranscript.id===revision.id);$('transcript-history').append(option);}
  if (transcript && !transcriptDirty && !historicalTranscript && (!currentTranscript || currentTranscript.id!==transcript.id)) {currentTranscript=transcript;renderTranscript();$('transcript-history').value=transcript.id;}
  activeStudyJob=jobs.find(job=>['queued','running','interrupted'].includes(job.status)) || null;
  $('transcribe-lesson').disabled=Boolean(transcriptDirty || transcriptSaving || activeStudyJob || historicalTranscript || currentTranscript && currentTranscript.metadata.manual);
  $('cancel-study').hidden=!activeStudyJob; $('study-progress').hidden=!activeStudyJob;
  if (activeStudyJob) {
    $('study-progress').value=activeStudyJob.progress;
    $('transcript-status').textContent=activeStudyJob.kind==='question'?T('Domanda in elaborazione sul dispositivo.'):activeStudyJob.kind==='pipeline'?(activeStudyJob.stage==='notes'?T('Fase: proposta dispensa'):T('Fase: trascrizione'))+' · '+Math.floor(activeStudyJob.progress)+'%':activeStudyJob.status==='queued'?T('In coda: attendo il motore locale.'):T`${activeStudyJob.kind==='speakers'?T('Analisi parlanti'):T('Trascrizione')} in corso · ${Math.floor(activeStudyJob.progress)}%. L’avanzamento si aggiorna al termine di ogni blocco.`;
    studyTimer=setTimeout(()=>loadStudy().catch(e=>notify(e.message,true)),2000);
  } else if (currentTranscript) $('transcript-status').textContent=historicalTranscript?T('Revisione storica in sola lettura. Scegli l’ultima revisione per modificare.'):T('Testo automatico da verificare ascoltando i timestamp. Le correzioni vengono salvate in una nuova revisione.');
  else $('transcript-status').textContent=jobs[0] && jobs[0].status==='failed'?jobs[0].error:T('Whisper Turbo · italiano · elaborazione sul dispositivo. Installa il modello nella sezione Modelli locali.');
  if($('start-workflow')){$('start-workflow').disabled=Boolean(activeStudyJob || transcriptDirty || historicalTranscript || currentTranscript?.metadata.manual);const pipeline=jobs.find(job=>job.kind==='pipeline');if(pipeline)$('workflow-status').textContent=pipeline.status==='completed'?T('Proposta pronta: apri Dispensa per verificarla.'):pipeline.error || (pipeline.stage==='notes'?T('Fase: proposta dispensa'):T('Fase: trascrizione'));}
}
$('transcribe-lesson').onclick=async()=>{
  if (!currentLesson)return;
  if(transcriptDirty){notify(T('Salva le correzioni prima di avviare un altro lavoro.'),true);return;}
  $('transcribe-lesson').disabled=true;
  try {await request(`/api/v1/lessons/${currentLesson.id}/transcribe`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:$('transcription-language').value,base_revision:currentTranscript?currentTranscript.id:null,audio_job_id:$('transcription-source').value==='enhanced' && currentAudioJob?currentAudioJob.id:null})});await loadStudy();}
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
    notify(T('Correzioni salvate in una nuova revisione. Le dispense già generate possono richiedere un aggiornamento.'));
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
  const hiddenAssets=new Set(result.models.flatMap(model=>model.requires || []));
  const sizeLabel=bytes=>bytes<1048576?(bytes/1024).toFixed(0)+' KiB':bytes<1073741824?(bytes/1048576).toFixed(1)+' MiB':(bytes/1073741824).toFixed(2)+' GiB';
  for(const model of result.models.filter(model=>!hiddenAssets.has(model.id))){
    const assets=[model,...(model.requires || []).map(id=>result.models.find(m=>m.id===id)).filter(Boolean)],complete=assets.every(m=>m.status==='installed');
    const transfers=new Map(assets.map(m=>[m.archive?.sha256 || m.sha256,m.archive?.bytes || m.bytes]));
    const card=document.createElement('article');card.className='model-card';
    const details=document.createElement('div'), title=document.createElement('h3'),meta=document.createElement('p'),status=document.createElement('p');
    title.textContent=T(model.name);meta.textContent=T`${sizeLabel([...transfers.values()].reduce((a,b)=>a+b,0))} · ${model.license} · download verificato`;
    const names={installed:T('Installato · pronto per lavorare offline'),not_installed:T('Da scaricare'),queued:T('In attesa di download'),downloading:T('Download in corso'),verifying:T('Verifica integrità'),failed:model.error};
    status.textContent=complete?names.installed:(model.status==='installed'?T('Completa il download dei modelli collegati'):names[model.status] || model.status);
    if(!result.runtimes[model.task])status.textContent+=T(' · runtime nativo da installare (vedi README)');
    details.append(title,meta,status);
    const progressModel=assets.find(m=>['queued','downloading','verifying'].includes(m.status)),active=Boolean(progressModel);pending ||= active;
    if(active){const progress=document.createElement('progress');progress.max=progressModel.archive?.bytes || progressModel.bytes;progress.value=progressModel.downloaded;progress.setAttribute('aria-label',T`Download ${model.name}`);details.append(progress);}
    const button=document.createElement('button');button.textContent=complete?T('Installato'):active?T('Download…'):T('Scarica modelli');button.disabled=active || complete;
    button.onclick=async()=>{button.disabled=true;try{await request(`/api/v1/models/${model.id}/download`,{method:'POST'});await loadModels();}catch(e){notify(e.message,true);button.disabled=false;}};
    card.append(details,button);$('model-list').append(card);
  }
  if(pending)modelsTimer=setTimeout(()=>loadModels().catch(e=>notify(e.message,true)),1500);
}
async function openSource(ref){
  const lesson=lessons.find(item=>item.id===ref.lesson_id);if(!lesson){notify(T('Lezione sorgente non presente nella lista.'),true);return;}
  showStudyView('library');if(!await openLesson(lesson))return;
  if(currentTranscript && currentTranscript.id!==ref.revision_id){currentTranscript=await request(`/api/v1/transcripts/${ref.revision_id}`);historicalTranscript=true;renderTranscript();$('transcript-history').value=currentTranscript.id;$('transcript-status').textContent=T('Fonte della dispensa: revisione storica in sola lettura.');}
  if(currentTranscript){const index=currentTranscript.segments.findIndex(s=>s.id===ref.segment_id);if(index>=0){transcriptPage=Math.floor(index/TRANSCRIPT_PAGE_SIZE);renderTranscript();}}
  seekTo(ref.start);$('player-panel').scrollIntoView({behavior:'smooth',block:'start'});
}
function renderChapter(chapter,editable,allChapters=currentNotes?.chapters || [],revision=currentNotes?.id){
  const card=document.createElement('article');card.className='chapter-card';card.dataset.chapterId=chapter.id;
  const heading=document.createElement('div');heading.className='chapter-heading';const title=document.createElement('h3');title.textContent=chapter.title;heading.append(title);
  if(editable){const button=document.createElement('button');button.className='text-button';button.textContent=chapter.manual?T('Modifica · protetta'):T('Modifica');button.onclick=()=>{editingChapter=chapter;$('chapter-title').value=chapter.title;$('chapter-text').value=chapter.text;$('chapter-dialog').showModal();};heading.append(button);}
  const text=document.createElement('p');text.className='chapter-text';text.textContent=chapter.text;
  const sources=document.createElement('div');sources.className='sources';
  for(const ref of chapter.sources){const link=document.createElement('button');link.className='source-link';link.textContent=T`↗ ${readableTime(ref.start)} · fonte`;link.title=(lessons.find(l=>l.id===ref.lesson_id)||{}).title||T('Lezione');link.onclick=()=>openSource(ref).catch(e=>notify(e.message,true));const printed=document.createElement('span');printed.className='print-citation';printed.textContent=T`Fonte: ${(lessons.find(l=>l.id===ref.lesson_id)||{}).title||ref.lesson_id}, ${readableTime(ref.start)} · revisione ${ref.revision_id}`;sources.append(link,printed);}
  card.append(heading,text,sources);
  if(revision && chapter.sources.length){const check=document.createElement('button'),output=document.createElement('div');output.className='evidence-output';check.className='text-button';check.textContent=T('Controlla citazioni con IA locale');check.onclick=()=>checkEvidence(revision,chapter.id,check,output).catch(e=>{check.disabled=false;output.textContent=e.message;notify(e.message,true);});card.append(check,output);}
  if(chapter.possible_conflict_with){const warning=document.createElement('p');warning.className='conflict-notice';const other=allChapters.find(c=>c.id===chapter.possible_conflict_with);warning.textContent=T`Possibile contrasto${other?T(' con “')+other.title+'”':''}: confronta entrambe le fonti. Nessuna versione è stata scelta automaticamente.`;if(other){const jump=document.createElement('button');jump.className='text-button';jump.textContent=T('Vai alla sezione da confrontare');jump.onclick=()=>card.parentElement.querySelector(`[data-chapter-id="${other.id}"]`)?.scrollIntoView({behavior:'smooth',block:'center'});warning.append(jump);}card.append(warning);}
if(chapter.reviewed_at || chapter.manual){const state=document.createElement('p');state.className='small';state.textContent=chapter.manual?T('Sezione modificata manualmente · protetta'):T('Sezione controllata dallo studente');card.append(state);}return card;
}
async function loadNotes(){
  clearTimeout(notesTimer);if(!selected){$('notes-status').textContent=T('Crea o scegli una materia per iniziare.');return;}
  const id=selected,result=await request(`/api/v1/subjects/${id}/notes`);if(selected!==id || activeView!=='notes')return;
  if(historicalNotes?.subject_id!==id || historicalNotes?.id===result.current?.id)historicalNotes=null;
  const revisions=await allPages(`/api/v1/subjects/${id}/notes/revisions`);if(selected!==id || activeView!=='notes')return;
  $('notes-history').replaceChildren();$('notes-history').disabled=!revisions.length;
  for(const [revisionIndex,revision] of revisions.entries()){const option=document.createElement('option');option.value=revision.id;option.textContent=(revisions.length-revisionIndex)+' · '+new Date(revision.created_at).toLocaleString(I18n.locale)+(revision.id===result.current?.id?' · '+T('Attuale'):'');$('notes-history').append(option);}
  currentNotes=historicalNotes || result.current;$('notes-history').value=currentNotes?.id || '';
  $('notes-history-status').textContent=historicalNotes?T('Revisione storica in sola lettura. Esportazione e nuove proposte usano la versione attuale.'):'';
  $('generate-source-map').hidden=!currentNotes || Boolean(historicalNotes);$('generate-outline').hidden=!currentNotes || Boolean(historicalNotes);$('notes-content').replaceChildren();$('notes-proposals').replaceChildren();
  const active=result.jobs.find(job=>job.kind==='notes' && ['queued','running','interrupted'].includes(job.status));
  $('generate-notes').disabled=Boolean(active);
  $('notes-status').textContent=active?T`Aggiornamento in preparazione · ${Math.floor(active.progress)}%`:result.current && result.current.stale?T('Alcune fonti sono cambiate. Prepara un aggiornamento e controlla i riferimenti.'):!currentNotes?T('Trascrivi una lezione, poi prepara la prima proposta.'):T`Dispensa salvata · ${new Date(currentNotes.created_at).toLocaleString(I18n.locale)}`;
  if(!active && result.jobs[0] && result.jobs[0].status==='failed')$('notes-status').textContent=result.jobs[0].error;
  const proposal=result.proposals.find(p=>(p.parent_id || null)===(currentNotes?currentNotes.id:null));
  if(proposal && !active) $('notes-status').textContent=T('Proposta pronta: controlla le sezioni e i riferimenti prima di accettarla.');
  if(proposal){
    const box=document.createElement('section');box.className='proposal-card';const title=document.createElement('h3');title.textContent=T('Aggiornamento da verificare');const description=document.createElement('p');description.textContent=T`${proposal.chapters.length} sezioni nella proposta. Le sezioni invariate e le correzioni manuali vengono conservate; controlla le aggiunte, gli aggiornamenti e le eventuali sostituzioni.`;
    const changeMap=new Map((proposal.changes?.chapters || []).map(item=>[item.chapter_id,item]));
    const required=proposal.chapters.filter(c=>!c.manual && !['unchanged','protected'].includes(changeMap.get(c.id)?.kind)),checked=new Set(),removed=proposal.changes?.removed || [],removedChecked=new Set();
    const button=document.createElement('button'),progress=document.createElement('p');progress.className='small';
    const update=()=>{button.textContent=proposal.blocking_stale?T('Fonti cambiate · rigenera'):T('Accetta sezioni controllate');button.disabled=proposal.blocking_stale || checked.size!==required.length || removedChecked.size!==removed.length;progress.textContent=T`${checked.size} di ${required.length} sezioni nuove o aggiornate controllate${removed.length?T` · ${removedChecked.size} di ${removed.length} sostituzioni controllate`:''}. Confronta il testo con le fonti prima di confermare.`;};update();
    button.onclick=async()=>{button.disabled=true;try{await request(`/api/v1/subjects/${id}/notes/${proposal.id}/accept`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewed_chapter_ids:[...checked],reviewed_removed_chapter_ids:[...removedChecked]})});await loadNotes();}catch(e){notify(e.message,true);update();}};
    box.append(title,description);
    for(const chapter of proposal.chapters){const card=renderChapter(chapter,false,proposal.chapters,proposal.id),change=changeMap.get(chapter.id);const state=document.createElement('p');state.className='change-label';state.textContent=({added:T('Nuova sezione'),updated:T('Sezione aggiornata'),unchanged:T('Invariata'),protected:T('Correzioni manuali conservate')})[change?.kind] || T('Sezione da controllare');card.prepend(state);
      if(change?.previous){const before=document.createElement('details'),summary=document.createElement('summary'),text=document.createElement('p');summary.textContent=T('Confronta con la versione attuale');text.className='chapter-text';text.textContent=change.previous.title+'\n\n'+change.previous.text;before.append(summary,text);card.append(before);}
      if(required.some(c=>c.id===chapter.id)){const label=document.createElement('label');label.className='chapter-review';const check=document.createElement('input');check.type='checkbox';check.setAttribute('aria-label',T`Ho controllato la sezione ${chapter.title} e i riferimenti`);check.onchange=()=>{check.checked?checked.add(chapter.id):checked.delete(chapter.id);update();};label.append(check,document.createTextNode(T('Ho controllato questa sezione e i riferimenti')));card.append(label);}box.append(card);}
    if(removed.length){const list=document.createElement('section');list.className='replaced-chapters';const heading=document.createElement('h4');heading.textContent=T('Sezioni precedenti che verranno sostituite');list.append(heading);for(const item of removed){const label=document.createElement('label');label.className='chapter-review';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.onchange=()=>{checkbox.checked?removedChecked.add(item.chapter_id):removedChecked.delete(item.chapter_id);update();};label.append(checkbox,document.createTextNode(T('Ho controllato la sostituzione di: ')+item.title));list.append(label);}box.append(list);}
    box.append(progress,button);$('notes-proposals').append(box);
  }
  if(currentNotes)for(const chapter of currentNotes.chapters)$('notes-content').append(renderChapter(chapter,!historicalNotes));
  $('export-notes').hidden=!currentNotes;$('export-notes').href=`/api/v1/subjects/${id}/notes/export`;$('export-notes').textContent=T('Esporta Markdown ↗');$('print-notes').hidden=!currentNotes;$('export-study').hidden=!currentNotes;$('export-study').href=`/api/v1/subjects/${id}/study-export`;
  await loadMaterials(id);
  if(active)notesTimer=setTimeout(()=>loadNotes().catch(e=>notify(e.message,true)),2000);
}
$('generate-notes').onclick=async()=>{if(!selected)return;$('generate-notes').disabled=true;try{await request(`/api/v1/subjects/${selected}/notes/generate?language=${$('notes-language').value}`,{method:'POST'});await loadNotes();}catch(e){notify(e.message,true);$('generate-notes').disabled=false;}};
$('chapter-form').onsubmit=async event=>{event.preventDefault();if(!currentNotes || !editingChapter || historicalNotes)return;const button=event.submitter;button.disabled=true;try{await request(`/api/v1/subjects/${selected}/notes`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:currentNotes.id,chapter_id:editingChapter.id,title:$('chapter-title').value,text:$('chapter-text').value})});$('chapter-dialog').close();await loadNotes();}catch(e){notify(e.message,true);}finally{button.disabled=false;}};
$('print-notes').onclick=()=>window.print();
window.addEventListener('beforeunload',event=>{if(transcriptDirty || typeof workspaceHasUnsavedChanges==='function' && workspaceHasUnsavedChanges() || typeof workspaceHasPendingImports==='function' && workspaceHasPendingImports()){event.preventDefault();event.returnValue='';}});

async function loadMaterials(id){
  const images=await request(`/api/v1/subjects/${id}/materials`);if(selected!==id || activeView!=='notes')return;
  $('materials-list').replaceChildren();
  for(const material of images){const figure=document.createElement('figure');const img=document.createElement('img');img.src=`/api/v1/materials/${material.id}/image`;img.alt=material.caption||T('Immagine del corso');img.loading='lazy';const caption=document.createElement('figcaption');caption.textContent=material.caption.replace(/^Mappa dei capitoli \(indice, non relazioni causali\) · revisione [a-f0-9-]+/,T('Mappa dei capitoli della dispensa'));figure.append(img,caption);$('materials-list').append(figure);}
}
$('material-file').onchange=async()=>{
  const file=$('material-file').files[0];if(!file || !selected)return;
  if(file.size>20*1024*1024){notify(T('L’immagine supera 20 MiB.'),true);return;}
  const id=selected,form=new FormData();form.append('file',file);form.append('caption',$('material-caption').value.trim());$('material-file').disabled=true;
  try{await request(`/api/v1/subjects/${id}/materials`,{method:'POST',body:form});$('material-caption').value='';if(selected===id)await loadMaterials(id);notify(T('Immagine aggiunta ai materiali della materia.'));}
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
  try{await request(`/api/v1/subjects/${id}/materials/outline`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:currentNotes.id})});await loadMaterials(id);notify(T('Mappa dei capitoli creata e collegata alla revisione della dispensa.'));}
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

$('notes-history').onchange=async()=>{if(!selected)return;const id=selected,revision=$('notes-history').value;try{const result=await request(`/api/v1/subjects/${id}/notes/revisions/${revision}`);if(selected!==id)return;historicalNotes=result;await loadNotes();}catch(e){notify(e.message,true);}};

async function checkEvidence(revision,chapterId,button,output){
  const subjectId=selected;button.disabled=true;output.textContent=T('Controllo locale in corso…');
  let job=await request(`/api/v1/subjects/${subjectId}/notes/${revision}/chapters/${chapterId}/evidence-check`,{method:'POST'});
  const cancel=document.createElement('button');cancel.className='text-button';cancel.textContent=T('Annulla');cancel.onclick=async()=>{cancel.disabled=true;try{await request(`/api/v1/study-jobs/${job.id}/cancel`,{method:'POST'});}catch(e){notify(e.message,true);cancel.disabled=false;}};output.append(cancel);
  while(['queued','running','interrupted'].includes(job.status)){await new Promise(resolve=>setTimeout(resolve,1200));if(!button.isConnected || selected!==subjectId)return;job=await request(`/api/v1/study-jobs/${job.id}`);}
  if(!button.isConnected || selected!==subjectId)return;
  button.disabled=false;if(job.status!=='completed'){output.textContent=job.error || job.status;return;}
  const result=await request(`/api/v1/study-jobs/${job.id}/evidence`);output.replaceChildren();
  const notice=document.createElement('p');notice.className='small';notice.textContent=T('Controllo assistito dal modello, non una certificazione. Verifica le citazioni e le quantità.');output.append(notice);
  for(const item of result.checks){const row=document.createElement('p');row.className='evidence-check';const claim=document.createElement('strong');claim.textContent=({supported:T('Supporto proposto'),unsupported:T('Non supportato'),uncertain:T('Da verificare')})[item.status]+': '+item.claim;row.append(claim);if(item.quote){const quote=document.createElement('blockquote');quote.textContent=item.quote;row.append(quote);}const reason=document.createElement('p');reason.className='small';reason.textContent=item.reason;row.append(reason);output.append(row);}
  if(result.unreviewed_claims){const remainder=document.createElement('p');remainder.textContent=T('Alcune frasi non sono state controllate: limite di otto frasi per verifica.');output.append(remainder);}
}

$('pdf-file').onchange=async()=>{
  const file=$('pdf-file').files[0];if(!file || !selected)return;const id=selected;
  if(file.size>50*1024*1024){notify('PDF exceeds 50 MiB',true);return;}
  $('pdf-file').disabled=true;const form=new FormData();form.append('file',file);
  try{const result=await request(`/api/v1/subjects/${id}/materials/pdf`,{method:'POST',body:form});if(selected===id)await loadMaterials(id);notify(T`Figure estratte: ${result.materials.length}. Avvisi: ${result.warnings.length}.`);}catch(e){notify(e.message,true);}finally{$('pdf-file').disabled=false;$('pdf-file').value='';}
};

$('generate-source-map').onclick=async()=>{if(!selected || !currentNotes || historicalNotes)return;const id=selected;$('generate-source-map').disabled=true;try{await request(`/api/v1/subjects/${id}/materials/source-map?language=${I18n.language}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_revision:currentNotes.id})});if(selected===id)await loadMaterials(id);}catch(e){notify(e.message,true);}finally{$('generate-source-map').disabled=false;}};
$('show-archive-health').onclick=async()=>{$('archive-health-dialog').showModal();$('archive-health-report').textContent=T('Caricamento…');try{const result=await request('/api/v1/archive-health');$('archive-health-report').textContent=JSON.stringify({missing:result.missing,orphan_derivatives:result.orphan_derivatives,unreferenced_originals:result.unreferenced_originals,unclassified:result.unclassified},null,2);}catch(e){$('archive-health-report').textContent=e.message;}};
