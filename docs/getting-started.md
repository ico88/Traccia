# Guida di installazione e funzionamento

Documentazione tecnica di **Traccia**. Per la presentazione del progetto, torna al [README](../README.md).

## Piattaforme di riferimento

- Mac Apple Silicon: sviluppo e prove su Apple M4 con 24 GB di memoria unificata. Mac Intel esclusi.
- Server Linux: destinazione Intel i7 / 24 GB RAM; benchmark sul server e build Docker ancora da verificare.

I motori vengono caricati in sequenza, con un lavoro alla volta. Queste configurazioni non sono requisiti minimi certificati.

## Avvio da sorgenti

Richiede Python 3.11+, macOS o Linux. Per la compilazione dei runtime servono Git e un compilatore C/C++ (Command Line Tools su Mac; toolchain di sviluppo su Linux).

```sh
git clone --branch sviluppo https://github.com/ico88/aulalocale.git
cd aulalocale
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install cmake==4.4.4
python scripts/setup_runtimes.py
python -m aulalocale
```

Su Mac il launcher apre una finestra dedicata WebKit, senza schede del browser, e crea una sessione locale senza chiedere di copiare un token. Ascolta soltanto sul loopback, su una porta libera. **Chiudi app** arresta il servizio. I dati del launcher sono in `~/Library/Application Support/AulaLocale` su Mac e `~/.local/share/aulalocale` su Linux; `--data /percorso/archivio` permette di scegliere un altro archivio.

Il primo avvio non scarica automaticamente i pesi. Aprire **Modelli locali** e avviare esplicitamente i download. Per aprire esplicitamente il browser usare `python -m aulalocale --browser`. Per avviare soltanto il servizio: `python -m aulalocale --no-browser`.

### Modalità API / sviluppo

```sh
export AULALOCALE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export AULALOCALE_DATA_DIR=./data
python -m uvicorn aulalocale.app:app --host 127.0.0.1 --port 8765
```

Aprire `http://127.0.0.1:8765/` e inserire il token configurato. I client API possono usare `Authorization: Bearer <token>`.

Il cookie del browser è HttpOnly e SameSite Strict. Il token non viene salvato in localStorage e non appare negli URL audio. Il launcher usa un codice di apertura monouso nel frammento URL, rimosso immediatamente dall'interfaccia, per creare la sessione; il codice non è il token API e non viene accettato due volte. Le modifiche con sessione browser richiedono la stessa origine.

Avviare un solo processo per archivio: **non usare `--workers`**. Un lock rifiuta il secondo worker. Questa versione è per un unico utilizzatore per archivio; non esporla direttamente su Internet come servizio multiutente.

## Modelli e funzionamento offline

