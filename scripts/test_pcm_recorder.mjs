// Optional development check; Node is not required to run AulaLocale.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const code=fs.readFileSync(new URL('../aulalocale/web/pcm-recorder.js',import.meta.url),'utf8');
for(const rate of [16000,44100,48000]){
  let Processor;const blocks=[];let flushed=false;
  const context=vm.createContext({sampleRate:rate,AudioWorkletProcessor:class{constructor(){this.port={postMessage(value){if(value.flushed)flushed=true;else if(typeof value.level!=='number')blocks.push(new Int16Array(value));}};}},registerProcessor(name,value){Processor=value;}});
  vm.runInContext(code,context);const recorder=new Processor();const count=Math.round(rate*5.3);
  for(let start=0;start<count;start+=128){const samples=new Float32Array(Math.min(128,count-start));for(let i=0;i<samples.length;i++)samples[i]=.25*Math.sin(2*Math.PI*1000*(start+i)/rate);recorder.process([[samples]]);}
  recorder.port.onmessage({data:'flush'});assert(flushed);const output=blocks.flatMap(b=>[...b]);assert(Math.abs(output.length-count/rate*16000)<=1);assert(output.every(n=>Math.abs(n)<=8193));assert(blocks.slice(0,-1).every(b=>b.length===32000));
  let crossings=0;for(let i=1;i<output.length;i++)if(output[i-1]<0 && output[i]>=0)crossings++;assert(Math.abs(crossings-5300)<=2);console.log(rate,'Hz:',output.length,'PCM frames, two-second blocks, 1 kHz tone preserved');
}
