"""Persistent desktop preferences, independent of random loopback ports."""
import json


class DesktopPreferences:
    def __init__(self,root):self._path=root/'desktop-preferences.json'
    def language(self):
        try:
            language=json.loads(self._path.read_text()).get('language')
            return language if language in ('en','it') else ''
        except (OSError,ValueError,AttributeError):return ''
    def set_language(self,language):
        if language not in ('en','it'):raise ValueError('Unsupported interface language')
        partial=self._path.with_suffix('.part');partial.write_text(json.dumps({'language':language}));partial.replace(self._path)
        return True