| Modello | Download | Licenza dichiarata upstream | Impiego |
|---|---:|---|---|
| [Whisper Large v3 Turbo Q8](https://huggingface.co/ggerganov/whisper.cpp) | 874 MB circa | MIT | Trascrizione multilingue, italiano prioritario |
| [GTCRN](https://github.com/Xiaobin-Rong/gtcrn) | 523 KiB circa | MIT | Pulizia voce, distribuzione ONNX ufficiale sherpa-onnx |
| [Analisi parlanti](https://github.com/k2-fsa/sherpa-onnx) | 41 MB circa, due asset | MIT / Apache-2.0 | Segmentazione pyannote e embedding 3D-Speaker |
| [VoxLock](https://huggingface.co/arbazsiddiqui/voxlock) | 73 MB circa compressi, due asset | Apache-2.0 | Estrazione della voce da campione |
| [Qwen3 4B Q4_K_M](https://huggingface.co/Qwen/Qwen3-4B-GGUF) | 2,50 GB circa | Apache-2.0 | Proposte di dispensa |

Revisioni immutabili, dimensioni e SHA-256 sono fissati in `aulalocale/models.py`. I download sono riprendibili e diventano disponibili solo dopo la verifica. Nessuna lezione viene inviata a Hugging Face. I motori usano file locali; llama.cpp viene avviato in modalità offline. Un modello mancante non attiva un servizio esterno di ripiego.

I runtime sono compilati da revisioni verificate di [whisper.cpp](https://github.com/ggml-org/whisper.cpp) e [llama.cpp](https://github.com/ggml-org/llama.cpp). In alternativa impostare `AULALOCALE_WHISPER_BIN` e `AULALOCALE_LLAMA_BIN` a eseguibili compatibili. L'adattatore llama.cpp è verificato rispetto alla revisione fissata dallo script, non a qualunque versione CLI.

## Audio, trascrizioni e dispense

Importazione di MP3, WAV, M4A e FLAC fino a 512 MiB. Contenuto ed estensione devono corrispondere; la decodifica completa viene verificata prima dell'archiviazione. SHA-256 per duplicati nella stessa materia. Il limite viene applicato dopo il parsing multipart: non è ancora una protezione preventiva del traffico di un server pubblico.

La pulizia IA usa GTCRN tramite sherpa-onnx, localmente su CPU: converte a 16 kHz mono, riduce il rumore e miscela il risultato con l’originale secondo l’intensità scelta. FFmpeg resta necessario per conversione, controllo del volume e MP3 a 96 kbit/s per il riascolto. È disponibile anche il percorso tradizionale con filtri passa-alto e riduzione spettrale. Il percorso IA conserva un WAV senza ulteriore compressione per la trascrizione (circa 1,92 MB al minuto), oltre al MP3. Il modello va scaricato esplicitamente da **Modelli locali**. Possono occupare più spazio dell'originale senza recuperare dettagli che non erano presenti. I preset GTCRN sono da qualificare all’ascolto e non separano i parlanti. Per isolare una voce è disponibile il percorso sperimentale VoxLock, descritto in [Audio e app Mac](audio-desktop.md). Nessun percorso garantisce la rimozione del riverbero.

Whisper permette di scegliere l’originale o la versione migliorata, con normalizzazione del volume e blocchi di dieci minuti. Per GTCRN usa il WAV intermedio, evitando la ricompressione MP3; la revisione registra la provenienza. La pulizia non è un requisito per trascrivere e non garantisce meno errori: il confronto controllato è descritto in [docs/asr-comparison.md](asr-comparison.md). Titolo della materia, della lezione e descrizione forniscono un breve contesto al riconoscimento; i segmenti vengono separati ai confini delle parole. I timestamp sono riportati alla lezione completa; i confini dei blocchi possono influire sul riconoscimento. L'avanzamento si aggiorna al termine di ciascun blocco. Il segno “Rivisto all’ascolto” è una dichiarazione dello studente, non una certificazione automatica. Modificare nuovamente il testo rimuove il segno; anche una correzione senza segno resta protetta. Le correzioni salvano una nuova revisione, con controllo contro modifiche concorrenti. Una trascrizione corretta manualmente è protetta dalla ritrascrizione automatica.

Ogni nuova sezione della proposta richiede una conferma esplicita prima dell’accettazione, anche tramite API. L’endpoint `POST /api/v1/subjects/{subject_id}/notes/{revision_id}/accept` richiede il corpo JSON `{"reviewed_chapter_ids":["UUID della sezione"]}` con tutti e soli gli ID delle sezioni nuove o aggiornate. Le sezioni invariate e manuali preservate non richiedono una nuova conferma. Se vengono ricostruite sezioni precedenti, occorre confermarne anche gli ID in `reviewed_removed_chapter_ids`.

Le dispense sono proposte basate sulle revisioni delle trascrizioni, con riferimenti a lezione, revisione, segmento e tempo. Il modello sintetizza le fonti nuove/corrette e propone di integrare i contenuti nei capitoli automatici pertinenti. La vista delle modifiche distingue aggiunte, aggiornamenti, parti invariate e correzioni protette; i possibili contrasti rimangono separati e segnalati. Organizzazione e deduplicazione richiedono ancora qualificazione su corsi reali. Metodo, limiti e prove in [docs/dynamic-notes.md](dynamic-notes.md). Le sezioni modificate manualmente vengono preservate. Fonti cambiate e proposte basate su versioni superate sono segnalate e, quando necessario, ne viene impedita l'accettazione. Le revisioni precedenti restano nel database; la cronologia delle trascrizioni è consultabile dall’interfaccia in sola lettura.

Immagini fino a 20 MiB e 20 megapixel vengono validate e ricodificate in PNG. Per ora sono materiali della materia, non figure collocate automaticamente in punti specifici dei capitoli. È possibile generare localmente una mappa dei capitoli dalla dispensa accettata: è un indice visivo dei primi 12 capitoli, non una mappa di relazioni causali. Il PDF usa la funzione di stampa del browser, non un generatore PDF lato server.

Il confronto sperimentale con **Fluid Speech Pro MLX**, separato dall’app, è documentato in [docs/fluid-experiment.md](fluid-experiment.md). È stato eseguito su M4; non è ancora una scelta disponibile nel pacchetto Mac.

È disponibile anche una [prova separata di MOSS-Transcribe-Diarize](moss-experiment.md), con timestamp e parlanti: non è incluso nel pacchetto Mac.

Provati separatamente anche [Qwen3-ASR 1.7B MLX e Whisper Large v3 completo](qwen-large-experiment.md): entrambi eseguiti sul M4, ancora non inclusi nel selettore dell’app o nel DMG.

## Backup

**Esporta backup** crea uno ZIP con uno snapshot SQLite, audio originali, versioni completate, ruoli dei parlanti e immagini, con manifest SHA-256. Non include modelli, runtime o credenziali. Il ripristino non sovrascrive archivi esistenti:

```sh
python -m aulalocale.restore /percorso/aulalocale-backup.zip --data /percorso/nuovo-archivio
```

Il ripristino verifica percorsi, checksum, integrità e versione del database. Modelli e runtime devono essere installati separatamente. Un lavoro interrotto riparte dall'inizio della fase al successivo avvio; non riprende dal campione o token esatto.

## Pacchetto Mac di sviluppo

Su Apple Silicon, dopo aver compilato i runtime:

```sh
python -m pip install pyinstaller==6.22.3
python scripts/build_macos.py --output ./dist-macos --dmg
```

Il pacchetto include Python, dipendenze e runtime nativi, mentre i pesi vengono scaricati successivamente dall'app. Su Mac l’interfaccia si apre in una finestra WebKit tramite pywebview; il servizio locale rimane su loopback. La modalità browser resta disponibile esplicitamente per sviluppo e accesso web. Il build è di sviluppo: firma Developer ID, notarizzazione, aggiornamenti automatici e verifica su un secondo Mac pulito restano da completare.

## Server proprio

Sono inclusi `Dockerfile`, `compose.yaml` e `.env.example`. Copiare `.env.example` in `.env`, impostare un token casuale di almeno 32 caratteri e avviare:

```sh
docker compose up --build -d
```

Il Compose pubblica soltanto `127.0.0.1:8765`, conserva l'archivio in un volume e non scarica automaticamente i modelli. La configurazione è predisposta ma il build Docker non è stato eseguito nell'ambiente di sviluppo corrente. Accesso remoto con HTTPS, gestione delle origini dietro proxy e utenti separati richiedono una successiva validazione.

## Sviluppo e verifiche

```sh
python -m pytest -q
```

Per includere le due prove neurali effettive, impostare `AULALOCALE_GTCRN_TEST_MODEL` al percorso del modello locale verificato. Nessun peso viene scaricato dai test.

Test con segnali sintetici, nessuna registrazione personale nel repository. Sono coperti autenticazione, archivio, Range audio, filtri effettivi FFmpeg, annullamento e recupero, revisioni, fonti, proposte, download e checksum, immagini, backup e ripristino. I test dell'orchestrazione delle dispense usano un adattatore controllato: sono distinti dalle prove reali dei modelli. Dettagli in [docs/verification.md](verification.md).

La CI GitHub non è ancora attiva: il token utilizzato per creare il repository non ha lo scope `workflow`. Il modello di workflow è conservato in `docs/ci-workflow.yml`; dopo l'attivazione, il controllo `backend-tests` andrà reso obbligatorio su `main`.

## Branch

- **`sviluppo`**: codice e integrazione quotidiana.
- **`main`**: base approvata, attualmente documentazione iniziale.
- Promozioni tramite pull request e solo dopo conferma esplicita del responsabile. Nessun auto-merge.

Leggere [CONTRIBUTING.md](../CONTRIBUTING.md), [architettura](architecture.md) e [roadmap](roadmap.md). Non committare audio, trascrizioni reali, dati personali, chiavi, modelli o runtime compilati.

## Licenze e riferimenti

La licenza del codice del progetto deve ancora essere scelta dal titolare: repository pubblico non equivale a licenza open source. Le dipendenze mantengono le proprie condizioni; in particolare Mutagen è GPL, e FFmpeg richiede la verifica della build effettivamente distribuita. La compatibilità delle licenze va chiusa prima di distribuire una release del prodotto.

[VoiceStudio](https://github.com/debpalash/voicestudio) è un riferimento per l'esperienza di installazione e gestione modelli. Non è stato copiato il suo codice e Traccia non è affiliato al progetto.
