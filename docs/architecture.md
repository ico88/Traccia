# Architettura 0.8

## Applicazione

FastAPI e SQLite, un singolo utilizzatore per archivio. Interfaccia HTML/CSS/JavaScript locale, senza CDN. Il contenitore React/Electron rimane una possibile evoluzione; il launcher Mac corrente include il runtime Python e apre il browser di sistema.

`app.py` configura autenticazione, risorse web e lifecycle. `lessons.py` gestisce importazione e originali; `suggestions.py` legge nome e tag. `enhancement.py` orchestra il worker seriale e i processi FFmpeg. `study.py` implementa trascrizioni, revisioni e proposte di dispensa. `models.py` contiene catalogo fissato, download e verifica. `materials.py` gestisce immagini e backup. `restore.py` ripristina esclusivamente in una nuova cartella.

## Persistenza

Schema 5, migrazioni additive. Materie, lezioni, lavori audio, lavori di studio, trascrizioni immutabili con revisioni, dispense accettate/proposte e immagini. Le API di modifica usano la revisione di base per evitare di sovrascrivere aggiornamenti concorrenti.

Originali con nomi interni generati; immagini ricodificate in PNG. File temporanei dei processi separati dai risultati pubblicati. Filesystem e SQLite non sono una singola transazione: un arresto improvviso dell'importazione può lasciare orfani da riconciliare. Il backup usa snapshot SQLite, file immutabili e manifest SHA-256.

## Coda e motori

Un thread orchestratore, con lock esclusivo per archivio, avvia un solo processo di elaborazione alla volta. Prima cerca lavori audio, poi lavori di studio; una politica di priorità equa è ancora da implementare. L'annullamento ferma il processo nativo. Dopo il riavvio i lavori interrotti ripartono dall'inizio della fase.

Whisper riceve WAV mono 16 kHz normalizzati, in blocchi di dieci minuti. Risultati con segmenti temporali e revisione del modello. Il profilo corrente usa Large v3 Turbo Q8. Le revisioni manuali restano protette; la ritrascrizione di una versione automatica richiede l'identificativo esatto della revisione corrente e non elimina quella precedente.

Qwen3 4B Q4_K_M tramite llama.cpp offline genera JSON vincolato a schema. Gli id delle citazioni devono appartenere agli input; il controllo è strutturale e non dimostra il sostegno semantico di ogni affermazione. Una proposta non sostituisce automaticamente la dispensa. I capitoli manuali vengono preservati; una prima classificazione/consolidamento tematico è implementata in `note_consolidation.py` e rimane da qualificare; vedere [dispense dinamiche](dynamic-notes.md).

Download dei pesi separato dall'inferenza: un download alla volta, revisioni immutabili, dimensione e SHA-256 verificati. Nessun upload di contenuti di studio o inferenza remota. I runtime sono compilati separatamente da sorgenti upstream verificati; nel pacchetto Mac vengono inclusi, insieme a Python e FFmpeg.

## Accesso

API bearer o cookie HttpOnly/SameSite Strict. Verifica di origine per richieste browser con cookie; nessuna CORS permissiva. Cookie con nome derivato dalla configurazione per evitare collisioni fra istanze locali. Interfaccia con CSP restrittiva, testo utente reso tramite textContent e immagini eseguibili non accettate.

Il launcher desktop genera token e codice di apertura monouso, ascolta solo sul loopback e passa al browser il codice nel frammento URL. L'interfaccia lo rimuove prima di creare la sessione. Il codice non viene scritto nei log HTTP e non è riutilizzabile. Chiudi app arresta il servizio dopo la risposta.

La modalità server è ancora singolo utente. Il Compose si lega al loopback; reverse proxy, HTTPS e isolamento fra utenti devono essere progettati e verificati prima di una pubblicazione remota.

## Pulizia IA

GTCRN esegue il denoising in un processo figlio locale sherpa-onnx su CPU. La coda seriale esistente gestisce avanzamento, annullamento e recupero. FFmpeg decodifica il file in PCM 16 kHz mono e prepara il derivato MP3 per il lettore; un WAV neurale mantiene la sorgente senza ricompressione per Whisper. Gli originali restano immutabili. La ricetta include hash dei pesi, intensità e postfiltri; il riuso distingue modello e preset. Il backup include entrambi i derivati completati. Lo schema resta alla versione 5: usare questa versione o successive per archivi con lavori GTCRN, evitando il downgrade dell’app.
