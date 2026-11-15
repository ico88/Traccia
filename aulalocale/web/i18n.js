'use strict';
// Only explicitly marked interface messages are translated. User content is never scanned.
const I18n = (() => {
  let saved;
  try { saved=localStorage.getItem('traccia.interfaceLanguage'); } catch {}
  const desktopLanguage=new URLSearchParams(window.location.hash.slice(1)).get('language');
  if(['en','it'].includes(desktopLanguage))saved=desktopLanguage;
  const language=['en','it'].includes(saved)?saved:(navigator.language?.toLowerCase().startsWith('it')?'it':'en');
  const locale=language==='it'?'it-IT':'en-GB';
  const translate=key=>language==='it'?key:(window.TracciaLocales?.[language]?.[key] ?? key);
  function message(strings,...values) {
    if(typeof strings==='string')return translate(strings);
    const key=strings.reduce((text,part,index)=>text+part+(index<values.length?'{{'+index+'}}':''),'');
    // Substitute once: user content containing {{n}} is not treated as another placeholder.
    return translate(key).replace(/\{\{(\d+)\}\}/g,(_,index)=>String(values[Number(index)]));
  }
  function apply(root=document) {
    document.documentElement.lang=language;
    for(const node of root.querySelectorAll('[data-i18n]'))node.textContent=translate(node.dataset.i18n);
    for(const attr of ['aria-label','placeholder','title'])for(const node of root.querySelectorAll('[data-i18n-'+attr+']'))node.setAttribute(attr,translate(node.getAttribute('data-i18n-'+attr)));
  }
  return {language,locale,message,apply};
})();
const T=I18n.message;
I18n.apply();
const languageSelect=document.getElementById('interface-language');
languageSelect.value=I18n.language;
languageSelect.onchange=async()=>{
  if(typeof isRecording==='function' && isRecording()){languageSelect.value=I18n.language;alert(T('Ferma e salva la registrazione prima di chiudere.'));return;}
  if(typeof importing==='boolean' && importing){languageSelect.value=I18n.language;alert(T('Caricamento e verifica audio in corso. Per registrazioni lunghe può richiedere alcuni minuti.'));return;}
  if(document.querySelector('dialog[open]') && !window.confirm(T('Ci sono correzioni non salvate. Vuoi abbandonarle?'))){languageSelect.value=I18n.language;return;}
  if(typeof mayLeaveTranscript==='function' && !mayLeaveTranscript()){languageSelect.value=I18n.language;return;}
  try {localStorage.setItem('traccia.interfaceLanguage',languageSelect.value);}catch{languageSelect.value=I18n.language;alert('Language preference could not be saved.');return;}
  if(window.tracciaDesktop){try{await request('/api/v1/desktop-language',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({language:languageSelect.value})});}catch{languageSelect.value=I18n.language;alert('Language preference could not be saved.');return;}}
  window.location.reload();
};

document.getElementById('notes-language').value=I18n.language;
