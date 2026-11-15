# Roadmap

1. Fondazione: repository, workflow Git, API materie, database e test.
2. Importazione: validazione audio, hash, asset originali, metadati e lezioni — implementati nel backend; prima interfaccia browser e lettore originale implementati.
3. Audio: worker persistente, miglioramento tradizionale, lettore originale/derivato e prima misura sul campione reale implementati; anteprima su intervallo, qualificazione percettiva e motore IA restano da sviluppare.
4. Trascrizione: modelli locali qualificati, segmenti, timestamp, correzioni e glossario.
5. Dispense: fonti, capitoli incrementali, revisioni, protezione delle modifiche, immagini e schemi.
6. Desktop: interfaccia, gestione modelli, installazione DMG e verifica offline.
7. Server: autenticazione multiutente, isolamento, coda limitata, backup e distribuzione Linux.

Per ogni fase: implementazione su sviluppo, test e dimostrazione, conferma del responsabile, quindi pull request e merge su main. Nessuna scadenza o prestazione promessa prima della prova tecnica.

## Pulizia audio integrata 0.4

39 test superati. Aggiunti test con esecuzione FFmpeg effettiva sui tre preset, conservazione dell'originale, accesso protetto e Range sul derivato, durata del risultato, riuso dei risultati, annullamento in coda e durante l'esecuzione, nuovo tentativo, sorgente mancante, recupero di lavoro interrotto e rifiuto del secondo worker sullo stesso archivio.

Prova locale su Mac M4 24 GB con la registrazione completa di Farmacologia: preset bilanciato, circa 6,43 secondi fra creazione e completamento del lavoro; output 53.900.252 byte. È una singola misura, non un benchmark generalizzabile. SHA-256 dell'originale invariato.

Nel browser: avvio del lavoro con avanzamento, recupero della versione dopo ricaricamento e passaggio da originale a migliorato con posizione 8,435231 secondi mantenuta e pausa preservata. Durata del derivato nel lettore: 4491,56 secondi. Nessun errore del lettore osservato. Queste prove non qualificano la qualità percettiva dei preset o l'efficacia sul rumore.

## Versione 0.5

53 test automatici superati localmente: aggiunti catalogo e integrità dei modelli, ripresa dei download, revisioni della trascrizione e conflitti, proposte con riferimenti, protezione delle modifiche manuali, immagini e mappe dei capitoli, backup/ripristino e accesso monouso del launcher.

Prove reali su Mac M4 24 GB:

- Trascrizione completa della registrazione di 4491,56 secondi con Whisper Turbo Q8: 588,68 secondi fra creazione e completamento del lavoro, 1697 segmenti. Nessun riferimento manuale disponibile per misurare WER/CER.
- Proposta sull'intera trascrizione con Qwen3 4B Q4_K_M: 371,94 secondi, 30 sezioni e 127 riferimenti, lasciata non approvata.
- Nel campione d'aula sono presenti errori importanti del riconoscimento, propagati nella sintesi. Qualità didattica non validata; i collegamenti strutturali non certificano il sostegno semantico delle affermazioni.
- Il confronto iniziale Small/Turbo non è controllato: è cambiata anche la normalizzazione. Non permette di attribuire tutto il miglioramento al modello.
- Nel browser verificati accettazione e modifica di una proposta di prova, stato protetto delle sezioni, consultazione di una revisione storica, navigazione dalle citazioni all'audio, inserimento immagini, mappa dei capitoli ed esportazione ZIP con immagini.
- Pacchetto .app eseguito in un archivio di prova separato, con i pesi già scaricati: avvio, risorse web, runtime inclusi, importazione, FFmpeg, trascrizione Whisper, proposta Qwen e arresto completati. La prova non usa il Python del progetto per eseguire il servizio incluso nel bundle. La firma è ad hoc; nessuna notarizzazione o verifica su un secondo Mac.

Build Docker non eseguito: Docker non è disponibile nell'ambiente corrente. CI GitHub non attiva per il permesso workflow mancante.

## Versione 0.6 — primo denoising IA

58 test superati, comprese due prove effettive con il peso GTCRN locale fornito esplicitamente (senza variabile ambiente queste due prove vengono saltate). Verificati durata PCM invariata, originale invariato, creazione e riuso del derivato, backup con WAV e selezione della sorgente per la trascrizione. I test normali restano privi di download dei pesi.

Prova sulla registrazione completa di Farmacologia: GTCRN bilanciato, 180,70 secondi tra creazione e completamento del lavoro; WAV 16 kHz mono di 4491,56 secondi / 71.864.960 campioni, 143.729.964 byte. SHA-256 dell'originale invariato. È una singola esecuzione su M4 24 GB, non un benchmark del server né una misura della qualità percettiva. Generati estratti privati originali/tradizionali/IA per l'ascolto; nessun WER/CER o giudizio di superiorità dichiarato.

Nuovo pacchetto Mac 0.6 firmato ad hoc: eseguito con il Python incluso, GTCRN reale in processo figlio, trascrizione Whisper dal WAV neurale, proposta Qwen e arresto regolare. I pesi già scaricati sono stati collegati solo all'archivio di prova, non inclusi nel pacchetto. Nessun test su un secondo Mac pulito o server i7.

Interfaccia: versione IA completata riconosciuta dopo riavvio; selezione Migliorato e sorgente migliorata per Whisper disponibili. La trascrizione completa precedente e le dispense non sono state sostituite durante questa verifica.

Vedere [valutazione dei candidati](model-selection.md) per i modelli proposti: ricerca documentale distinta dai motori realmente integrati.

