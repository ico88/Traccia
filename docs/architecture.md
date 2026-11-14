# Architettura

## Implementato

FastAPI espone health e API versionate per creare, elencare e leggere materie. SQLite conserva i dati fra riavvii. Un token bearer configurato protegge tutte le API applicative. La configurazione senza token fallisce all'avvio. Nessuna CORS permissiva e documentazione pubblica disabilitata. Interfaccia locale statica con CSP restrittiva. Accesso browser mediante cookie HttpOnly/SameSite Strict derivato dal token server, mai inserito negli URL audio. Richieste con cookie soggette a controllo di origine; client bearer ancora supportati. Logout elimina il cookie locale; il token server deve cambiare per revocare tutte le sessioni. Non è ancora un servizio di autenticazione multiutente.

Le lezioni hanno una chiave esterna verso la materia e un vincolo univoco su materia/hash. Gli originali sono in `data/originals`, gli upload provvisori in `data/staging`. Il nome fornito dal client viene conservato solo come metadato; il percorso archiviato è generato dal server. La validazione legge metadati e decodifica il contenuto prima di creare la lezione. Gli errori gestiti eliminano i file temporanei e le copie non registrate. Gli arresti improvvisi richiederanno una futura riconciliazione degli orfani.

Migrazione additiva alla versione schema 2, con conservazione delle materie. La versione API corrente è 0.4.0.

Questa base è per uso locale e singolo utente. Il token protegge le richieste, ma non sostituisce TLS, gestione delle sessioni e isolamento degli utenti della futura versione server. L'avvio documentato usa esclusivamente il loopback.

## Previsto

React/TypeScript con Electron sul Mac e browser sul server. Worker separati per conversione, audio, trascrizione e dispense; coda persistente con dipendenze e recupero dall'ultima fase completata. Asset originali immutabili; derivati e revisioni espliciti.

Blocchi della dispensa collegati a revisione della trascrizione e segmenti temporali. Aggiornamenti proposti prima dell'applicazione, con modifiche manuali protette. Correzioni e rimozioni delle fonti invalidano le dipendenze senza cancellazioni automatiche.

Profilo Mac M4 24 GB e server i7 24 GB. Una sola elaborazione IA alla volta all'inizio; caricamento sequenziale dei modelli. Modelli e accelerazione da scegliere tramite misure. Nessun benchmark ancora completato per i motori IA.

## Elaborazione audio implementata

Schema 3: `audio_jobs` collega una lezione al preset, stato, avanzamento, errore, filtri e versione del motore. Un indice univoco parziale impedisce più lavori attivi per lezione e preset. Il thread di orchestrazione esegue un processo FFmpeg alla volta. Un lock `flock` mantiene un solo worker per archivio su macOS/Linux.

Output temporaneo in `enhanced/{job-id}.part.mp3`, rinomina atomica al termine e stato completato solo dopo il risultato. I lavori interrotti vengono rimessi in coda al successivo avvio e il relativo output parziale viene sostituito. Gli output non completati vengono rimossi in caso di errori gestiti e annullamento. Originali in sola lettura per il worker.

La pubblicazione filesystem e il commit SQLite non costituiscono una transazione unica. In caso di crash fra le due operazioni, il recupero del lavoro non completato ripete la fase. Non sono ancora implementati checksum dei derivati né riconciliazione dei risultati completati rimossi esternamente.
