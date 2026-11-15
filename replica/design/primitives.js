'use strict';
const byId=id=>document.getElementById(id);
let toastTimer;
function notify(text){const toast=byId('toast');toast.textContent=text;toast.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.hidden=true,7000);}
document.querySelectorAll('[data-open]').forEach(button=>button.addEventListener('click',()=>byId(button.dataset.open).showModal()));
document.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
document.querySelectorAll('[data-feedback]').forEach(button=>button.addEventListener('click',()=>notify(button.dataset.feedback)));
const tabs=[...document.querySelectorAll('[role=tab]')];
function selectTab(tab){tabs.forEach(item=>{const selected=item===tab;item.setAttribute('aria-selected',String(selected));item.tabIndex=selected?0:-1;byId(item.getAttribute('aria-controls')).hidden=!selected;});}
tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>selectTab(tab));tab.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;if(next!==undefined){event.preventDefault();selectTab(tabs[next]);tabs[next].focus();}});});
const rows=[...document.querySelectorAll('.lecture-row')];
rows.forEach(row=>row.addEventListener('click',()=>{rows.forEach(other=>{const selected=other===row;other.classList.toggle('selected',selected);other.setAttribute('aria-pressed',String(selected));});byId('lecture-heading').textContent=row.dataset.lecture;notify('Sample lecture selected. The specimen passages remain synthetic.');}));
byId('lecture-search').addEventListener('input',event=>{const term=event.target.value.trim().toLocaleLowerCase();rows.forEach(row=>row.hidden=!row.dataset.lecture.toLocaleLowerCase().includes(term));byId('search-empty').hidden=rows.some(row=>!row.hidden);});
document.querySelectorAll('.segmented button').forEach(button=>button.addEventListener('click',()=>{button.parentElement.querySelectorAll('button').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));notify('Visual comparison state changed. No audio is loaded in this workshop.');}));
byId('position').addEventListener('input',event=>{const seconds=Number(event.target.value);byId('position-label').value=Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');});
byId('preferences-demo').addEventListener('submit',event=>{event.preventDefault();byId('preferences-status').textContent='Sample settings updated for this page only. Nothing was saved to your archive.';});
byId('question-demo').addEventListener('submit',event=>{event.preventDefault();byId('answer-demo').hidden=false;notify('Sample evidence state shown. No AI request was made.');});
byId('note-demo').addEventListener('submit',event=>{event.preventDefault();byId('note-dialog').close();notify('Sample note reviewed. Nothing was saved to an archive.');});
byId('discard-demo').addEventListener('click',()=>{byId('confirm-dialog').close();notify('Sample confirmation completed. No data was removed.');});
document.querySelector('.favorite').addEventListener('click',event=>{const button=event.currentTarget,selected=button.getAttribute('aria-pressed')!=='true';button.setAttribute('aria-pressed',String(selected));button.textContent=selected?'★ Saved':'☆ Save';});
byId('history-demo').addEventListener('change',event=>{const old=event.target.value==='old';byId('edit-history').disabled=old;byId('history-status').textContent=old?'Historical version · read only. Current accepted notes remain unchanged.':'Current accepted version. Editing would create a new revision.';});
byId('loading-demo').addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;button.setAttribute('aria-busy','true');button.textContent='Preparing sample…';await new Promise(resolve=>setTimeout(resolve,1000));button.disabled=false;button.removeAttribute('aria-busy');button.textContent='Try loading state';notify('Sample loading finished.');});
function showFiles(files){const output=byId('import-results');output.replaceChildren();const list=[...files].slice(0,20);if(files.length>20)notify('This workshop displays up to 20 selected files.');list.forEach(file=>{const allowed=/\.(mp3|mp4|wav|m4a|flac|ogg)$/i.test(file.name),oversize=file.size>512*1024*1024,row=document.createElement('div'),name=document.createElement('strong'),status=document.createElement('span');row.className='queue-row';name.textContent=file.name;status.className='badge '+(allowed&&!oversize?'neutral':'danger');status.textContent=!allowed?'Unsupported type':oversize?'Over 512 MiB':'Selected · not uploaded';row.append(name,status);output.append(row);});}
byId('sample-files').addEventListener('change',event=>showFiles(event.target.files));
let dragDepth=0;
byId('dropzone').addEventListener('dragenter',event=>{event.preventDefault();dragDepth++;event.currentTarget.classList.add('dragging');});
byId('dropzone').addEventListener('dragover',event=>{event.preventDefault();event.dataTransfer.dropEffect='copy';});
byId('dropzone').addEventListener('dragleave',event=>{dragDepth=Math.max(0,dragDepth-1);if(!dragDepth)event.currentTarget.classList.remove('dragging');});
byId('dropzone').addEventListener('drop',event=>{event.preventDefault();dragDepth=0;event.currentTarget.classList.remove('dragging');showFiles(event.dataTransfer.files);});
byId('import-dialog').addEventListener('close',()=>{dragDepth=0;byId('dropzone').classList.remove('dragging');});
document.addEventListener('dragover',event=>event.preventDefault());document.addEventListener('drop',event=>event.preventDefault());
document.querySelectorAll('.sidebar nav a').forEach(link=>link.addEventListener('click',()=>{document.querySelectorAll('.sidebar nav a').forEach(other=>other.removeAttribute('aria-current'));link.setAttribute('aria-current','location');}));
