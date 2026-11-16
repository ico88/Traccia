import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync(new URL('../aulalocale/web/study.js',import.meta.url),'utf8');
const load=code.slice(code.indexOf('async function loadNotes(){'),code.indexOf("$('generate-notes').onclick="));
function element(){return {children:[],replaceChildren(){this.children=[];},append(...children){this.children.push(...children);},prepend(...children){this.children.unshift(...children);},setAttribute(){},querySelectorAll(){return [];}};}
const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
let result={current:null,proposals:[],jobs:[{id:'pipeline',kind:'pipeline',status:'running',progress:40}]};const callbacks=[];
const context=vm.createContext({$:node,selected:'subject',activeView:'notes',historicalNotes:null,currentNotes:null,notesTimer:null,I18n:{locale:'en'},request:async()=>result,allPages:async()=>[],loadMaterials:async()=>{},document:{createElement:element},clearTimeout(){},setTimeout(callback){callbacks.push(callback);return callbacks.length;},notify(){},T:(text,...values)=>typeof text==='string'?text:text.reduce((s,t,i)=>s+t+(i<values.length?values[i]:''),'')});
vm.runInContext(load,context);await context.loadNotes();assert.equal(node('generate-notes').disabled,true);assert.equal(callbacks.length,1);
result={current:null,proposals:[{id:'proposal',parent_id:null,chapters:[],changes:{chapters:[],removed:[]}}],jobs:[{id:'pipeline',kind:'pipeline',status:'completed',progress:100}]};
await callbacks[0]();assert.equal(node('generate-notes').disabled,false);assert.equal(node('notes-proposals').children.length,1);assert.equal(callbacks.length,1);
result={current:null,proposals:[],jobs:[{id:'pipeline',kind:'pipeline',status:'failed',error:'Pipeline stopped'}]};await context.loadNotes();assert.equal(node('notes-status').textContent,'Pipeline stopped');
console.log('Course-note polling: pipeline progress, proposal refresh and failure feedback passed');
