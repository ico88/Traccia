'use strict';
const $ = (id) => document.getElementById(id);
let subjects = [], selected = null, lessons = [], loadingVersion = 0, noticeTimer;
function notify(message, error = false) {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
  $('notice').hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { $('notice').hidden = true; }, error ? 10000 : 5000);
}
function signedOut() {
  $('player').pause(); $('player').removeAttribute('src'); $('player').load();
  $('player-panel').hidden = true;
  $('workspace').hidden = true; $('login-view').hidden = false;
  for (const dialog of document.querySelectorAll('dialog[open]')) dialog.close();
  subjects = []; selected = null; lessons = []; loadingVersion++;
}
async function request(path, options = {}) {
  let response;
  try { response = await fetch(path, {credentials: 'same-origin', ...options}); }
  catch { throw new Error('Connessione interrotta. Verifica che AulaLocale sia in esecuzione.'); }
  if (response.status === 401) { signedOut(); throw new Error('Accesso richiesto. Inserisci il token locale.'); }
  if (!response.ok) {
    let detail; try { detail = (await response.json()).detail; } catch { /* generic below */ }
    if (response.status === 409) throw new Error('Questa registrazione è già presente nella materia.');
    if (response.status === 413) throw new Error('Il file supera il limite di 512 MiB.');
    if (response.status === 422) throw new Error('Controlla i campi e il formato audio. Il file deve essere decodificabile e corrispondere all’estensione.');
    if (response.status === 507) throw new Error('Impossibile salvare: controlla spazio libero e permessi.');
    throw new Error(typeof detail === 'string' ? detail : 'Operazione non riuscita. Riprova.');
  }
  return response.status === 204 ? null : response.json();
}
async function allPages(path) {
  let items = [], page;
  do { page = await request(`${path}?limit=200&offset=${items.length}`); items.push(...page); } while (page.length === 200);
  return items;
}
function duration(seconds) {
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
  $('lesson-count').textContent = lessons.length;
  $('total-duration').textContent = duration(lessons.reduce((sum, l) => sum + l.duration_seconds, 0));
  for (const lesson of lessons) {
    const card = document.createElement('article'); card.className = 'lesson-card';
    const play = document.createElement('button'); play.className = 'play-button'; play.textContent = '▶';
    play.setAttribute('aria-label', `Ascolta ${lesson.title}`);
    play.onclick = async () => {
      $('playing-title').textContent = lesson.title;
      $('player-panel').hidden = false;
      $('player').src = `/api/v1/lessons/${encodeURIComponent(lesson.id)}/audio`;
      $('player').playbackRate = Number($('speed').value);
      try { await $('player').play(); } catch { notify('Riproduzione non avviata. Premi Play nel lettore o verifica il formato supportato dal browser.', true); }
    };
    const details = document.createElement('div'); details.className = 'lesson-details';
    const title = document.createElement('h3'); title.textContent = lesson.title;
    const meta = document.createElement('p');
    const date = lesson.lecture_date ? new Date(`${lesson.lecture_date}T12:00:00`).toLocaleDateString('it-IT') : 'Data non indicata';
    meta.textContent = [date, duration(lesson.duration_seconds), lesson.teacher, `${(lesson.size_bytes / 1048576).toFixed(1)} MiB`].filter(Boolean).join(' · ');
    details.append(title, meta);
    const badge = document.createElement('span'); badge.className = 'badge'; badge.textContent = 'Originale';
    card.append(play, details, badge); $('lessons').append(card);
  }
}
async function selectSubject(id) {
  const version = ++loadingVersion;
  selected = id; renderSubjects();
  const subject = subjects.find(s => s.id === id);
  $('subject-title').textContent = subject.title;
  $('subject-description').textContent = subject.description || 'Le registrazioni e i materiali di questa materia.';
  $('open-upload').disabled = false;
  $('player').pause(); $('player').removeAttribute('src'); $('player').load(); $('player-panel').hidden = true;
  lessons = []; renderLessons(); $('empty').hidden = true; $('list-status').textContent = 'Caricamento…';
  try {
    const result = await allPages(`/api/v1/subjects/${encodeURIComponent(id)}/lessons`);
    if (version !== loadingVersion) return;
    lessons = result; renderLessons();
  } finally { if (version === loadingVersion) $('list-status').textContent = ''; }
}
async function openWorkspace() {
  subjects = await allPages('/api/v1/subjects');
  $('login-view').hidden = true; $('workspace').hidden = false;
  renderSubjects();
  if (subjects.length) await selectSubject(subjects[0].id);
  else {
    selected = null; lessons = []; renderLessons(); $('open-upload').disabled = true;
    $('subject-title').textContent = 'Il tuo spazio di studio';
    $('subject-description').textContent = 'Una materia alla volta, una lezione dopo l’altra.';
  }
}
$('login-form').onsubmit = async event => {
  event.preventDefault(); const button = event.submitter; button.disabled = true;
  const token = $('token').value.trim(); $('token').value = '';
  try { await request('/api/v1/session', {method:'POST', headers:{Authorization:`Bearer ${token}`}}); await openWorkspace(); }
  catch (e) { notify(e.message, true); } finally { button.disabled = false; }
};
$('logout').onclick = async () => {
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
    subjects.push(subject); $('subject-dialog').close(); $('subject-form').reset(); await selectSubject(subject.id); notify('Materia creata.');
  } catch (e) { notify(e.message, true); } finally { button.disabled = false; }
};
$('audio-file').onchange = () => { const file = $('audio-file').files[0]; if (file && !$('lesson-title').value) $('lesson-title').value = file.name.replace(/\.[^.]+$/, '').slice(0, 200); };
$('upload-form').onsubmit = async event => {
  event.preventDefault(); if (!selected) return;
  const file = $('audio-file').files[0];
  if (!file || file.size > 512 * 1024 * 1024) { notify('Scegli un file audio fino a 512 MiB.', true); return; }
  const sid = selected, button = event.submitter; button.disabled = true;
  const form = new FormData($('upload-form'));
  if (!form.get('lecture_date')) form.delete('lecture_date');
  $('upload-status').textContent = 'Caricamento e verifica audio in corso. Per registrazioni lunghe può richiedere alcuni minuti.';
  try {
    await request(`/api/v1/subjects/${encodeURIComponent(sid)}/lessons`, {method:'POST',body:form});
    $('upload-dialog').close(); $('upload-form').reset();
    if (selected === sid) await selectSubject(sid);
    notify('Lezione importata. L’audio originale è pronto per l’ascolto.');
  } catch (e) { notify(e.message, true); }
  finally { button.disabled = false; $('upload-status').textContent = 'L’originale sarà conservato senza modifiche.'; }
};
$('speed').onchange = () => { $('player').playbackRate = Number($('speed').value); };
$('player').onerror = () => { if ($('player').getAttribute('src')) notify('Audio non disponibile o formato non riproducibile dal browser. Prova a riaprire la sessione.', true); };
openWorkspace().catch(e => { if (!$('login-view').hidden) return; notify(e.message, true); });
