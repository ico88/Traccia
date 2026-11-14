// Mono PCM16 at 16 kHz, transferred in two-second blocks; no audio monitoring.
class AulaRecorder extends AudioWorkletProcessor {
  constructor(){super();this.buffer=[];this.position=0;this.step=sampleRate/16000;this.pcm=[];this.active=true;this.meterFrames=0;this.port.onmessage=event=>{if(event.data==='flush'){this.active=false;while(this.position<this.buffer.length){const i=Math.floor(this.position),fraction=this.position-i,value=this.buffer[i]*(1-fraction)+(this.buffer[i+1] ?? this.buffer[i])*fraction;this.pcm.push(Math.round(Math.max(-1,Math.min(32767/32768,value))*32768));this.position+=this.step;}this.buffer=[];this.emit();this.port.postMessage({flushed:true});}};}
  emit(){if(!this.pcm.length)return;const block=new Int16Array(this.pcm);this.pcm=[];this.port.postMessage(block.buffer,[block.buffer]);}
  process(inputs){
    if(!this.active)return true;
    const channel=inputs[0]?.[0];if(!channel)return true;
    this.meterFrames+=channel.length;if(this.meterFrames>=sampleRate/10){this.meterFrames=0;let sum=0;for(const value of channel)sum+=value*value;this.port.postMessage({level:Math.sqrt(sum/channel.length)});}
    for(const value of channel)this.buffer.push(value);
    while(this.position<this.buffer.length-1){const i=Math.floor(this.position),fraction=this.position-i,value=this.buffer[i]*(1-fraction)+this.buffer[i+1]*fraction;this.pcm.push(Math.round(Math.max(-1,Math.min(32767/32768,value))*32768));this.position+=this.step;if(this.pcm.length===32000)this.emit();}
    const used=Math.min(Math.floor(this.position),this.buffer.length-1);this.buffer=this.buffer.slice(used);this.position-=used;return true;
  }
}
registerProcessor('aula-recorder',AulaRecorder);
