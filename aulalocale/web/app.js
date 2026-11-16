'use strict';
const $ = (id) => document.getElementById(id);
const workspaceLaunchHash=window.location.hash;
let subjects = [], selected = null, lessons = [], loadingVersion = 0, noticeTimer, workspaceBooting=true;
let selectedAudio = null, previewController = null, previewVersion = 0, importing = false;
let autoFields = {};
let currentLesson = null, currentAudioJob = null, audioPollTimer = null, audioSourceVersion = 0, lessonOpenSequence=0;
function notify(message, error = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
  $('notice').hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { $('notice').hidden = true; }, error ? 10000 : 5000);
}
function signedOut() {
  if(typeof resetWorkspaceSession==='function')resetWorkspaceSession();
  resetAudioState();
  $('player').pause(); $('player').removeAttribute('src'); $('player').load();
  $('player-panel').hidden = true;
  $('workspace').hidden = true; $('login-view').hidden = false;
  for (const dialog of document.querySelectorAll('dialog[open]')) dialog.close();
  subjects = []; selected = null; lessons = []; loadingVersion++;
  clearSelection(); $('upload-form').reset();
}
async function request(path, options = {}) {
  let response;
  const {allowMissing = false, ...fetchOptions} = options;
  try { response = await fetch(path, {credentials: 'same-origin', ...fetchOptions}); }
  catch (error) { if (error.name === 'AbortError') throw error; throw new Error(T('Connessione interrotta. Verifica che Traccia sia in esecuzione.')); }
  if (response.status === 401) { signedOut(); throw new Error(T('Accesso richiesto. Inserisci il token locale.')); }
  if (response.status === 404 && allowMissing) return null;
  if (!response.ok) {
    let detail; try { detail = (await response.json()).detail; } catch { /* generic below */ }
    if (response.status === 409) {const error=new Error(typeof detail === 'string' ? detail : T('Questa registrazione è già presente nella materia.'));error.status=409;error.detail=detail;throw error;}
    if (response.status === 413) throw new Error(T('Il file supera il limite di 512 MiB.'));
    if (response.status === 422) throw new Error(typeof detail === 'string' ? detail : T('Controlla i campi e il formato audio.'));
    if (response.status === 507) throw new Error(T('Impossibile salvare: controlla spazio libero e permessi.'));
    throw new Error(typeof detail === 'string' ? detail : T('Operazione non riuscita. Riprova.'));
  }
  return response.status === 204 ? null : response.json();
}
async function allPages(path) {
  let items = [], page;
  do { page = await request(`${path}?limit=200&offset=${items.length}`); items.push(...page); } while (page.length === 200);
  return items;
}
function duration(seconds) {
  if(seconds>0 && seconds<60)return `${Math.max(1,Math.round(seconds))} s`;
  const mins = Math.round(seconds / 60);
  return mins >= 60 ? `${Math.floor(mins / 60)} h ${mins % 60} min` : `${mins} min`;
}
function renderSubjects() {
  $('subjects').replaceChildren();
  $('no-subjects').hidden = subjects.length > 0;
  for (const subject of subjects) {
    const button = document.createElement('button');
    button.className = `subject-button${subject.id === selected ? ' active' : ''}`;
    button.textContent = subject.title;
    button.setAttribute('aria-current', subject.id === selected ? 'page' : 'false');
    button.onclick = () => selectSubject(subject.id).catch(e => notify(e.message, true));
    $('subjects').append(button);
  }
}
function renderLessons() {
  $('lessons').replaceChildren();
  $('empty').hidden = lessons.length > 0;
  $('library-message').hidden=true;$('library-message').className='';
  $('lesson-count').textContent = lessons.length;
  $('total-duration').textContent = duration(lessons.reduce((sum, l) => sum + l.duration_seconds, 0));
  const query = $('lesson-search').value.trim().toLocaleLowerCase(I18n.locale);
  const visible = lessons.filter(lesson => [lesson.title,lesson.teacher,lesson.lecture_date || ''].join(' ').toLocaleLowerCase(I18n.locale).includes(query));
  if(lessons.length && !visible.length){$('library-message').hidden=false;$('library-message').textContent=T('Nessuna lezione corrisponde alla ricerca.');}
  for (const lesson of visible) {
    const card = document.createElement('article'); card.className = 'lesson-card' + (currentLesson && currentLesson.id === lesson.id ? ' active' : '');
    const play = document.createElement('button'); play.className = 'play-button'; play.textContent = '▶';
    play.setAttribute('aria-label', T`Ascolta ${lesson.title}`);
    play.onclick = () => openLesson(lesson,true);
    const details = document.createElement('div'); details.className = 'lesson-details';
    const title = document.createElement('h3'); const open=document.createElement('button'); open.className='lesson-title'; open.textContent=lesson.title; open.onclick=()=>openLesson(lesson,false); title.append(open);
    const meta = document.createElement('p');
    const date = lesson.lecture_date ? new Date(`${lesson.lecture_date}T12:00:00`).toLocaleDateString(I18n.locale) : T('Data non indicata');
    meta.textContent = [date, duration(lesson.duration_seconds), lesson.teacher, `${(lesson.size_bytes / 1048576).toFixed(1)} MiB`].filter(Boolean).join(' · ');
    details.append(title, meta);
    const badge = document.createElement('span'); badge.className = 'badge'; badge.textContent = T('Originale');
    card.append(play, details, badge); $('lessons').append(card);
  }
}
async function selectSubject(id) {
  if (typeof mayLeaveTranscript === 'function' && !mayLeaveTranscript()) return false;
  const version = ++loadingVersion;
  resetAudioState();
  if (typeof showStudyView === 'function') showStudyView('library');
  $('lesson-search').value = '';
  selected = id; renderSubjects();
  const subject = subjects.find(s => s.id === id);
  $('subject-title').textContent = subject.title;
  $('subject-description').textContent = subject.description || T('Le registrazioni e i materiali di questa materia.');
  $('open-upload').disabled = false;$('open-recording').disabled=false;
  $('player').pause(); $('player').removeAttribute('src'); $('player').load(); $('player-panel').hidden = true;
  lessons = []; renderLessons(); $('empty').hidden = true; $('list-status').textContent = T('Caricamento…');
  try {
    const result = await allPages(`/api/v1/subjects/${encodeURIComponent(id)}/lessons`);
    if (version !== loadingVersion) return;
    lessons = result; renderLessons();
    if(typeof resetQuestionsForCourse==='function')resetQuestionsForCourse();
    if(typeof loadCoursePreferences==='function')await loadCoursePreferences(id);
  } catch(error){if(version===loadingVersion){$('library-message').hidden=false;$('library-message').textContent=error.message;$('library-message').className='workspace-error';}throw error;} finally { if (version === loadingVersion) $('list-status').textContent = ''; }
  return true;
}
async function openWorkspace() {
  $('workspace').setAttribute('aria-busy','true');
  try{
  subjects = await allPages('/api/v1/subjects');
  $('login-view').hidden = true; $('workspace').hidden = false;
  renderSubjects();
  if (subjects.length) await selectSubject(subjects[0].id);
  else {
    selected = null; lessons = []; renderLessons(); $('open-upload').disabled = true;$('open-recording').disabled=true;
    $('subject-title').textContent = T('Il tuo spazio di studio');
    $('subject-description').textContent = T('Una materia alla volta, una lezione dopo l’altra.');
  }
  }finally{if(!workspaceBooting)$('workspace').setAttribute('aria-busy','false');}
}
$('login-form').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  const token = $('token').value.trim(); $('token').value = '';
  try { await request('/api/v1/session', {method:'POST', headers:{Authorization:`Bearer ${token}`}}); await openWorkspace(); }
  catch (e) { notify(e.message, true); } finally { button.disabled = false; }
};
$('logout').onclick = async () => {
  if (typeof mayLeaveTranscript === 'function' && !mayLeaveTranscript()) return;
  try { await request('/api/v1/session', {method:'DELETE'}); signedOut(); }
  catch (e) { notify(e.message, true); }
};
$('new-subject').onclick = () => $('subject-dialog').showModal();
$('open-upload').onclick = () => { if (selected) $('upload-dialog').showModal(); };
for (const button of document.querySelectorAll('.close-dialog')) button.onclick = () => button.closest('dialog').close();
$('subject-form').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  try {
    const subject = await request('/api/v1/subjects', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title:$('subject-name').value.trim(),description:$('description').value.trim()})});
    subjects.push(subject); $('subject-dialog').close(); $('subject-form').reset(); await selectSubject(subject.id); notify(T('Materia creata.'));
  } catch (e) { notify(e.message, true); } finally { button.disabled = false; }
};
const suggestionFields = {'title':'lesson-title','teacher':'teacher','lecture_date':'lecture-date'};
function clearSelection() {
  selectedAudio = null; autoFields = {}; previewVersion++;
  if (previewController) previewController.abort();
  $('selected-file').textContent = T('MP3, MP4, WAV, M4A o FLAC · massimo 512 MiB');
  $('suggestion-status').textContent = T('Titolo, data e docente saranno proposti dal nome e dai metadati, quando disponibili.');
}
async function chooseAudio(file) {
  if (importing || !file) return;
  if (!/\.(mp3|mp4|wav|m4a|flac)$/i.test(file.name) || file.size > 512 * 1024 * 1024) {
    clearSelection(); $('audio-file').value = '';
    notify(T('Scegli un MP3, MP4, WAV, M4A o FLAC fino a 512 MiB.'), true); return;
  }
  const version = ++previewVersion;
  if (previewController) previewController.abort();
  previewController = new AbortController(); selectedAudio = file;
  $('selected-file').textContent = `${file.name} · ${(file.size / 1048576).toFixed(1)} MiB`;
  for (const [key, id] of Object.entries(suggestionFields)) {
    if ($(id).value === autoFields[key]) $(id).value = '';
  }
  autoFields = {};
  if (!$('lesson-title').value) {
    const title = file.name.replace(/\.[^.]+$/, '').slice(0,200);
    $('lesson-title').value = title; autoFields.title = title;
  }
  const baseline = Object.fromEntries(Object.entries(suggestionFields).map(([key,id]) => [key,$(id).value]));
  $('suggestion-status').textContent = T('Lettura del nome e dei metadati audio… Puoi già modificare i campi.');
  const data = new FormData(); data.append('file',file,file.name);
  try {
    const result = await request('/api/v1/audio/preview',{method:'POST',body:data,signal:previewController.signal});
    if (version !== previewVersion) return;
    for (const [key,id] of Object.entries(suggestionFields)) {
      const candidate = result[key];
      const eligible = !baseline[key] || (key === 'title' && baseline[key] === autoFields.title);
      if (candidate && eligible && $(id).value === baseline[key]) {
        $(id).value = candidate; autoFields[key] = candidate;
      }
    }
    const sources = {filename:T('nome del file'),embedded_title:T('titolo nei tag'),embedded_artist:T('artista nei tag'),embedded_date:T('data nei tag')};
    const labels = {title:T('Titolo'),teacher:T('Docente'),lecture_date:T('Data')};
    const hints = Object.entries(result.sources).map(([key,source]) => `${labels[key]}: ${sources[source]}.`);
    $('suggestion-status').textContent = [T('Proposte da verificare prima di importare.'),...hints,...result.notes].join('\n');
  } catch (error) {
    if (version !== previewVersion || error.name === 'AbortError') return;
    $('suggestion-status').textContent = T('Metadati non disponibili. Puoi compilare i campi manualmente; l’audio sarà verificato durante l’importazione.');
  }
}
$('audio-file').onchange = () => chooseAudio($('audio-file').files[0]);
for (const name of ['dragenter','dragover']) $('drop-zone').addEventListener(name,event => {
  event.preventDefault(); if (!importing) $('drop-zone').classList.add('dragover');
});
$('drop-zone').addEventListener('dragleave',event => {
  if (!$('drop-zone').contains(event.relatedTarget)) $('drop-zone').classList.remove('dragover');
});
$('drop-zone').addEventListener('drop',event => {
  event.preventDefault(); event.stopPropagation(); $('drop-zone').classList.remove('dragover');
  const files = event.dataTransfer.files;
  if (files.length !== 1) { notify(T('Trascina una registrazione alla volta.'),true); return; }
  $('audio-file').value = '';
  chooseAudio(files[0]);
});
// Avoid navigating away from the app when a file is dropped outside the target.
window.addEventListener('dragover',event => { if ([...event.dataTransfer.types].includes('Files')) event.preventDefault(); });
window.addEventListener('drop',event => { if ([...event.dataTransfer.types].includes('Files')) event.preventDefault(); });
$('upload-form').onsubmit = async event => {
  event.preventDefault(); if (!selected) return;
  const file = selectedAudio;
  if (!file || file.size > 512 * 1024 * 1024) { notify(T('Scegli un file audio fino a 512 MiB.'), true); return; }
  const sid = selected, button = event.submitter; button.disabled = true;
  importing = true; $('audio-file').disabled = true;
  const form = new FormData($('upload-form'));
  form.set('file',file,file.name);
  if (!form.get('lecture_date')) form.delete('lecture_date');
  $('upload-status').textContent = T('Caricamento e verifica audio in corso. Per registrazioni lunghe può richiedere alcuni minuti.');
  try {
    await request(`/api/v1/subjects/${encodeURIComponent(sid)}/lessons`, {method:'POST',body:form});
    $('upload-dialog').close(); $('upload-form').reset(); clearSelection();
    if (selected === sid) await selectSubject(sid);
    notify(T('Lezione importata. L’audio originale è pronto per l’ascolto.'));
  } catch (e) { notify(e.message, true); }
  finally { importing = false; $('audio-file').disabled = false; button.disabled = false; $('upload-status').textContent = T('L’originale sarà conservato senza modifiche.'); }
};
function resetAudioState() {
  lessonOpenSequence++;
  if(typeof clearLessonWorkspace==='function')clearLessonWorkspace();
  if(typeof resetPreview==='function')resetPreview();
  if (typeof resetStudy === 'function') resetStudy();
  currentLesson = null; currentAudioJob = null; audioSourceVersion++;
  $('audio-method').value='gtcrn'; $('audio-preset').value='balanced'; $('audio-gain').value='0';
  $('voice-reference').hidden=true; $('audio-preset').closest('label').hidden=false;
  clearTimeout(audioPollTimer);
}
function renderAudioJob() {
  const job = currentAudioJob;
  const active = job && ['queued','running'].includes(job.status);
  const completed = job && job.status === 'completed';
  $('source-enhanced').disabled = !completed;
  $('transcription-source').options[1].disabled=!completed;
  if(!completed)$('transcription-source').value='original';
  $('enhance-audio').disabled = Boolean(active || completed);
  $('enhance-audio').textContent = completed ? T('Versione pronta') : T('Migliora audio');
  $('cancel-enhancement').hidden = !active;
  $('audio-progress').hidden = !active;
  $('audio-progress').value = job ? job.progress : 0;
  const statuses = {
    queued:T('In coda. L’elaborazione inizierà appena il motore è libero.'),
    running:T`Elaborazione in corso · ${Math.floor(job ? job.progress : 0)}%`,
    completed:T('Versione pronta. Premi Migliorato per confrontarla dallo stesso punto.'),
    cancelled:T('Elaborazione annullata. Puoi avviarla di nuovo.'),
    interrupted:T('Elaborazione interrotta: ripartirà all’avvio del servizio.'),
    failed:T('Elaborazione non riuscita. Verifica che l’originale sia presente e che ci sia spazio libero, poi riprova.')
  };
  $('enhancement-status').textContent = job ? statuses[job.status] || job.status : T('Scegli un’intensità e crea una versione da confrontare.');
}
async function refreshAudioJob() {
  clearTimeout(audioPollTimer);
  if (!currentLesson) return;
  const id = currentLesson.id, preset = $('audio-preset').value, method=$('audio-method').value,options=enhancementOptions();
  const jobs = await request(`/api/v1/lessons/${encodeURIComponent(id)}/enhancements`);
  if (!currentLesson || currentLesson.id !== id || $('audio-preset').value !== preset || $('audio-method').value !== method || JSON.stringify(enhancementOptions()) !== JSON.stringify(options)) return;
  currentAudioJob = jobs.find(job => !job.preview && job.preset === preset && (job.method || 'traditional') === method && (job.gain_db || 0)===options.gain_db && (method!=='voxlock' || (()=>{try{const recipe=JSON.parse(job.filter);return recipe.reference_start===options.reference_start && recipe.reference_end===options.reference_end;}catch{return false;}})())) || null;
  renderAudioJob();
  if (currentAudioJob && ['queued','running','interrupted'].includes(currentAudioJob.status)) {
    audioPollTimer = setTimeout(() => refreshAudioJob().catch(e => notify(e.message,true)),1200);
  }
}
async function switchAudio(improved, keepPosition = true, autoplay = null) {
  if (!currentLesson || (improved && (!currentAudioJob || currentAudioJob.status !== 'completed'))) return;
  const player = $('player'), position = keepPosition ? player.currentTime || 0 : 0;
  const playing = autoplay === null ? !player.paused : autoplay;
  const rate = Number($('speed').value), sourceVersion = ++audioSourceVersion;
  player.pause();
  $('audio-source-label').textContent = improved ? T('AUDIO MIGLIORATO') : T('AUDIO ORIGINALE');
  $('source-original').setAttribute('aria-pressed',String(!improved));
  $('source-enhanced').setAttribute('aria-pressed',String(improved));
  player.onloadedmetadata = async () => {
    if (sourceVersion !== audioSourceVersion) return;
    player.currentTime = Math.min(position,Math.max(0,(player.duration || position) - .05));
    player.playbackRate = rate;
    if (playing) try { await player.play(); } catch { notify(T('Premi Play nel lettore per avviare l’ascolto.'),true); }
  };
  player.src = improved ? `/api/v1/audio-jobs/${encodeURIComponent(currentAudioJob.id)}/audio` : `/api/v1/lessons/${encodeURIComponent(currentLesson.id)}/audio`;
  player.load();
}
async function openLesson(lesson, autoplay = false) {
  if (typeof mayLeaveTranscript === 'function' && !mayLeaveTranscript()) return false;
  const opener=document.activeElement;
  resetAudioState();const sequence=lessonOpenSequence; currentLesson = lesson; $('preview-end').value=Math.min(20,lesson.duration_seconds); renderLessons();
  $('playing-title').textContent = lesson.title; $('player-panel').hidden = false;$('player-panel').setAttribute('aria-busy','true');
  renderAudioJob(); switchAudio(false,false,autoplay);
  if(typeof resetLessonWorkspace==='function')resetLessonWorkspace(lesson);
  try { await refreshAudioJob(); if(sequence!==lessonOpenSequence)return false;await loadStudy();if(sequence!==lessonOpenSequence)return false;await loadSpeakers(); } catch(e) { if(sequence===lessonOpenSequence)notify(e.message,true); }
  finally{if(sequence===lessonOpenSequence)$('player-panel').setAttribute('aria-busy','false');}
  if(sequence!==lessonOpenSequence)return false;
  if(document.activeElement===document.body || document.activeElement===opener){$('playing-title').tabIndex=-1;$('playing-title').focus({preventScroll:true});$('player-panel').scrollIntoView({block:'start'});}
  return true;
}
$('source-original').onclick = () => switchAudio(false);
$('source-enhanced').onclick = () => switchAudio(true);
$('audio-preset').onchange = async () => {
  switchAudio(false); currentAudioJob = null; renderAudioJob();
  try { await refreshAudioJob(); } catch(e) { notify(e.message,true); }
};
$('enhance-audio').onclick = async () => {
  if (!currentLesson) return;
  const id = currentLesson.id;
  $('enhance-audio').disabled = true;
  try {
    const job = await request(`/api/v1/lessons/${encodeURIComponent(id)}/enhancements`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(enhancementOptions())});
    if (currentLesson && currentLesson.id === id) { await refreshAudioJob(); }
    notify(job.status === 'completed' ? T('La versione migliorata è già pronta.') : T('Elaborazione avviata. Puoi continuare a usare l’archivio.'));
  } catch(e) { notify(e.message,true); renderAudioJob(); }
};
$('cancel-enhancement').onclick = async () => {
  if (!currentAudioJob) return;
  const id = currentAudioJob.id;
  try { await request(`/api/v1/audio-jobs/${encodeURIComponent(id)}/cancel`,{method:'POST'}); await refreshAudioJob(); }
  catch(e) { notify(e.message,true); }
};
$('speed').onchange = () => { $('player').playbackRate = Number($('speed').value); };
$('player').onerror = () => { if ($('player').getAttribute('src')) notify(T('Audio non disponibile o formato non riproducibile dal browser. Prova a riaprire la sessione.'), true); };
async function bootstrapWorkspace() {
  $('workspace').setAttribute('aria-busy','true');
  if(document.readyState==='loading' || document.readyState==='interactive')await new Promise(resolve=>document.addEventListener('DOMContentLoaded',resolve,{once:true}));
  const access = new URLSearchParams(window.location.hash.slice(1)).get('access');
  if (access) {
    window.history.replaceState(null, '', window.location.pathname);
    await request('/api/v1/desktop-session', {method:'POST',headers:{'X-Desktop-Access':access}});
  }
  await openWorkspace();
  const environment=await request('/api/v1/environment');
  window.tracciaDesktop=environment.desktop;
  $('quit-desktop').hidden=!environment.desktop;
  if(typeof restoreWorkspaceRoute==='function')await restoreWorkspaceRoute();
}
$('quit-desktop').onclick=async()=>{
  if (typeof mayLeaveTranscript === 'function' && !mayLeaveTranscript()) return;
  try {await request('/api/v1/shutdown',{method:'POST'});signedOut();notify(T('Traccia è stata chiusa. Puoi chiudere questa scheda.'));}
  catch(e){notify(e.message,true);}
};
bootstrapWorkspace().catch(e => { if (!$('login-view').hidden) return; notify(e.message, true); }).finally(()=>{workspaceBooting=false;$('workspace').setAttribute('aria-busy','false');});

