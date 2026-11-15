import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const folder=new URL('../aulalocale/web/',import.meta.url);
const catalog=fs.readFileSync(new URL('locales/en.js',folder),'utf8');
const source=fs.readFileSync(new URL('i18n.js',folder),'utf8');
function session(saved,browser='en-US',storageAvailable=true){
  const nodes=new Map();const user={textContent:'Lezioni',value:'Titolo'};
  for(const id of ['interface-language','notes-language'])nodes.set(id,{value:''});
  const label={dataset:{i18n:'Lezioni'},textContent:'Lezioni'};
  const context=vm.createContext({URLSearchParams,navigator:{language:browser},window:{location:{hash:'',reload(){context.reloaded=true;}}},document:{documentElement:{},querySelector:()=>null,getElementById:id=>nodes.get(id),querySelectorAll:selector=>selector==='[data-i18n]'?[label]:[]},localStorage:{getItem(){if(!storageAvailable)throw Error('disabled');return saved;},setItem(key,value){context.saved=[key,value];}},alert:message=>context.alert=message});
  vm.runInContext(catalog,context);vm.runInContext(source,context);
  return {context,nodes,label,user,run:code=>vm.runInContext(code,context)};
}
let s=session('en');assert.equal(s.label.textContent,'Lectures');assert.equal(s.context.document.documentElement.lang,'en');assert.equal(s.user.textContent,'Lezioni');assert.equal(s.user.value,'Titolo');
assert.equal(s.run("T`Ascolta ${'Titolo {{0}} <script>'}`"),'Listen to Titolo {{0}} <script>');
assert.equal(s.run("T('unknown diagnostic')"),'unknown diagnostic');
s.nodes.get('interface-language').value='it';s.nodes.get('interface-language').onchange();assert.equal(s.context.saved[1],'it');assert.equal(s.context.reloaded,true);
s=session('it');assert.equal(s.label.textContent,'Lezioni');assert.equal(s.nodes.get('notes-language').value,'it');
s=session('fr','it-IT');assert.equal(s.context.document.documentElement.lang,'it');
s=session(null,'fr-FR',false);assert.equal(s.context.document.documentElement.lang,'en');
s=session('en');s.context.isRecording=()=>true;s.nodes.get('interface-language').value='it';s.nodes.get('interface-language').onchange();assert.equal(s.context.reloaded,undefined);assert.equal(s.nodes.get('interface-language').value,'en');
s=session('en');s.context.mayLeaveTranscript=()=>false;s.nodes.get('interface-language').value='it';s.nodes.get('interface-language').onchange();assert.equal(s.context.reloaded,undefined);
for(const file of ['app.js','study.js','speakers.js','recording.js','pcm-recorder.js','preview.js'])new vm.Script(fs.readFileSync(new URL(file,folder),'utf8'),{filename:file});
console.log('i18n: English/Italian, fallback, persistence, safe interpolation, user content and recording/unsaved-change guards passed');
