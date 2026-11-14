"""Immutable audio originals and lesson metadata for a single local user."""
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4
import hashlib
import math
import sqlite3
import subprocess

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
import imageio_ffmpeg
import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from .suggestions import audio_suggestions

MAX_UPLOAD_BYTES = 512 * 1024 * 1024
FORMATS = {".mp3": (MP3, "audio/mpeg"), ".wav": (WAVE, "audio/wav"),
           ".flac": (FLAC, "audio/flac"), ".m4a": (MP4, "audio/mp4")}


class Lesson(BaseModel):
    id: UUID
    subject_id: UUID
    title: str
    teacher: str
    lecture_date: date | None
    original_filename: str
    sha256: str
    size_bytes: int
    duration_seconds: float
    sample_rate: int
    channels: int
    media_type: str
    created_at: datetime


def migrate_lessons(connection):
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > 3:
        raise RuntimeError("Database is newer than this application; refusing to downgrade")
    connection.execute("""CREATE TABLE IF NOT EXISTS lessons (
        id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES subjects(id),
        title TEXT NOT NULL, teacher TEXT NOT NULL, lecture_date TEXT,
        original_filename TEXT NOT NULL, sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL, duration_seconds REAL NOT NULL,
        sample_rate INTEGER NOT NULL, channels INTEGER NOT NULL,
        media_type TEXT NOT NULL, created_at TEXT NOT NULL,
        storage_name TEXT NOT NULL UNIQUE, UNIQUE(subject_id, sha256))""")
    connection.execute("CREATE INDEX IF NOT EXISTS lessons_subject_date ON lessons(subject_id, created_at, id)")
    if version < 2:
        connection.execute("PRAGMA user_version = 2")


def inspect_audio(path: Path, suffix: str):
    try:
        audio = mutagen.File(path)
        expected, media_type = FORMATS[suffix]
        if not isinstance(audio, expected):
            raise ValueError("Content does not match extension")
        info = audio.info
        duration, rate, channels = float(info.length), int(info.sample_rate), int(info.channels)
        if not math.isfinite(duration) or duration <= 0 or rate <= 0 or channels <= 0:
            raise ValueError("Invalid audio metadata")
    except (mutagen.MutagenError, ValueError, AttributeError, TypeError) as error:
        raise HTTPException(422, "Invalid audio or content does not match its extension") from error
    # Decode the entire stream; metadata alone does not establish decodability.
    try:
        result = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-v", "error", "-xerror",
             "-protocol_whitelist", "file,pipe", "-i", str(path),
             "-map", "0:a:0", "-vn", "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180, check=False)
    except subprocess.TimeoutExpired as error:
        raise HTTPException(422, "Audio validation exceeded 180 seconds") from error
    except (OSError, RuntimeError) as error:
        raise HTTPException(503, "Local audio decoder is unavailable") from error
    if result.returncode:
        raise HTTPException(422, "Audio cannot be fully decoded")
    return dict(duration_seconds=duration, sample_rate=rate, channels=channels, media_type=media_type)


