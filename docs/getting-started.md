# Installation and operation

Technical guide for **Traccia**. [Project introduction](../README.md) · [Italian introduction](../README.it.md)

## Reference platforms

- **Apple Silicon Mac:** development and runtime trials on Apple M4 with 24 GB unified memory. Intel Macs are excluded. Minimum requirements are not certified.
- **Own Linux server:** target Intel i7 with 24 GB RAM. Container builds and performance on that server remain unverified.

Models are loaded sequentially and share one processing queue.

## Run from source

Requires Python 3.11+, Git and a C/C++ toolchain (Xcode Command Line Tools on Mac).

```sh
git clone --branch sviluppo https://github.com/ico88/Traccia.git
cd Traccia
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install cmake==4.4.4
python scripts/setup_runtimes.py
python -m aulalocale
```

Mac opens a dedicated WebKit window, with the backend listening only on a free loopback port. Closing the window stops the service. Use `--browser` for an external browser, `--no-browser` for a headless service, or `--data /path/to/archive` to choose another archive.

Default data paths remain `~/Library/Application Support/AulaLocale` on Mac and `~/.local/share/aulalocale` on Linux. The legacy Python module, environment variables and Mac bundle identifier are retained for compatibility. Existing recordings do not need migration.

Create a subject and open **Local models**. Weights are downloaded only after an explicit request, using pinned revisions and SHA-256 verification. Installation and downloads need internet; inference uses local files, without cloud fallback or a Hugging Face token in the standard workflow.

## Languages

Use **Language / Lingua** to choose English or Italian. The browser/device remembers your selection; the first visit follows the browser language, defaulting to English for other languages. The page reloads after a change. Unsaved transcript/speaker changes require a decision; an active recording must be saved first.

Choose the lecture language independently: Italian, English or automatic recognition. The notes control selects the language of newly generated sections, English or Italian. Existing chapters and manual edits are not automatically translated. Some technical diagnostics and generated map labels retain their source language. Additional UI languages can be added through the catalog system.

## Models

The [catalog](https://github.com/ico88/Traccia/blob/sviluppo/aulalocale/models.py) pins revisions, sizes and hashes. Whisper Turbo handles transcription, Qwen3 4B proposes notes, GTCRN reduces noise, pyannote/3D-Speaker analyzes speakers and VoxLock attempts reference-based voice extraction. Download only what you need.

Native whisper.cpp and llama.cpp runtimes are built by `setup_runtimes.py`. Optional overrides: `AULALOCALE_WHISPER_BIN` and `AULALOCALE_LLAMA_BIN`. Compatibility is checked against the script's pinned revisions, not arbitrary CLI versions.

## Audio and course notes

MP3, WAV, M4A and FLAC imports support up to 512 MiB. Files are fully decoded for validation; duplicate detection uses SHA-256 within a subject. This limit is checked after multipart parsing and is not a preventive upload-traffic limit for a public server.

Originals are preserved. FFmpeg handles conversion, volume and playback MP3s. AI processing also keeps a lossless mono 16 kHz WAV (about 1.92 MB/minute). Enhanced files can be larger than the original and cannot restore missing details. [Audio workflow and limitations](audio-desktop.md)

Transcription can use the normalized original or a selected enhanced version. Enhancement does not automatically become the transcription source and does not guarantee better recognition. Ten-minute recognition blocks have timestamps mapped back to the complete lecture. Manual corrections create protected revisions. “Reviewed by listening” is a student action, not an accuracy certification.

Course notes use transcript snapshots, source references and explicit approval of changed sections. The API acceptance request requires `reviewed_chapter_ids`; replacement approval also requires `reviewed_removed_chapter_ids`. Manual edits stay protected, and stale sources/proposals are flagged or blocked. [Dynamic notes](dynamic-notes.md)

Images are validated and re-encoded to PNG, limited to 20 MiB and 20 megapixels. They are subject materials; automatic placement and slide extraction are not implemented. Chapter maps are visual indexes of up to twelve chapters, not inferred causal diagrams. PDF output uses the print dialog.

## Backup and restore

**Export backup** includes a SQLite snapshot, originals, completed audio derivatives, images and completed speaker analyses/edits, with SHA-256 manifest. It excludes weights, runtimes, credentials and unfinished recording drafts. Finish and import drafts before backup.

```sh
python -m aulalocale.restore /path/to/aulalocale-backup.zip --data /path/to/new-archive
```

Restore checks paths, checksums, SQLite integrity and schema version. It requires a new destination and never overwrites an existing archive. Install models and runtimes separately. Interrupted processing in the same archive restarts the phase; it does not resume at the exact sample/token. In newly restored backups, pending jobs are cancelled and must be started explicitly.

## Development Mac package

After building runtimes on Apple Silicon:

```sh
python -m pip install pyinstaller==6.22.3
python scripts/build_ffmpeg.py --sources ./work/corresponding-sources
python scripts/build_macos.py --output ./dist-macos --dmg
```

The `.app` includes Python, libraries, icon, FFmpeg and native inference runtimes; weights download separately. Builds are ad hoc signed for development, not Developer ID signed or notarized. Stable distribution, automatic updates and validation on a clean second Mac remain pending.

## API / development mode

```sh
export AULALOCALE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export AULALOCALE_DATA_DIR=./data
python -m uvicorn aulalocale.app:app --host 127.0.0.1 --port 8765
```

Open the local URL and enter the configured token. API clients use `Authorization: Bearer <token>`. Browser sessions use HttpOnly / SameSite Strict cookies; tokens are not stored in localStorage or audio URLs. The desktop launcher exchanges a single-use fragment code for a session. Cookie-authenticated mutations require the same origin.

Run one process per archive: **do not use `--workers`**. An archive lock rejects another worker. This preview is for one user per archive; do not expose it as a public multi-user service.

## Own server

Dockerfile, Compose and `.env.example` are provided. Copy `.env.example` to `.env`, set a random token of at least 32 characters, then:

```sh
docker compose up --build -d
```

Compose binds only `127.0.0.1:8765` and persists the archive in a volume. It does not download weights automatically. Container builds, remote HTTPS, reverse-proxy origin handling and separate users still need validation.

## Tests and licensing

```sh
python -m pytest -q
```

Set `AULALOCALE_GTCRN_TEST_MODEL` to an already verified local model for neural tests. Tests do not download weights. [Verification](verification.md) distinguishes controlled adapters from real model runs. GitHub CI is active in `.github/workflows/ci.yml`.

Traccia is GPL-3.0-or-later. Models and dependencies retain their licenses; Mutagen is GPL and redistribution of the actual FFmpeg build needs review. [Contributing](../CONTRIBUTING.md)
