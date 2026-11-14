# Architettura

## Implementato

FastAPI espone health e API versionate per creare, elencare e leggere materie. SQLite conserva i dati fra riavvii. Un token bearer configurato protegge tutte le API applicative. La configurazione senza token fallisce all'avvio. Nessuna CORS permissiva e documentazione pubblica disabilitata.

Questa base è per uso locale e singolo utente. Il token protegge le richieste, ma non sostituisce TLS, gestione delle sessioni e isolamento degli utenti della futura versione server. L'avvio documentato usa esclusivamente il loopback.

## Previsto

React/TypeScript con Electron sul Mac e browser sul server. Worker separati per conversione, audio, trascrizione e dispense; coda persistente con dipendenze e recupero dall'ultima fase completata. Asset originali immutabili; derivati e revisioni espliciti.

Blocchi della dispensa collegati a revisione della trascrizione e segmenti temporali. Aggiornamenti proposti prima dell'applicazione, con modifiche manuali protette. Correzioni e rimozioni delle fonti invalidano le dipendenze senza cancellazioni automatiche.

Profilo Mac M4 24 GB e server i7 24 GB. Una sola elaborazione IA alla volta all'inizio; caricamento sequenziale dei modelli. Modelli e accelerazione da scegliere tramite misure. Nessun benchmark ancora completato per i motori IA.