$('lesson-search').oninput = renderLessons;

function enhancementOptions(){const result={preset:$('audio-preset').value,method:$('audio-method').value,gain_db:Number($('audio-gain').value)};if(result.method==='voxlock'){result.reference_start=Number($('reference-start').value);result.reference_end=Number($('reference-end').value);}return result;}
async function enhancementChanged(){const isolation=$('audio-method').value==='voxlock';$('voice-reference').hidden=!isolation;$('audio-preset').closest('label').hidden=isolation;if(isolation){$('audio-preset').value='balanced';if(currentLesson && Number($('reference-end').value)>currentLesson.duration_seconds)$('reference-end').value=currentLesson.duration_seconds;}switchAudio(false);currentAudioJob=null;renderAudioJob();try{await refreshAudioJob();}catch(e){notify(e.message,true);}}
async function setIsolationReference(start,end){$('audio-method').value='voxlock';$('reference-start').value=Number(start.toFixed(1));$('reference-end').value=Number(Math.min(currentLesson.duration_seconds,end).toFixed(1));await enhancementChanged();$('voice-reference').scrollIntoView({block:'center',behavior:'smooth'});}
for(const id of ['audio-method','audio-preset','audio-gain','reference-start','reference-end'])$(id).onchange=enhancementChanged;
$('reference-from-player').onclick=()=>{if(currentLesson){const start=Math.min($('player').currentTime,Math.max(0,currentLesson.duration_seconds-3));setIsolationReference(start,Math.min(start+10,currentLesson.duration_seconds));}};
