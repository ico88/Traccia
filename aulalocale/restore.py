"""Restore a verified export into a NEW directory, without overwriting an archive."""
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import argparse
import hashlib
import json
import math
import os
import shutil
import sqlite3
import zipfile
from uuid import UUID


def restore(backup:Path,destination:Path):
    destination=destination.resolve()
    if destination.exists():raise ValueError('Destination already exists: choose a new directory')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(backup) as bundle,TemporaryDirectory(dir=destination.parent,prefix='.restore-') as temp:
        infos=bundle.infolist()
        if len(infos)>100000 or sum(i.file_size for i in infos)>50*1024**3:raise ValueError('Backup exceeds restore limits')
        names=[i.filename for i in infos]
        if len(names)!=len(set(names)) or 'manifest.json' not in names:raise ValueError('Invalid archive entries')
        info=bundle.getinfo('manifest.json')
        if info.file_size>20*1024**2:raise ValueError('Manifest too large')
        manifest=json.loads(bundle.read('manifest.json'))
        from . import ARCHIVE_SCHEMA
        if manifest.get('schema') not in {5,6,ARCHIVE_SCHEMA}:raise ValueError('Unsupported backup schema')
        expected=manifest.get('files',{})
        if set(names)!={'manifest.json',*expected} or 'aulalocale.sqlite3' not in expected:raise ValueError('Manifest does not match archive')
        staging=Path(temp)/'archive';staging.mkdir()
        for name,digest in expected.items():
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or len(path.parts)>2:raise ValueError('Unsafe backup path')
            if name!='aulalocale.sqlite3' and (len(path.parts)!=2 or path.parts[0] not in {'originals','enhanced','materials','speakers','evidence'}):raise ValueError('Unexpected backup file')
            if bundle.getinfo(name).external_attr>>16 & 0o170000 == 0o120000:raise ValueError('Symbolic links are not allowed')
            target=staging.joinpath(*path.parts);target.parent.mkdir(exist_ok=True)
            checksum=hashlib.sha256()
            with bundle.open(name) as source,target.open('wb') as output:
                for chunk in iter(lambda:source.read(4*1024**2),b''):checksum.update(chunk);output.write(chunk)
            if checksum.hexdigest()!=digest:raise ValueError('Backup checksum mismatch')
        with sqlite3.connect(staging/'aulalocale.sqlite3') as c:
            if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')
            if c.execute('PRAGMA user_version').fetchone()[0]!=manifest['schema']:raise ValueError('Database schema mismatch')
            if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Broken database references')
            tables=['subjects','lessons','audio_jobs','study_jobs','transcripts','notes','materials']
            if manifest['schema']>=7:tables+=['archive_identity','note_templates','subject_preferences','lecture_annotations','study_questions']
            for table in tables:
                for (identifier,) in c.execute('SELECT id FROM '+table):
                    try:valid=str(UUID(identifier))==identifier
                    except (ValueError,TypeError,AttributeError):valid=False
                    if not valid:raise ValueError('Invalid archive identifier')
            for identifier,filename,checksum in c.execute('SELECT id,storage_name,sha256 FROM lessons'):
                if Path(filename).name!=filename or '\\' in filename or Path(filename).stem!=identifier or 'originals/'+filename not in expected or expected['originals/'+filename]!=checksum:
                    raise ValueError('Invalid original asset reference')
            for (identifier,) in c.execute("SELECT id FROM study_jobs WHERE kind='speakers' AND status='completed'"):
                if 'speakers/'+identifier+'.json' not in expected:raise ValueError('Missing speaker analysis')
            for (identifier,) in c.execute("SELECT id FROM study_jobs WHERE kind='evidence' AND status='completed'"):
                if 'evidence/'+identifier+'.json' not in expected:raise ValueError('Missing evidence review')
            for identifier,filename in c.execute('SELECT id,filename FROM materials'):
                if filename!=identifier+'.png' or 'materials/'+filename not in expected:raise ValueError('Invalid image reference')
            if manifest['schema']>=7:
                for start,duration,material_subject,lesson_subject in c.execute('SELECT a.start,l.duration_seconds,m.subject_id,l.subject_id FROM lecture_annotations a JOIN lessons l ON a.lesson_id=l.id LEFT JOIN materials m ON a.material_id=m.id'):
                    if not math.isfinite(start) or not 0<=start<=duration or material_subject is not None and material_subject!=lesson_subject:raise ValueError('Invalid lecture annotation reference')
            # A portable backup is data, not authorization to execute stored jobs.
            for table in ['audio_jobs','study_jobs']:
                c.execute("UPDATE "+table+" SET status='cancelled',error='Restored from backup: start a new job explicitly' WHERE status IN ('queued','running','interrupted')")
        if destination.exists():raise ValueError('Destination appeared during restore')
        staging.rename(destination)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path);parser.add_argument('--data',type=Path,required=True);args=parser.parse_args()
    try:restore(args.backup,args.data)
    except (ValueError,OSError,zipfile.BadZipFile,sqlite3.Error) as error:parser.exit(1,str(error)+'\n')
    print('Archive restored. Models and native runtimes must be installed separately.')
if __name__=='__main__':main()
