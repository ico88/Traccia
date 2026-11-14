"""Validated image attachments and portable, consistent archive exports."""
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from uuid import UUID, uuid4
import hashlib
import io
import json
import sqlite3
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from PIL import Image, ImageDraw, ImageFont, ImageOps, PngImagePlugin, UnidentifiedImageError
from datetime import datetime
from pydantic import BaseModel
import textwrap

MAX_IMAGE_BYTES=20*1024*1024
Image.MAX_IMAGE_PIXELS=20_000_000


def migrate_materials(c):
    c.execute('''CREATE TABLE IF NOT EXISTS materials(id TEXT PRIMARY KEY,
        subject_id TEXT NOT NULL REFERENCES subjects(id),caption TEXT NOT NULL,
        filename TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL)''')
    c.execute('PRAGMA user_version=5')


class OutlineInput(BaseModel):
    base_revision: UUID


def materials_router(root,connect,authenticate,worker):
    router=APIRouter(prefix='/api/v1',dependencies=[Depends(authenticate)])
    def subject(c,identifier):
        if not c.execute('SELECT 1 FROM subjects WHERE id=?',(str(identifier),)).fetchone():raise HTTPException(404,'Subject not found')

    @router.post('/subjects/{subject_id}/materials',status_code=201)
    def upload(subject_id:UUID,file:UploadFile=File(...),caption:str=Form('',max_length=500)):
        with closing(connect()) as c:subject(c,subject_id)
        data=file.file.read(MAX_IMAGE_BYTES+1)
        if len(data)>MAX_IMAGE_BYTES:raise HTTPException(413,'Image exceeds 20 MiB')
        try:
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in {'PNG','JPEG','WEBP'}:raise ValueError()
                if probe.width*probe.height>Image.MAX_IMAGE_PIXELS:raise ValueError()
                probe.verify()
            with Image.open(io.BytesIO(data)) as source:
                image=ImageOps.exif_transpose(source).convert('RGBA' if 'A' in source.getbands() else 'RGB')
                width,height=image.size
        except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError) as error:
            raise HTTPException(422,'Use a valid PNG, JPEG or WebP image up to 20 megapixels') from error
        directory=root/'materials';directory.mkdir(exist_ok=True)
        identifier=str(uuid4());filename=identifier+'.png';target=directory/filename
        try:
            # Re-encode pixels only; exclude metadata and executable formats.
            image.save(target,format='PNG')
            with closing(connect()) as c,c:c.execute('INSERT INTO materials VALUES (?,?,?,?,?,?)',(identifier,str(subject_id),caption.strip(),filename,width,height))
        except Exception:
            target.unlink(missing_ok=True);raise
        return {'id':identifier,'subject_id':str(subject_id),'caption':caption.strip(),'width':width,'height':height}

    @router.post('/subjects/{subject_id}/materials/outline',status_code=201)
    def outline(subject_id:UUID,options:OutlineInput):
        from .study import latest_notes
        from .note_consolidation import conflict_label
        with closing(connect()) as c:
            subject(c,subject_id)
            notes=latest_notes(c,subject_id)
            name=c.execute('SELECT title FROM subjects WHERE id=?',(str(subject_id),)).fetchone()[0]
        if not notes:raise HTTPException(409,'Accetta una dispensa prima di generare la mappa.')
        if notes['id']!=str(options.base_revision):raise HTTPException(409,'La dispensa è cambiata: ricarica prima di generare la mappa.')
        chapters=notes['chapters'][:12]
        if not chapters:raise HTTPException(409,'La dispensa non contiene sezioni.')
        rows=(len(chapters)+1)//2;width=1400;height=230+rows*190
        canvas=Image.new('RGB',(width,height),'#f5f8ef');draw=ImageDraw.Draw(canvas)
        title_font=ImageFont.load_default(size=32);font=ImageFont.load_default(size=23);small=ImageFont.load_default(size=18)
        draw.rounded_rectangle((40,30,1360,150),radius=22,fill='#2d604b')
        draw.text((70,48),'Mappa dei capitoli',font=title_font,fill='white')
        draw.text((70,100),name[:75],font=small,fill='#dae9d1')
        for i,chapter in enumerate(chapters):
            x=40+(i%2)*680;y=190+(i//2)*190
            draw.rounded_rectangle((x,y,x+640,y+155),radius=16,fill='white',outline='#cad8bf',width=2)
            draw.text((x+22,y+18),f'{i+1:02d}',font=small,fill='#6c8a59')
            wrapped='\n'.join(textwrap.wrap(chapter['title'],width=43)[:3])
            draw.multiline_text((x+22,y+50),wrapped,font=font,fill='#284b36',spacing=8)
        footer=f"Indice della dispensa · {len(chapters)} di {len(notes['chapters'])} sezioni"
        draw.text((45,height-35),footer,font=ImageFont.load_default(size=15),fill='#6c805e')
        identifier=str(uuid4());filename=identifier+'.png';directory=root/'materials';directory.mkdir(exist_ok=True)
        caption='Mappa dei capitoli · versione del '+datetime.fromisoformat(notes['created_at']).strftime('%d/%m/%Y %H:%M UTC')
        if len(notes['chapters'])>12:caption+=' · prime 12 sezioni'
        target=directory/filename
        try:
            provenance=PngImagePlugin.PngInfo();provenance.add_text('source_revision',notes['id'])
            canvas.save(target,format='PNG',pnginfo=provenance)
            with closing(connect()) as c,c:c.execute('INSERT INTO materials VALUES (?,?,?,?,?,?)',(identifier,str(subject_id),caption,filename,width,height))
        except Exception:
            target.unlink(missing_ok=True);raise
        return {'id':identifier,'subject_id':str(subject_id),'caption':caption,'width':width,'height':height}

    @router.get('/subjects/{subject_id}/materials')
    def materials(subject_id:UUID):
        with closing(connect()) as c:
            subject(c,subject_id)
            return [{key:row[key] for key in ['id','subject_id','caption','width','height']} for row in c.execute('SELECT * FROM materials WHERE subject_id=? ORDER BY rowid',(str(subject_id),))]

    @router.get('/materials/{identifier}/image')
    def image(identifier:UUID):
        with closing(connect()) as c:row=c.execute('SELECT filename FROM materials WHERE id=?',(str(identifier),)).fetchone()
        if not row or not (root/'materials'/row['filename']).is_file():raise HTTPException(404,'Image not found')
        return FileResponse(root/'materials'/row['filename'],media_type='image/png',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

    @router.get('/subjects/{subject_id}/study-export')
    def study_export(subject_id:UUID):
        from .study import latest_notes
        from .note_consolidation import conflict_label
        with closing(connect()) as c:
            subject(c,subject_id)
            name=c.execute('SELECT title FROM subjects WHERE id=?',(str(subject_id),)).fetchone()[0]
            notes=latest_notes(c,subject_id)
            images=[dict(row) for row in c.execute('SELECT * FROM materials WHERE subject_id=? ORDER BY rowid',(str(subject_id),))]
        if not notes:raise HTTPException(404,'Accept a note proposal before exporting')
        exports=root/'exports';exports.mkdir(exist_ok=True)
        with NamedTemporaryFile(dir=exports,suffix='.zip',delete=False) as output:path=Path(output.name)
        try:
            lines=['# '+name,'','Dispensa da verificare sulle fonti.','']
            for chapter in notes['chapters']:
                lines+=['## '+chapter['title'],'',chapter['text'],'']
                warning=conflict_label(chapter,notes['chapters'])
                if warning:lines+=['**'+warning+'**','']
                lines += [f"- Fonte: lezione {r['lesson_id']}, revisione {r['revision_id']}, segmento {r['segment_id']}, tempo {r['start']} s" for r in chapter['sources']]
                lines.append('')
            with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
                for image in images:
                    file=root/'materials'/image['filename']
                    if not file.is_file():raise ValueError('Missing image')
                    bundle.write(file,'immagini/'+image['filename'])
                    lines+=['## Immagine didattica','',image['caption'],'',f"![Immagine](immagini/{image['filename']})",'']
                bundle.writestr('dispensa.md','\n'.join(lines))
        except Exception as error:
            path.unlink(missing_ok=True);raise HTTPException(409,'Export failed; check archive files and disk space') from error
        return FileResponse(path,media_type='application/zip',filename='dispensa-con-immagini.zip',headers={'Cache-Control':'no-store'},background=BackgroundTask(path.unlink,missing_ok=True))

    @router.get('/backup')
    def backup():
        exports=root/'exports';exports.mkdir(exist_ok=True)
        with NamedTemporaryFile(dir=exports,suffix='.zip',delete=False) as output:path=Path(output.name)
        try:
            with TemporaryDirectory(dir=exports) as temp:
                snapshot=Path(temp)/'aulalocale.sqlite3'
                # A SQLite snapshot and immutable originals make the backup portable.
                with worker.lock:
                    with closing(connect()) as source,closing(sqlite3.connect(snapshot)) as target:source.backup(target)
                    with closing(sqlite3.connect(snapshot)) as c:
                        names=['originals/'+r[0] for r in c.execute('SELECT storage_name FROM lessons')]
                        jobs=[r[0] for r in c.execute("SELECT id FROM audio_jobs WHERE status='completed'")]
                        names+=['enhanced/'+identifier+'.mp3' for identifier in jobs]
                        names+=['enhanced/'+identifier+'.wav' for identifier in jobs if (root/'enhanced'/(identifier+'.wav')).is_file()]
                        names+=['materials/'+r[0] for r in c.execute('SELECT filename FROM materials')]
                    entries={'aulalocale.sqlite3':snapshot,**{name:root/name for name in names}}
                    manifest={'schema':5,'files':{}}
                    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as bundle:
                        for name,file in entries.items():
                            if not file.is_file():raise ValueError('An archived file is missing; backup aborted')
                            digest=hashlib.sha256()
                            with file.open('rb') as data:
                                for chunk in iter(lambda:data.read(4*1024*1024),b''):digest.update(chunk)
                            manifest['files'][name]=digest.hexdigest();bundle.write(file,name)
                        bundle.writestr('manifest.json',json.dumps(manifest))
        except Exception as error:
            path.unlink(missing_ok=True)
            raise HTTPException(409,'Backup non riuscito: controlla integrità dei file e spazio disponibile.') from error
        return FileResponse(path,media_type='application/zip',filename='aulalocale-backup.zip',headers={'Cache-Control':'no-store'},background=BackgroundTask(path.unlink,missing_ok=True))
    return router
