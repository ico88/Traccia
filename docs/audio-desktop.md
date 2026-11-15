# Audio e finestra Mac — sviluppo 0.9

## App desktop

Su Apple Silicon l’avvio standard usa pywebview / WKWebView in una finestra dedicata. Non apre il browser esterno. Il backend rimane un servizio HTTP di loopback, accessibile solo sul dispositivo, con sessione inizializzata da un codice monouso. Chiudere la finestra arresta il servizio. `--browser` apre esplicitamente il browser; `--no-browser` avvia il servizio senza interfaccia. Il server web resta una modalità separata, utile per l’i7 Linux.

L’app di sviluppo include la descrizione macOS per l’accesso al microfono. La prima registrazione richiede il permesso del sistema; non viene attivato automaticamente all’avvio. La distribuzione non è ancora notarizzata.

## Registrazione

Dalla materia selezionare **Registra**, inserire i metadati e premere **Inizia**. Sono disponibili scelta del dispositivo, livello del segnale, pausa e ripresa. Acquisizione mono PCM 16 kHz, con conversione dal sample rate del dispositivo; non registra l’audio di sistema. I blocchi vengono salvati progressivamente sul dispositivo/server di destinazione. Dopo un’interruzione la bozza già ricevuta può essere recuperata dal dialogo; un blocco ancora in viaggio può andare perso.

La chiusura importa un WAV verificato come originale, conservato senza modifiche. Si possono poi avviare pulizia e trascrizione. Non è trascrizione simultanea alla registrazione. Limite 512 MiB, inclusa intestazione WAV. Una bozza non vuota non viene cancellata dal pulsante di rimozione. **Le bozze in corso non fanno parte del backup ZIP**: terminarle/importarle prima del backup. Le lezioni completate sono incluse normalmente.

## Pulizia e volume

GTCRN riduce il rumore, con tre intensità e confronto con l’originale. FFmpeg resta necessario per decodifica, normalizzazione, guadagno e codifica. Il selettore di volume aggiunge 0/3/6/9/12 dB con limitatore; il limite evita picchi oltre il massimo, non garantisce un aumento percepito uniforme. Le diverse ricette producono derivati separati. Per trascrivere resta consigliato confrontare l’originale normalizzato prima di scegliere il derivato.

## Parlanti

Scaricare **Analisi parlanti** in Modelli locali: segmentazione pyannote 3.0 int8 e embedding 3D-Speaker ERes2Net. Entrambi girano localmente su CPU via sherpa-onnx. Si può proporre il numero di voci o usare il conteggio automatico. L’analisi suggerisce intervalli e sigle S01, S02…; non conosce l’identità del docente. Rinominare i ruoli e correggere gli intervalli. Le modifiche sono versionate e protette dalla rianalisi automatica; sono incluse nel backup.

I tag sulle trascrizioni derivano dalla sovrapposizione temporale con gli intervalli: non sono una trascrizione separata per ogni persona. Sovrapposizioni ambigue vengono segnalate. Conteggio automatico e qualità su aule reali restano da qualificare: nel campione pubblico a quattro voci il conteggio automatico ha sovrastimato i gruppi.

## Isolare il docente

Scaricare **Isolamento docente**: VoxLock, due asset ONNX. Selezionare 3–30 secondi dell’originale in cui parla soltanto il docente, oppure usare un intervallo proposto dall’analisi parlanti. Avviare il metodo sperimentale **Isola docente**. Il riferimento e i checksum dei modelli sono registrati nella ricetta. Il risultato è un WAV per eventuale trascrizione e un MP3 per l’ascolto; l’originale non viene modificato.

VoxLock usa un campione vocale per estrarre la voce desiderata; non garantisce separazione perfetta, recupero delle parole coperte o rimozione del riverbero. Può attenuare e alterare il parlato. Sul breve campione pubblico la prima prova CPU ha richiesto circa 37 secondi per 14 secondi di audio: non è un benchmark dell’intera lezione. Nessun audio o campione vocale viene inviato a servizi di inferenza esterni.

## Verifica 0.9

- 82 test backend: autenticazione, sequenze dei blocchi, ripartenza delle bozze, importazione WAV, riferimenti vocali invalidi, protezione delle correzioni, backup/ripristino dei ruoli, download con archivio e checksum, oltre alle funzionalità precedenti.
- AudioWorklet verificato con segnale sintetico a 16 / 44,1 / 48 kHz: durata e frequenza conservate entro un campione su 5,3 secondi.
- Modelli reali: diarizzazione, salvataggio dei ruoli e isolamento VoxLock con guadagno +3 dB completati tramite app su un campione pubblico di 17,01 secondi. Conservazione del numero di campioni verificata separatamente sul campione da 14,01 secondi.
- Pacchetto Mac: runtime GTCRN, Whisper e Qwen completati; i due nuovi worker inclusi hanno completato diarizzazione (4 gruppi richiesti, 10 intervalli) e VoxLock (224160 campioni conservati). Finestra dedicata verificata visivamente.
- Accesso fisico al microfono, permessi e qualità percettiva su lezioni reali richiedono ancora prova manuale. Non è stato attivato il microfono dell’utente durante questi test.
