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
