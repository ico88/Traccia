import hashlib
import io
import sqlite3
import subprocess
import wave
from uuid import uuid4

import imageio_ffmpeg
import pytest
from fastapi.testclient import TestClient

from aulalocale.app import create_app
from aulalocale import lessons

TOKEN = "lesson-test-token-" * 3
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b"\0\0" * 1600)
    return buffer.getvalue()


def subject(client):
    return client.post("/api/v1/subjects", headers=HEADERS,
                       json={"title": "Farmacologia"}).json()["id"]


def upload(client, identifier, content=None, filename="lesson.wav", **fields):
    return client.post(f"/api/v1/subjects/{identifier}/lessons", headers=HEADERS,
                       data={"title": " Recettori ", **fields},
                       files={"file": (filename, wav_bytes() if content is None else content, "audio/wav")})


def test_import_restart_original_and_ranges(tmp_path):
    content = wav_bytes()
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        sid = subject(client)
        response = upload(client, sid, content, filename="../../private.wav",
                          teacher=" Docente ", lecture_date="2026-10-31")
        assert response.status_code == 201, response.text
        record = response.json()
        assert record["original_filename"] == "private.wav"
        assert record["title"] == "Recettori"
        assert record["teacher"] == "Docente"
        assert record["lecture_date"] == "2026-10-31"
        assert record["duration_seconds"] == pytest.approx(.1)
        assert record["sample_rate"] == 16000
        assert record["channels"] == 1
        assert record["sha256"] == hashlib.sha256(content).hexdigest()
        assert "storage_name" not in record
        lid = record["id"]
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert client.get(f"/api/v1/subjects/{sid}/lessons", headers=HEADERS).json() == [record]
        assert client.get(f"/api/v1/lessons/{lid}", headers=HEADERS).json() == record
        url = f"/api/v1/lessons/{lid}/audio"
        assert client.get(url).status_code == 401
        assert client.get(url, headers=HEADERS).content == content
        partial = client.get(url, headers={**HEADERS, "Range": "bytes=0-15"})
        assert partial.status_code == 206
        assert partial.content == content[:16]
        assert "no-store" in partial.headers["cache-control"]
    assert list((tmp_path / "staging").iterdir()) == []
    assert len(list((tmp_path / "originals").iterdir())) == 1


def test_duplicates_per_subject(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        sid = subject(client)
        first = upload(client, sid)
        duplicate = upload(client, sid)
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["lesson_id"] == first.json()["id"]
        assert upload(client, subject(client)).status_code == 201
    assert len(list((tmp_path / "originals").iterdir())) == 2
    assert not list((tmp_path / "staging").iterdir())


@pytest.mark.parametrize("content,filename,fields", [
    (b"not audio", "fake.wav", {}), (b"", "empty.wav", {}),
    (wav_bytes(), "fake.mp3", {}), (wav_bytes(), "bad.exe", {}),
    (wav_bytes(), "valid.wav", {"title": "   "}),
    (wav_bytes(), "valid.wav", {"lecture_date": "not a date"}),
])
def test_rejects_invalid_imports(tmp_path, content, filename, fields):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        sid = subject(client)
        assert upload(client, sid, content, filename, **fields).status_code == 422
        assert client.get(f"/api/v1/subjects/{sid}/lessons", headers=HEADERS).json() == []
    assert not list((tmp_path / "staging").glob("*"))
    assert not list((tmp_path / "originals").glob("*"))


def test_upload_limit_and_decoder_failure_cleanup(tmp_path, monkeypatch):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        sid = subject(client)
        monkeypatch.setattr(lessons, "MAX_UPLOAD_BYTES", 20)
        assert upload(client, sid).status_code == 413
        monkeypatch.setattr(lessons, "MAX_UPLOAD_BYTES", 100000)
        monkeypatch.setattr(lessons.subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess([], 1))
        assert upload(client, sid).status_code == 422
    assert not list((tmp_path / "staging").glob("*"))
    assert not list((tmp_path / "originals").glob("*"))


def test_unknown_ids_and_authentication(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert upload(client, uuid4()).status_code == 404
        assert client.get(f"/api/v1/lessons/{uuid4()}", headers=HEADERS).status_code == 404
        sid = subject(client)
        path = f"/api/v1/subjects/{sid}/lessons"
        assert client.get(path).status_code == 401
        assert client.post(path, data={"title": "No"}, files={"file": ("x.wav", wav_bytes())}).status_code == 401
        assert client.get(path+"?limit=0", headers=HEADERS).status_code == 422


@pytest.mark.parametrize("suffix,codec", [("mp3", "libmp3lame"), ("m4a", "aac"), ("flac", "flac")])
def test_supported_compressed_formats(tmp_path, suffix, codec):
    source = tmp_path / "source.wav"
    source.write_bytes(wav_bytes())
    encoded = tmp_path / f"encoded.{suffix}"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(source),
                    "-c:a", codec, str(encoded)], check=True)
    with TestClient(create_app(tmp_path / "archive", TOKEN)) as client:
        response = upload(client, subject(client), encoded.read_bytes(), f"lesson.{suffix}")
        assert response.status_code == 201, response.text
        assert response.json()["sample_rate"] == 16000


def test_upgrade_existing_database(tmp_path):
    with sqlite3.connect(tmp_path / "aulalocale.sqlite3") as conn:
        conn.execute("CREATE TABLE subjects(id TEXT PRIMARY KEY,title TEXT,description TEXT,created_at TEXT)")
        conn.execute("INSERT INTO subjects VALUES ('old','Existing','','2026-01-01T00:00:00Z')")
        conn.execute("PRAGMA user_version = 1")
    with TestClient(create_app(tmp_path, TOKEN)) as client:
        assert client.get("/health").status_code == 200
    with sqlite3.connect(tmp_path / "aulalocale.sqlite3") as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT title FROM subjects WHERE id='old'").fetchone()[0] == "Existing"