## Versione 0.7 — revisione guidata

Whisper Turbo resta il motore integrato; sorgente iniziale reimpostata all’originale normalizzato per ogni lezione. GTCRN resta il percorso IA del riascolto, con scelta esplicita del derivato per l’ASR. Nessuna promozione dei modelli sperimentali.

Aggiunti segni di revisione per segmento, ricerca nel testo, filtro dei passaggi da rivedere, navigazione al prossimo passaggio, riascolto limitato al segmento e ripetizione. I segni sono dichiarazioni manuali salvate nelle revisioni, non misure dell’accuratezza. Un’ulteriore modifica del testo richiede di rivederlo nuovamente. Le revisioni storiche restano in sola lettura.

L’accettazione delle dispense richiede gli ID di ogni nuova sezione controllata; richieste vuote, parziali o con ID estranei sono rifiutate. Le sezioni modificate manualmente vengono preservate. Nessuna approvazione o modifica automatica delle dispense reali durante i test.

Prova browser su archivio dimostrativo separato con segnale audio sintetico: conferma parziale e completa delle due sezioni, accettazione, salvataggio di un passaggio rivisto e protezione della revisione, ricerca/filtro e avvio del riascolto. Non costituisce una prova di qualità della trascrizione o delle dispense.

68 test superati, incluse versioni dei segni di revisione, invalidazione dopo modifica, ID non validi e rifiuto dell’accettazione parziale delle dispense. Verificato nel browser anche l’arresto del riascolto al termine del passaggio e la rimozione del segno dopo modifica.

Pacchetto Mac 0.7 eseguito nell’archivio di prova separato: avvio, runtime inclusi, GTCRN reale, Whisper dal WAV neurale, proposta Qwen e arresto regolare. Build ad hoc non notarizzata; nessun peso o archivio personale incluso, nessuna prova su un secondo Mac.

Verificata anche la ripetizione del passaggio nel browser. L’anteprima sull’archivio reale è stata riavviata con il backend 0.7; una richiesta di controllo su ID inesistenti conferma la nuova validazione senza coinvolgere proposte reali.

## Versione 0.8 — dispense dinamiche

Prima integrazione incrementale per argomenti, controllo delle revisioni già considerate, ricostruzione delle parti automatiche collegate a fonti corrette, conservazione delle sezioni manuali, confronto prima/dopo e conferma esplicita delle sostituzioni.

Prove con Qwen locale su due lezioni sintetiche: fusione nel capitolo esistente con entrambe le fonti e nota manuale invariata; terza lezione discordante mantenuta separata e segnalata. Verifica browser di confronto, accettazione e segnalazione del contrasto. Dettagli in [dynamic-notes.md](dynamic-notes.md). Nessuna dispensa o trascrizione reale sostituita durante le prove.

75 test automatici superati: pianificazione incrementale, fonti collegate ricostruite dopo una correzione, consolidamento con fonti di entrambe le lezioni, rifiuto della perdita di riferimenti, conservazione delle parti manuali, blocco dell’accettazione senza controllo delle sostituzioni e segnalazioni di contrasto negli export. È coperto anche il caso di metadati precedenti su un capitolo manuale, che non deve riavviare inutilmente la generazione.

Pacchetto Mac 0.8 verificato: avvio del server incluso, risorse web, GTCRN, Whisper, proposta Qwen con la nuova pianificazione e arresto regolare nell’archivio di prova separato. Firma ad hoc verificata, non notarizzata. Nessuna prova su un secondo Mac o server i7.

## Sviluppo 0.9 — audio e finestra Mac

82 test backend superati, incluso il ripristino delle assegnazioni manuali dei parlanti. Test del ricampionamento AudioWorklet a 16/44,1/48 kHz superati. Finestra Mac WebKit verificata visivamente nel pacchetto. Prova del pacchetto senza interfaccia: upload, FFmpeg, GTCRN, Whisper sul WAV migliorato, proposta Qwen e arresto completati. Dettagli e limiti in [audio-desktop.md](audio-desktop.md).

## Multilingual preview 0.10

84 backend tests passed, including validation of note output language and authenticated desktop preference persistence across launcher instances. The JavaScript i18n check covers English/Italian rendering, fallback, placeholder safety, preference storage, preservation of user text and guards against language changes while recording or with unsaved edits.

Browser and packaged Mac checks confirmed English/Italian switching. The Mac preference was saved, the app closed and restarted on a different loopback port, and English was retained. Existing course text remained unchanged. New-note prompts were checked for the requested output language using a controlled LLM adapter; this does not measure English summary quality. Some backend diagnostics, generated map labels and operating-system media controls retain their source/system language.

## Roadmap development 0.11

100 backend tests passed, with explicit local GTCRN weights. Added checks cover interval previews, refusal of preview-as-full-transcription input, accepted-only history, reversible derivative quarantine, symlink refusal, legacy-backup restore, archive locking before migration, PDF page/fingerprint provenance, source-map anchors, human-reference weighted scoring, and conservative quote/quantity validation.

Real UI checks on public/synthetic demo material completed a five-second GTCRN preview, historical read-only selection, PDF figure import and source-map generation. Qwen completed a local four-claim source check and classified the unsupported demo claims as uncertain. That is a bounded functional trial, not a measured entailment benchmark. The packaged PDF subprocess extracted the synthetic figure successfully.

The Linux Docker build and startup/auth/native-runtime smoke check passed on a GitHub-hosted runner. It is not an i7 performance measurement. No valid signing identities were found on the development Mac; no Developer ID signing/notarization or clean-second-Mac qualification is claimed.
