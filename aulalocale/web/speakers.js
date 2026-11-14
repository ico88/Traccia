'use strict';
let speakerAnalysis=null,speakerJob=null,speakerTimer=null,speakerPage=0;
window.aulalocaleSpeakersDirty=false;
function resetSpeakers(){clearTimeout(speakerTimer);speakerAnalysis=null;speakerJob=null;speakerPage=0;window.aulalocaleSpeakersDirty=false;$('speaker-labels').replaceChildren();$('speaker-turns').replaceChildren();$('speaker-status').textContent='Le voci vengono distinte automaticamente. Assegna tu il nome Docente: le etichette non identificano le persone.';}
function speakerForSegment(segment){
  if(!speakerAnalysis)return '';
  if(currentTranscript?.id===speakerAnalysis.transcript_revision_id && !window.aulalocaleSpeakersDirty){const id=speakerAnalysis.transcript_speakers?.[segment.id];return id==='overlap'?'Voci sovrapposte':speakerAnalysis.labels[id] || '';}
  const scores=new Map();for(const turn of speakerAnalysis.segments){const overlap=Math.max(0,Math.min(segment.end,turn.end)-Math.max(segment.start,turn.start));scores.set(turn.speaker,(scores.get(turn.speaker)||0)+overlap);}
  const ranked=[...scores].filter(([,amount])=>amount>0).sort((a,b)=>b[1]-a[1]);if(!ranked.length || ranked[0][1]<Math.max(.01,segment.end-segment.start)*.2)return '';
  if(ranked[1] && ranked[1][1]>=ranked[0][1]*.6)return 'Voci sovrapposte';return speakerAnalysis.labels[ranked[0][0]] || ranked[0][0];
}
function renderSpeakers(){
  const active=Boolean(speakerJob);$('analyze-speakers').disabled=active || Boolean(speakerAnalysis?.version);$('save-speakers').hidden=!speakerAnalysis;$('save-speakers').disabled=active || !window.aulalocaleSpeakersDirty;$('cancel-speakers').hidden=!active;
  $('speaker-labels').replaceChildren();$('speaker-turns').replaceChildren();$('speaker-pages').hidden=!speakerAnalysis || speakerAnalysis.segments.length<=20;
  if(!speakerAnalysis)return;
  for(const [id,name] of Object.entries(speakerAnalysis.labels)){const label=document.createElement('label');label.textContent=id;const input=document.createElement('input');input.value=name;input.maxLength=80;input.disabled=active;input.setAttribute('aria-label','Nome del parlante '+id);input.oninput=()=>{speakerAnalysis.labels[id]=input.value;window.aulalocaleSpeakersDirty=true;$('save-speakers').disabled=false;};label.append(input);$('speaker-labels').append(label);}
  const total=speakerAnalysis.segments.length;speakerPage=Math.min(speakerPage,Math.max(0,Math.ceil(total/20)-1));$('speaker-prev').disabled=speakerPage===0;$('speaker-next').disabled=(speakerPage+1)*20>=total;$('speaker-page-info').textContent=`${speakerPage*20+1}–${Math.min(total,(speakerPage+1)*20)} di ${total}`;
  for(const turn of speakerAnalysis.segments.slice(speakerPage*20,(speakerPage+1)*20)){const row=document.createElement('div');row.className='speaker-turn';const play=document.createElement('button');play.className='text-button';play.textContent=readableTime(turn.start)+'–'+readableTime(turn.end);play.setAttribute('aria-label','Ascolta parlante da '+readableTime(turn.start));play.onclick=()=>listenSegment(turn);
    const choice=document.createElement('select');choice.setAttribute('aria-label','Parlante a '+readableTime(turn.start));choice.disabled=active;for(const [id,name] of Object.entries(speakerAnalysis.labels)){const option=document.createElement('option');option.value=id;option.textContent=name;choice.append(option);}choice.value=turn.speaker;choice.onchange=()=>{turn.speaker=choice.value;window.aulalocaleSpeakersDirty=true;$('save-speakers').disabled=false;};
    const reference=document.createElement('button');reference.className='text-button';reference.textContent='Usa come campione docente';reference.disabled=turn.end-turn.start<3;reference.onclick=()=>setIsolationReference(turn.start,Math.min(turn.end,turn.start+10));row.append(play,choice,reference);$('speaker-turns').append(row);
  }
}
async function loadSpeakers(){
  clearTimeout(speakerTimer);if(!currentLesson)return;const id=currentLesson.id;
  const [result,jobs]=await Promise.all([request(`/api/v1/lessons/${id}/speakers`),request(`/api/v1/lessons/${id}/study-jobs`)]);if(currentLesson?.id!==id)return;
  const changed=result && (!speakerAnalysis || speakerAnalysis.job_id!==result.job_id || speakerAnalysis.version!==result.version);
  if(!window.aulalocaleSpeakersDirty && changed){speakerAnalysis=result;speakerPage=0;}
  speakerJob=jobs.find(j=>j.kind==='speakers' && ['queued','running','interrupted'].includes(j.status)) || null;renderSpeakers();
  if(speakerJob){$('speaker-status').textContent=`Analisi parlanti ${speakerJob.status==='queued'?'in coda':'in corso'} · ${Math.floor(speakerJob.progress)}%`;speakerTimer=setTimeout(()=>loadSpeakers().catch(e=>notify(e.message,true)),2000);}
  else if(speakerAnalysis)$('speaker-status').textContent=`${new Set(speakerAnalysis.segments.map(s=>s.speaker)).size} voci proposte · ${speakerAnalysis.version?'correzioni manuali protette':'assegna i ruoli e controlla i passaggi, soprattutto le sovrapposizioni'}.`;
  else{const latest=jobs.find(j=>j.kind==='speakers');if(latest?.status==='failed')$('speaker-status').textContent=latest.error;}
  if(changed && currentTranscript && !transcriptDirty)renderTranscript();
}
$('analyze-speakers').onclick=async()=>{if(!currentLesson)return;$('analyze-speakers').disabled=true;try{await request(`/api/v1/lessons/${currentLesson.id}/speakers`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({num_speakers:Number($('speaker-count').value)})});await loadSpeakers();}catch(e){notify(e.message,true);$('analyze-speakers').disabled=false;}};
$('save-speakers').onclick=async()=>{
  if(!speakerAnalysis || !currentLesson)return;const id=currentLesson.id;$('save-speakers').disabled=true;
  try{const result=await request(`/api/v1/lessons/${id}/speakers`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({base_version:speakerAnalysis.version,labels:speakerAnalysis.labels,assignments:Object.fromEntries(speakerAnalysis.segments.map(s=>[s.id,s.speaker]))})});if(currentLesson?.id!==id)return;speakerAnalysis=result;window.aulalocaleSpeakersDirty=false;renderSpeakers();if(currentTranscript && !transcriptDirty)renderTranscript();notify('Nomi e assegnazioni dei parlanti salvati.');}catch(e){notify(e.message,true);$('save-speakers').disabled=false;}
};
$('cancel-speakers').onclick=async()=>{if(!speakerJob)return;try{await request(`/api/v1/study-jobs/${speakerJob.id}/cancel`,{method:'POST'});await loadSpeakers();}catch(e){notify(e.message,true);}};
$('speaker-prev').onclick=()=>{speakerPage=Math.max(0,speakerPage-1);renderSpeakers();};$('speaker-next').onclick=()=>{speakerPage++;renderSpeakers();};