def lessons_router(root, connect, authenticate):
    router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticate)])
    originals = root / "originals"
    staging = root / "staging"

    def subject_exists(subject_id):
        with closing(connect()) as connection:
            if not connection.execute("SELECT 1 FROM subjects WHERE id=?", (str(subject_id),)).fetchone():
                raise HTTPException(404, "Subject not found")

    def find_lesson(lesson_id):
        with closing(connect()) as connection:
            row = connection.execute("SELECT * FROM lessons WHERE id=?", (str(lesson_id),)).fetchone()
        if row is None:
            raise HTTPException(404, "Lesson not found")
        return dict(row)

    @router.post("/audio/preview")
    def preview_audio(file: UploadFile = File(...)):
        if file.size is not None and file.size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Audio exceeds the 512 MiB limit")
        return audio_suggestions(file.file, file.filename or "", FORMATS)

    @router.post("/subjects/{subject_id}/lessons", status_code=201, response_model=Lesson)
    def import_lesson(subject_id: UUID, file: UploadFile = File(...),
                      title: str = Form(..., min_length=1, max_length=200),
                      teacher: str = Form("", max_length=200),
                      lecture_date: date | None = Form(None)):
        subject_exists(subject_id)
        title = title.strip()
        if not title:
            raise HTTPException(422, "Title cannot be blank")
        filename = (file.filename or "").replace("\\", "/").split("/")[-1]
        suffix = Path(filename).suffix.lower()
        if suffix not in FORMATS or len(filename) > 255 or any(ord(c) < 32 for c in filename):
            raise HTTPException(422, "Use an MP3, WAV, M4A or FLAC file with a valid filename")
        if file.size is not None and file.size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Audio exceeds the 512 MiB limit")
        staging.mkdir(parents=True, exist_ok=True)
        originals.mkdir(parents=True, exist_ok=True)
        temporary = None
        destination = None
        committed = False
        try:
            digest, size = hashlib.sha256(), 0
            with NamedTemporaryFile(dir=staging, suffix=suffix, delete=False) as target:
                temporary = Path(target.name)
                while chunk := file.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, "Audio exceeds the 512 MiB limit")
                    digest.update(chunk)
                    target.write(chunk)
            checksum = digest.hexdigest()
            with closing(connect()) as connection:
                existing = connection.execute(
                    "SELECT id FROM lessons WHERE subject_id=? AND sha256=?",
                    (str(subject_id), checksum)).fetchone()
            if existing:
                raise HTTPException(409, {"message": "Audio already imported in this subject", "lesson_id": existing["id"]})
            metadata = inspect_audio(temporary, suffix)
            identifier = str(uuid4())
            storage_name = identifier + suffix
            destination = originals / storage_name
            record = dict(id=identifier, subject_id=str(subject_id), title=title,
                          teacher=teacher.strip(), lecture_date=lecture_date.isoformat() if lecture_date else None,
                          original_filename=filename, sha256=checksum, size_bytes=size,
                          created_at=datetime.now(timezone.utc).isoformat(),
                          storage_name=storage_name, **metadata)
            # Rename on the same filesystem; a failed DB write removes the new file.
            temporary.replace(destination)
            with closing(connect()) as connection, connection:
                connection.execute("""INSERT INTO lessons VALUES (
                    :id,:subject_id,:title,:teacher,:lecture_date,:original_filename,
                    :sha256,:size_bytes,:duration_seconds,:sample_rate,:channels,
                    :media_type,:created_at,:storage_name)""", record)
            committed = True
            return record
        except sqlite3.IntegrityError as error:
            raise HTTPException(409, "Audio was imported concurrently; refresh the lesson list") from error
        except OSError as error:
            raise HTTPException(507, "Unable to store the audio; check disk space and permissions") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if destination is not None and not committed:
                destination.unlink(missing_ok=True)

    @router.get("/subjects/{subject_id}/lessons", response_model=list[Lesson])
    def list_lessons(subject_id: UUID, limit: int = 50, offset: int = 0):
        subject_exists(subject_id)
        if not 1 <= limit <= 200 or offset < 0:
            raise HTTPException(422, "Invalid pagination")
        with closing(connect()) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM lessons WHERE subject_id=? ORDER BY created_at,id LIMIT ? OFFSET ?",
                (str(subject_id), limit, offset))]

    @router.get("/lessons/{lesson_id}", response_model=Lesson)
    def get_lesson(lesson_id: UUID):
        return find_lesson(lesson_id)

    @router.get("/lessons/{lesson_id}/audio")
    def get_original(lesson_id: UUID):
        record = find_lesson(lesson_id)
        path = originals / record["storage_name"]
        if not path.is_file():
            raise HTTPException(404, "Original audio is missing from the archive")
        return FileResponse(path, media_type=record["media_type"],
                            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    return router
