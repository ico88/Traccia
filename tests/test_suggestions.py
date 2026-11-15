import io
import wave

from fastapi.testclient import TestClient
from mutagen.wave import WAVE
from mutagen.id3 import TIT2, TPE1, TDRC
import pytest
from aulalocale.app import create_app
from aulalocale.suggestions import filename_suggestions

TOKEN = 'metadata-preview-token-' * 3
AUTH = {'Authorization': f'Bearer {TOKEN}'}


def test_filename_does_not_invent_year():
    result = filename_suggestions('[Farmacologia] 10-31 Lezione_ Farmacologia generale.mp3')
    assert result['title'] == 'Farmacologia generale'
    assert result['lecture_date'] is None
    assert result['teacher'] == ''
    assert result['notes']


def test_filename_iso_date():
    result = filename_suggestions('[Materia] 2026-10-31 Lezione_ Recettori.mp3')
    assert result['lecture_date'] == '2026-10-31'
    assert result['title'] == 'Recettori'
    assert filename_suggestions('2026-02-30 Lezione.mp3')['lecture_date'] is None


def audio_with_tags(path):
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(b'\0\0' * 1600)
    tagged = WAVE(path); tagged.add_tags()
    tagged.tags.add(TIT2(encoding=3,text='Titolo dai metadati'))
    tagged.tags.add(TPE1(encoding=3,text='Nome artista'))
    tagged.tags.add(TDRC(encoding=3,text='2026-10-31'))
    tagged.save()
    return path.read_bytes()


def test_preview_tags_no_archive_writes(tmp_path):
    content = audio_with_tags(tmp_path/'tagged.wav')
    archive = tmp_path/'archive'
    with TestClient(create_app(archive,TOKEN)) as client:
        result = client.post('/api/v1/audio/preview',headers=AUTH,
                             files={'file':('2026-10-30 source.wav',content)} )
        assert result.status_code == 200
        data = result.json()
        assert data['title'] == 'Titolo dai metadati'
        assert data['teacher'] == 'Nome artista'
        assert data['lecture_date'] == '2026-10-31'
        assert data['sources']['teacher'] == 'embedded_artist'
        assert len(data['notes']) == 2
        assert client.get('/api/v1/subjects',headers=AUTH).json() == []
        assert client.post('/api/v1/audio/preview',files={'file':('x.wav',content)}).status_code == 401
    assert not (archive/'originals').exists()
    assert not (archive/'staging').exists()


@pytest.mark.parametrize('name,body', [('fake.mp3',b'not audio'),('empty.wav',b''),('bad.exe',b'no')])
def test_preview_invalid(tmp_path,name,body):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        assert client.post('/api/v1/audio/preview',headers=AUTH,files={'file':(name,body)}).status_code == 422
