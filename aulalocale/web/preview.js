'use strict';
let previewJob=null,previewTimer=null;
function resetPreview(){clearTimeout(previewTimer);previewJob=null;$('preview-player').pause();$('preview-player').removeAttribute('src');$('preview-player').hidden=true;$('preview-original').disabled=true;$('preview-status').textContent='';$('create-preview').disabled=false;$('cancel-preview').hidden=true;}
async function pollPreview(lessonId,jobId){
  const job=await request(`/api/v1/audio-jobs/${jobId}`);if(currentLesson?.id!==lessonId || previewJob?.id!==jobId)return;previewJob=job;
  const active=['queued','running','interrupted'].includes(job.status);$('create-preview').disabled=active;$('cancel-preview').hidden=!active;
  $('preview-status').textContent=active?T`Elaborazione in corso · ${Math.floor(job.progress)}%`:job.status==='completed'?T('Anteprima pronta. Confronta originale e migliorato.'):job.error || job.status;
  if(active)previewTimer=setTimeout(()=>pollPreview(lessonId,jobId).catch(e=>notify(e.message,true)),1000);
  else if(job.status==='completed'){$('preview-player').src=`/api/v1/audio-jobs/${jobId}/audio`;$('preview-player').hidden=false;$('preview-original').disabled=false;}
}
$('create-preview').onclick=async()=>{
  if(!currentLesson)return;const id=currentLesson.id,options=enhancementOptions();
  if(options.method==='voxlock'){notify(T('Le anteprime supportano GTCRN e filtri tradizionali.'),true);return;}
  options.preview_start=Number($('preview-start').value);options.preview_end=Number($('preview-end').value);$('create-preview').disabled=true;
  try{clearTimeout(previewTimer);$('preview-player').pause();$('preview-player').hidden=true;$('preview-original').disabled=true;previewJob=await request(`/api/v1/lessons/${id}/enhancements`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(options)});if(currentLesson?.id===id)await pollPreview(id,previewJob.id);}catch(e){$('create-preview').disabled=false;notify(e.message,true);}
};
$('cancel-preview').onclick=async()=>{if(previewJob){await request(`/api/v1/audio-jobs/${previewJob.id}/cancel`,{method:'POST'});if(currentLesson)await pollPreview(currentLesson.id,previewJob.id);}};
$('preview-original').onclick=async()=>{if(!previewJob?.preview)return;$('preview-player').pause();await switchAudio(false);await listenSegment(previewJob.preview);};
$('preview-player').onplay=()=>{$('player').pause();previewRange=null;};
$('player').addEventListener('play',()=>{$('preview-player').pause();});
