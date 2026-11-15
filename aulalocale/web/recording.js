'use strict';
let capture=null;
function isRecording(){return Boolean(capture);}
function releaseCapture(state){for(const track of state.stream.getTracks())track.stop();state.context.close().catch(()=>{});clearInterval(state.timer);}
function recordControls(active){$('record-close').disabled=active;$('record-start').disabled=active;$('record-pause').hidden=!active;$('record-save').hidden=!active;for(const id of ['record-title','record-teacher','record-date','record-input'])$(id).disabled=active;}
async function recordingDrafts(){
  const drafts=await request('/api/v1/recordings');$('record-drafts').replaceChildren();$('record-start').disabled=drafts.length>0;
  for(const draft of drafts){const row=document.createElement('div');row.className='record-draft';const text=document.createElement('p');text.textContent=T`${draft.title} · ${readableTime(draft.duration_seconds)} salvati · ${subjects.find(s=>s.id===draft.subject_id)?.title || T('Materia precedente')}`;const button=document.createElement('button');button.type='button';button.textContent=draft.bytes?T('Recupera e salva lezione'):T('Chiudi bozza vuota');button.onclick=async()=>{button.disabled=true;try{if(draft.bytes){const lesson=await request(`/api/v1/recordings/${draft.id}/finish`,{method:'POST'});if(selected===lesson.subject_id)await selectSubject(selected);notify(T('Registrazione recuperata e conservata come lezione.'));}else await request(`/api/v1/recordings/${draft.id}`,{method:'DELETE'});await recordingDrafts();}catch(e){notify(e.message,true);button.disabled=false;}};row.append(text,button);$('record-drafts').append(row);}
}
$('open-recording').onclick=async()=>{
  if(!selected)return;$('record-title').value=T('Lezione del ')+new Date().toLocaleDateString(I18n.locale);$('record-date').value=new Date().toLocaleDateString('sv-SE');$('record-status').textContent=T('Il microfono viene attivato solo premendo Inizia. I blocchi ricevuti vengono salvati localmente durante la registrazione.');$('record-timer').textContent='0:00';$('record-dialog').showModal();try{const selectedInput=$('record-input').value;$('record-input').replaceChildren(new Option(T('Microfono di sistema'),''));if(navigator.mediaDevices?.enumerateDevices){for(const device of await navigator.mediaDevices.enumerateDevices()){if(device.kind==='audioinput' && device.deviceId){const option=new Option(device.label || T('Microfono disponibile'),device.deviceId);$('record-input').append(option);}}if([...$('record-input').options].some(o=>o.value===selectedInput))$('record-input').value=selectedInput;}await recordingDrafts();}catch(e){notify(e.message,true);}
};
$('record-dialog').addEventListener('cancel',event=>{if(capture){event.preventDefault();notify(T('Ferma e salva la registrazione prima di chiudere.'));}});
$('record-start').onclick=async()=>{
  if(capture || !selected)return;
  const title=$('record-title').value.trim();if(!title){$('record-title').focus();return;}
  $('record-start').disabled=true;let stream,context,state;
  try{
    if(!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode)throw new Error(T('Registrazione non disponibile qui. Usa l’app Mac oppure un browser con HTTPS o localhost.'));
    stream=await navigator.mediaDevices.getUserMedia({audio:{...($('record-input').value?{deviceId:{exact:$('record-input').value}}:{}),channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
    try{context=new AudioContext({sampleRate:16000});}catch{context=new AudioContext();}
    await context.audioWorklet.addModule('/static/pcm-recorder.js');
    const draft=await request('/api/v1/recordings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject_id:selected,title,teacher:$('record-teacher').value.trim(),lecture_date:$('record-date').value || null})});
    const source=context.createMediaStreamSource(stream),node=new AudioWorkletNode(context,'aula-recorder'),mute=context.createGain();mute.gain.value=0;
    state={stream,context,node,draft,queue:Promise.resolve(),sequence:0,frames:0,failed:false,flushed:null};capture=state;
    node.port.onmessage=event=>{
      if(typeof event.data?.level==='number'){$('record-level').value=Math.min(1,event.data.level*5);return;}
      if(event.data?.flushed){state.flushed?.();return;}
      if(state.failed)return;
      const body=event.data,sequence=state.sequence++;state.frames+=body.byteLength/2;
      state.queue=state.queue.then(async()=>{
        for(let attempt=0;attempt<2;attempt++){const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),5000);try{await request(`/api/v1/recordings/${draft.id}/chunks?sequence=${sequence}`,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body,signal:controller.signal});return;}catch(error){if(attempt===1)throw error;}finally{clearTimeout(timeout);}}
      });
      state.queue.catch(error=>{if(state.failed)return;state.failed=true;releaseCapture(state);if(capture===state)capture=null;recordControls(false);$('record-status').textContent=T('Registrazione interrotta. Puoi recuperare i blocchi già salvati; la parte non ricevuta dal servizio può mancare.');notify(error.message,true);recordingDrafts().catch(()=>{});});
    };
    if(context.sampleRate>16000){const lowpass=context.createBiquadFilter(),second=context.createBiquadFilter();for(const filter of [lowpass,second]){filter.type='lowpass';filter.frequency.value=7000;filter.Q.value=Math.SQRT1_2;}source.connect(lowpass);lowpass.connect(second);second.connect(node);}else source.connect(node);node.connect(mute);mute.connect(context.destination);await context.resume();
    state.timer=setInterval(()=>{$('record-timer').textContent=readableTime(state.frames/16000);},500);recordControls(true);$('record-status').textContent=T('Microfono attivo · salvataggio progressivo sul tuo computer o server.');
  }catch(error){if(stream)for(const track of stream.getTracks())track.stop();if(context)context.close().catch(()=>{});capture=null;recordControls(false);$('record-status').textContent=T('Registrazione non avviata. Controlla il permesso del microfono.');notify(error.message,true);await recordingDrafts().catch(()=>{});}
};
$('record-pause').onclick=async()=>{if(!capture)return;const state=capture;if(state.context.state==='running'){await state.context.suspend();for(const track of state.stream.getTracks())track.enabled=false;$('record-pause').textContent=T('Riprendi');$('record-status').textContent=T('In pausa · i blocchi già ricevuti restano salvati.');}else{for(const track of state.stream.getTracks())track.enabled=true;await state.context.resume();$('record-pause').textContent=T('Pausa');$('record-status').textContent=T('Microfono attivo · salvataggio progressivo.');}};
$('record-save').onclick=async()=>{
  if(!capture)return;const state=capture;$('record-save').disabled=true;$('record-pause').disabled=true;
  try{
    if(state.context.state==='suspended')await state.context.resume();
    await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(new Error(T('Chiusura audio non completata: la bozza resta recuperabile.'))),5000);state.flushed=()=>{clearTimeout(timeout);resolve();};state.node.port.postMessage('flush');});
    releaseCapture(state);await state.queue;
    const lesson=await request(`/api/v1/recordings/${state.draft.id}/finish`,{method:'POST'});capture=null;recordControls(false);$('record-dialog').close();if(selected===lesson.subject_id)await selectSubject(selected);notify(T('Registrazione salvata. Ora puoi migliorarla e trascriverla.'));
  }catch(error){releaseCapture(state);capture=null;recordControls(false);$('record-status').textContent=T('I blocchi già salvati restano nella bozza da recuperare.');notify(error.message,true);await recordingDrafts().catch(()=>{});}
  finally{$('record-save').disabled=false;$('record-pause').disabled=false;$('record-pause').textContent=T('Pausa');}
};
window.addEventListener('beforeunload',event=>{if(capture){event.preventDefault();event.returnValue='';}});
