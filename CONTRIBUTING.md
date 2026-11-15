# Contributing to Traccia

Work against `sviluppo`, run `python -m pytest` for backend changes, and keep the documentation consistent with implemented behavior. Promotion of application code to `main` requires explicit approval from the project owner; do not enable auto-merge.

Use synthetic fixtures. Never commit personal recordings, lecture transcripts, models, secrets or compiled runtimes. Do not add cloud inference APIs. Check model and dependency licenses before introducing them.

The code license has not been selected yet. Please agree substantial external contributions with the owner in advance.

## Interface languages

The interface currently supports English and Italian. Italian messages are source keys; `aulalocale/web/locales/en.js` contains English translations. `i18n.js` translates only explicitly marked interface text and calls to `T`. Never translate user-entered subjects, transcripts, filenames, captions or manually edited speaker names.

Tagged template messages preserve numbered placeholders. Keep every placeholder exactly once where it is required. Add a catalog and a supported-language option to introduce another interface language; test reload, dialogs, empty states, errors and screen-reader labels. Language changes must preserve unsaved edits and ongoing recordings.

Transcription language, new note-section language and interface language are independent. Do not silently translate existing notes when the interface changes.
