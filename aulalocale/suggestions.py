"""Conservative suggestions from filenames and embedded tags; no speech inference."""
from datetime import date
from pathlib import Path
import re

import mutagen
from fastapi import HTTPException


def filename_suggestions(filename: str):
    name = filename.replace('\\', '/').split('/')[-1]
    stem = Path(name).stem
    title = re.sub(r'^\s*\[[^\]]+\]\s*', '', stem)
    result = {"title": "", "teacher": "", "lecture_date": None,
              "sources": {}, "notes": []}
    full = re.search(r'(?<!\d)(\d{4})[-_.](\d{2})[-_.](\d{2})(?!\d)', title)
    if full:
        try:
            result['lecture_date'] = date(*map(int, full.groups())).isoformat()
            result['sources']['lecture_date'] = 'filename'
            title = title[:full.start()] + title[full.end():]
        except ValueError:
            result['notes'].append('La data nel nome non è valida: controllala manualmente.')
    else:
        partial = re.search(r'(?<!\d)(\d{1,2})[-_.](\d{2})(?!\d)', title)
        if partial:
            result['notes'].append('Il nome contiene una possibile data senza anno. La data della lezione resta da confermare.')
            title = title[:partial.start()] + title[partial.end():]
    title = re.sub(r'^\s*Lezione\s*[_:–-]\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title.replace('_', ' ')).strip(' -–:')
    result['title'] = (title or stem)[:200]
    result['sources']['title'] = 'filename'
    return result


def audio_suggestions(file, filename, formats):
    suffix = Path(filename).suffix.lower()
    if suffix not in formats:
        raise HTTPException(422, 'Unsupported audio extension')
    result = filename_suggestions(filename)
    try:
        file.seek(0)
        audio = mutagen.File(file)
        if not isinstance(audio, formats[suffix][0]):
            raise ValueError('Content does not match extension')
        tags = audio.tags or {}
        def text(*keys):
            for key in keys:
                value = tags.get(key)
                if value is not None:
                    if isinstance(value, (list, tuple)):
                        value = value[0] if value else ''
                    value = str(value).strip()
                    if value:
                        return value
            return ''
        title = text('title', 'TIT2', '\xa9nam')
        artist = text('artist', 'TPE1', '\xa9ART')
        tagged_date = text('date', 'TDRC', '\xa9day')
        if title:
            result['title'] = title[:200]
            result['sources']['title'] = 'embedded_title'
        if artist:
            result['teacher'] = artist[:200]
            result['sources']['teacher'] = 'embedded_artist'
            result['notes'].append('Il docente è proposto dal tag artista: verifica che sia la persona corretta.')
        if tagged_date:
            try:
                parsed = date.fromisoformat(tagged_date[:10]).isoformat()
                if result['lecture_date'] and result['lecture_date'] != parsed:
                    result['notes'].append('La data nei tag differisce dal nome: è stata proposta quella dei tag, da verificare.')
                result['lecture_date'] = parsed
                result['sources']['lecture_date'] = 'embedded_date'
            except ValueError:
                result['notes'].append('La data nei tag è incompleta o non valida e non è stata usata.')
        return result
    except (mutagen.MutagenError, ValueError, AttributeError, TypeError) as error:
        raise HTTPException(422, 'Cannot read metadata from this audio file') from error
    finally:
        file.seek(0)
