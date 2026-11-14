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
