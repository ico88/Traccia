"""Portable transcript exports with explicit revision, timing and available speaker labels."""
from contextlib import closing
from typing import Literal
from uuid import UUID
import html,re
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import Response
from .study import latest_transcript,transcript_record
from .speakers import dominant_speaker


def clock(seconds,subtitle=False):
    ms=max(0,round(seconds*1000));hours,rest=divmod(ms,3600000);minutes,rest=divmod(rest,60000);secs,millis=divmod(rest,1000)
    return f'{hours:02}:{minutes:02}:{secs:02}'+(f',{millis:03}' if subtitle else '')
def markdown(text):return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])',r'\\\1',html.escape(text))

def transcript_export_router(engine,authenticate):
    router=APIRouter(prefix='/api/v1',dependencies=[Depends(authenticate)])
    @router.get('/lessons/{lesson_id}/transcript/export')
    def export(lesson_id:UUID,format:Literal['txt','md','srt']='txt',revision_id:UUID|None=None,timestamps:bool=True,speakers:bool=False,language:Literal['en','it']='en'):
        with closing(engine.connect()) as c:
            lesson=c.execute('SELECT * FROM lessons WHERE id=?',(str(lesson_id),)).fetchone()
            if not lesson:raise HTTPException(404,'Lesson not found')
            transcript=transcript_record(c.execute('SELECT * FROM transcripts WHERE id=? AND lesson_id=?',(str(revision_id),str(lesson_id))).fetchone()) if revision_id else latest_transcript(c,lesson_id)
            if not transcript:raise HTTPException(404,'Transcript revision not found')
        analysis=engine.speakers.latest(lesson_id) if speakers else None
        rows=[]
        for index,segment in enumerate(transcript['segments'],1):
            text=segment['text'];speaker=None
            if analysis:
                key=dominant_speaker(segment['start'],segment['end'],analysis['segments'])
                speaker=('Voci sovrapposte' if language=='it' else 'Overlapping voices') if key=='overlap' else analysis.get('labels',{}).get(key,key)
            if speaker:text=f'{speaker}: {text}'
            if format=='srt':rows.append(f"{index}\n{clock(segment['start'],True)} --> {clock(segment['end'],True)}\n{html.escape(text)}\n")
            elif format=='md':rows.append((f"**{clock(segment['start'])}** " if timestamps else '')+markdown(text))
            else:rows.append((f"[{clock(segment['start'])}] " if timestamps else '')+text)
        content='\n'.join(rows) if format=='srt' else ('# '+markdown(lesson['title'])+'\n\n' if format=='md' else lesson['title']+'\n\n')+'\n\n'.join(rows)+'\n'
        media={'txt':'text/plain','md':'text/markdown','srt':'application/x-subrip'}[format]
        return Response(content,media_type=media,headers={'Content-Disposition':f'attachment; filename="transcript-{transcript["id"]}.{format}"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
    return router
