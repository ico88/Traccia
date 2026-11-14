"""Persistent, single-worker local audio processing; originals are never modified."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Literal
from uuid import UUID, uuid4
import fcntl
import subprocess
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
import imageio_ffmpeg

PRESETS = {
    'light': 'highpass=f=60,afftdn=nr=6:nf=-35,dynaudnorm=f=250:g=15:p=0.9:m=3,alimiter=limit=0.95:level=false:latency=true',
    'balanced': 'highpass=f=70,afftdn=nr=12:nf=-30,dynaudnorm=f=250:g=15:p=0.9:m=5,alimiter=limit=0.95:level=false:latency=true',
    'strong': 'highpass=f=80,afftdn=nr=18:nf=-25,dynaudnorm=f=250:g=15:p=0.9:m=7,alimiter=limit=0.95:level=false:latency=true',
}


class EnhancementInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    preset: Literal['light', 'balanced', 'strong'] = 'balanced'


class AudioJob(BaseModel):
    id: UUID
    lesson_id: UUID
    preset: str
    status: str
    progress: float
    error: str | None
    created_at: str
    updated_at: str
    engine: str
    filter: str


def migrate_enhancement(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS audio_jobs (
        id TEXT PRIMARY KEY, lesson_id TEXT NOT NULL REFERENCES lessons(id),
        preset TEXT NOT NULL, status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0,
        error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        engine TEXT NOT NULL, filter TEXT NOT NULL)''')
    connection.execute('''CREATE UNIQUE INDEX IF NOT EXISTS audio_jobs_active
        ON audio_jobs(lesson_id,preset) WHERE status IN ('queued','running')''')
    if connection.execute('PRAGMA user_version').fetchone()[0] < 3:
        connection.execute('PRAGMA user_version = 3')


def now():
    return datetime.now(timezone.utc).isoformat()


class AudioWorker:
    def __init__(self, root, connect):
        self.root, self.connect = root, connect
        self.stop_event, self.wake = Event(), Event()
        self.lock = Lock()
        self.process = None
        self.active_id = None
        self.thread = None
        self.lease = None

    def start(self):
        self.lease = (self.root / 'audio-worker.lock').open('a')
        try:
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lease.close()
            raise RuntimeError('Archive already open in another worker; use one server process')
        self.outputs = self.root / 'enhanced'
        self.outputs.mkdir(exist_ok=True)
        with closing(self.connect()) as connection, connection:
            connection.execute("UPDATE audio_jobs SET status='queued',progress=0,error=NULL,updated_at=? WHERE status IN ('running','interrupted')", (now(),))
        if getattr(self, 'study', None):
            self.study.recover()
        self.thread = Thread(target=self.run, name='audio-worker', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                with self.lock:
                    if self.process is not None and self.process.poll() is None:
                        self.process.kill()
                self.thread.join()
        if self.lease:
            self.lease.close()

    def get(self, job_id):
        with closing(self.connect()) as connection:
            row = connection.execute('SELECT * FROM audio_jobs WHERE id=?', (str(job_id),)).fetchone()
        if row is None:
            raise HTTPException(404, 'Audio job not found')
        return dict(row)

    def update(self, job_id, status, progress=0, error=None):
        with closing(self.connect()) as connection, connection:
            connection.execute('UPDATE audio_jobs SET status=?,progress=?,error=?,updated_at=? WHERE id=?',
                               (status, progress, error, now(), job_id))

    def cancel(self, job_id):
        with self.lock:
            job = self.get(job_id)
            if job['status'] in ('queued', 'running'):
                self.update(str(job_id), 'cancelled', job['progress'])
                if self.active_id == str(job_id) and self.process is not None and self.process.poll() is None:
                    self.process.terminate()
        return self.get(job_id)

    def run(self):
        while not self.stop_event.is_set():
            try:
                with closing(self.connect()) as connection:
                    row = connection.execute("SELECT * FROM audio_jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
                if row:
                    self.execute(dict(row))
                    continue
                if getattr(self, 'study', None) and self.study.next():
                    continue
            except Exception:
                # An unavailable database must not cause a busy retry loop.
                logger.exception("Audio worker iteration failed")
            self.wake.wait(.5)
            self.wake.clear()

    def execute(self, job):
        identifier = job['id']
        partial = self.outputs / (identifier + '.part.mp3')
        final = self.outputs / (identifier + '.mp3')
        try:
            with self.lock:
                if self.stop_event.is_set() or self.get(identifier)['status'] != 'queued':
                    return
                self.update(identifier, 'running')
                self.active_id = identifier
            partial.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
            with closing(self.connect()) as connection:
                lesson = connection.execute('SELECT * FROM lessons WHERE id=?', (job['lesson_id'],)).fetchone()
            if lesson is None or not (self.root / 'originals' / lesson['storage_name']).is_file():
                raise ValueError('Original audio is missing')
            executable = imageio_ffmpeg.get_ffmpeg_exe()
            engine = subprocess.run([executable, '-version'], capture_output=True, text=True, check=True, timeout=10).stdout.splitlines()[0]
            with closing(self.connect()) as connection, connection:
                connection.execute('UPDATE audio_jobs SET engine=? WHERE id=?', (engine, identifier))
            command = [executable, '-nostdin', '-v', 'error', '-y', '-protocol_whitelist', 'file,pipe',
                       '-i', str(self.root / 'originals' / lesson['storage_name']), '-map', '0:a:0', '-vn',
                       '-af', job['filter'], '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '96k',
                       '-progress', 'pipe:1', '-nostats', str(partial)]
            with self.lock:
                if self.stop_event.is_set() or self.get(identifier)['status'] == 'cancelled':
                    if self.stop_event.is_set() and self.get(identifier)['status'] != 'cancelled':
                        self.update(identifier, 'interrupted')
                    return
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                                text=True, bufsize=1)
            elapsed = 0
            for line in self.process.stdout:
                key, _, value = line.strip().partition('=')
                if key == 'out_time_us':
                    try:
                        elapsed = max(0, int(value) / 1000000)
                    except ValueError:
                        continue
                if key == 'progress':
                    with self.lock:
                        if self.get(identifier)['status'] == 'running':
                            self.update(identifier, 'running', min(99, elapsed / lesson['duration_seconds'] * 100))
            code = self.process.wait()
            self.process.stdout.close()
            with self.lock:
                if self.get(identifier)['status'] == 'cancelled':
                    return
                if self.stop_event.is_set():
                    self.update(identifier, 'interrupted')
                    return
                if code != 0 or not partial.is_file() or partial.stat().st_size == 0:
                    raise ValueError('Audio processing failed; check the original and free disk space')
                partial.replace(final)
                self.update(identifier, 'completed', 100)
        except Exception as error:
            with self.lock:
                if self.get(identifier)['status'] not in ('cancelled', 'completed'):
                    message = str(error) if isinstance(error, ValueError) else 'Unable to process audio; check disk space and local decoder'
                    self.update(identifier, 'interrupted' if self.stop_event.is_set() else 'failed', error=message)
        finally:
            with self.lock:
                if self.process is not None:
                    if self.process.poll() is None:
                        self.process.kill()
                    self.process.wait()
                    if self.process.stdout:
                        self.process.stdout.close()
                self.process = None
                self.active_id = None
            partial.unlink(missing_ok=True)
            if self.get(identifier)['status'] != 'completed':
                final.unlink(missing_ok=True)


def enhancement_router(root, connect, authenticate, worker):
    router = APIRouter(prefix='/api/v1', dependencies=[Depends(authenticate)])

    def require_lesson(identifier):
        with closing(connect()) as connection:
            if not connection.execute('SELECT 1 FROM lessons WHERE id=?', (str(identifier),)).fetchone():
                raise HTTPException(404, 'Lesson not found')

    @router.post('/lessons/{lesson_id}/enhancements', response_model=AudioJob, status_code=202)
    def create_job(lesson_id: UUID, options: EnhancementInput):
        require_lesson(lesson_id)
        with worker.lock:
            with closing(connect()) as connection, connection:
                row = connection.execute("SELECT * FROM audio_jobs WHERE lesson_id=? AND preset=? AND (status IN ('queued','running') OR (status='completed' AND filter=?)) ORDER BY created_at DESC LIMIT 1",
                                         (str(lesson_id), options.preset, PRESETS[options.preset])).fetchone()
                if row:
                    return dict(row)
                identifier, timestamp = str(uuid4()), now()
                connection.execute('''INSERT INTO audio_jobs
                    (id,lesson_id,preset,status,progress,error,created_at,updated_at,engine,filter)
                    VALUES (?,?,?,'queued',0,NULL,?,?,'ffmpeg',?)''',
                                   (identifier, str(lesson_id), options.preset, timestamp, timestamp, PRESETS[options.preset]))
            result = worker.get(identifier)
            worker.wake.set()
            return result

    @router.get('/lessons/{lesson_id}/enhancements', response_model=list[AudioJob])
    def list_jobs(lesson_id: UUID):
        require_lesson(lesson_id)
        with closing(connect()) as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM audio_jobs WHERE lesson_id=? ORDER BY created_at DESC,id', (str(lesson_id),))]

    @router.get('/audio-jobs/{job_id}', response_model=AudioJob)
    def get_job(job_id: UUID):
        return worker.get(job_id)

    @router.post('/audio-jobs/{job_id}/cancel', response_model=AudioJob)
    def cancel_job(job_id: UUID):
        return worker.cancel(job_id)

    @router.get('/audio-jobs/{job_id}/audio')
    def result_audio(job_id: UUID):
        job = worker.get(job_id)
        if job['status'] != 'completed':
            raise HTTPException(409, 'Improved audio is not ready')
        path = root / 'enhanced' / (str(job_id) + '.mp3')
        if not path.is_file():
            raise HTTPException(404, 'Improved audio is missing')
        return FileResponse(path, media_type='audio/mpeg', headers={'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})

    return router
