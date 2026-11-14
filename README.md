# AulaLocale

Da una lezione registrata a materiale di studio organizzato per materia, sul proprio computer.

**Progetto in sviluppo iniziale. Non è ancora disponibile un'app installabile.** Il nome è provvisorio.

AulaLocale è pensato per studenti universitari: conservare e riascoltare le lezioni con audio migliorato, correggere le trascrizioni e costruire dispense che crescono con il corso. L'elaborazione IA sarà locale, senza API di inferenza esterne o abbonamenti obbligatori.

Il codice applicativo è sul branch [`sviluppo`](https://github.com/ico88/aulalocale/tree/sviluppo); `main` conserva la documentazione iniziale fino alla prima approvazione.

## Stato attuale

Questa prima base implementa un'API locale con archivio SQLite, creazione e consultazione delle materie, importazione e consultazione delle lezioni, lettura dei metadati audio, conservazione e riproduzione degli originali, autenticazione tramite token locale e test automatici. Include una prima interfaccia browser locale. Implementa anche riduzione del rumore e normalizzazione tramite filtri tradizionali. Non implementa ancora trascrizione, pulizia tramite modelli IA o dispense.

| Funzione | Stato |
|---|---|
| Archivio persistente delle materie | API e interfaccia locale |
| Importazione lezioni, metadati e ascolto dell’audio originale | API e interfaccia locale |
| Miglioramento audio con filtri tradizionali e confronto allo stesso punto | Implementato |
| Pulizia audio tramite modelli IA | Da qualificare |
| Trascrizione italiana locale e revisione | Pianificato |
| Dispense incrementali con fonti e versioni | Pianificato |
| Immagini, allegati e schemi didattici | Pianificato |
| App macOS tramite DMG | Pianificato |
| Installazione web su server proprio | Pianificato |

## Piattaforme obiettivo

- **Mac Apple Silicon:** macchina di riferimento Apple M4, 24 GB di memoria unificata. Mac Intel esclusi.
- **Server:** Intel i7, 24 GB RAM; Linux come destinazione proposta. Profilo CPU con un lavoro IA alla volta, prestazioni da misurare sulla CPU specifica.

Questi sono ambienti di riferimento, non requisiti minimi certificati. I motori potranno differire fra Mac e server mantenendo gli stessi formati applicativi.

## Avvio per sviluppatori

Python 3.11 o successivo. Dalla radice del repository, su macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export AULALOCALE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn aulalocale.app:app --host 127.0.0.1 --port 8765
```

L'API è disponibile su `http://127.0.0.1:8765`. Le risposte applicative richiedono `Authorization: Bearer <token>`. Il database viene creato in `data/`; il percorso è configurabile con `AULALOCALE_DATA_DIR`.

In un altro terminale, usando lo stesso token:

```sh
curl -H "Authorization: Bearer $AULALOCALE_TOKEN" http://127.0.0.1:8765/api/v1/subjects
curl -X POST http://127.0.0.1:8765/api/v1/subjects   -H "Authorization: Bearer $AULALOCALE_TOKEN"   -H 'Content-Type: application/json'   -d '{"title":"Farmacologia","description":"Corso universitario"}'
```

Il token deve essere esportato anche nel secondo terminale. `GET /health` è pubblico e riporta soltanto lo stato del servizio. Aprire `http://127.0.0.1:8765/` nel browser e inserire il token configurato per usare l’interfaccia. Il token non viene salvato in localStorage: l’accesso crea un cookie di sessione HttpOnly, SameSite Strict, valido nel browser fino a 8 ore. Il pulsante Esci elimina il cookie dal browser; cambiare il token del server invalida tutte le sessioni precedenti. La documentazione interattiva API è disattivata. Non esporre questa versione su Internet: il sistema multiutente e l'installazione server non sono ancora implementati.

```sh
python -m pytest
```

## Architettura prevista

Interfaccia React/TypeScript condivisa fra contenitore desktop Electron e browser; backend FastAPI, SQLite e file locali; worker separati per le elaborazioni lunghe. La prima implementazione copre il backend delle materie e delle lezioni; una prima interfaccia leggera è servita direttamente da FastAPI; React/Electron rimangono lo stack previsto per l’app desktop.

Candidati da qualificare: whisper.cpp per trascrivere, DeepFilterNet per ridurre il rumore, llama.cpp e un modello multilingue quantizzato per generare dispense. Le versioni, i modelli e le licenze saranno selezionati tramite benchmark, senza promettere qualità o tempi prima delle misure.

## Dati e modelli

Audio originali conservati e derivati separati. Le future dispense avranno riferimenti alla lezione e al minuto sorgente, cronologia e protezione delle correzioni manuali. Il miglioramento audio è disponibile per il riascolto.

Modelli gratuiti scaricabili, preferibilmente senza account o token Hugging Face. Dopo il download, obiettivo di funzionamento offline; nessun ripiego automatico verso inferenza cloud. Gratuità dei modelli non significa hardware o hosting gratuiti. Ogni licenza sarà verificata separatamente, inclusa la ridistribuzione.

Non committare registrazioni, trascrizioni reali, dati personali, credenziali o pesi dei modelli. I campioni di sviluppo restano locali e non sono inclusi nel repository pubblico.

## Branch e contributi

- `main`: base approvata; promozioni soltanto dopo conferma del responsabile del progetto.
- `sviluppo`: ramo di lavoro e integrazione.
- Passaggio tramite pull request `sviluppo` → `main`, con test e conferma esplicita prima del merge. Nessun auto-merge.

Il primo commit su `main` contiene soltanto la costituzione del repository; il codice applicativo nasce su `sviluppo`.

Consultare [CONTRIBUTING.md](CONTRIBUTING.md), [architettura](docs/architecture.md) e [roadmap](docs/roadmap.md).

## Licenza e riferimenti

La licenza del codice deve ancora essere scelta dal titolare. Repository pubblico non equivale a licenza open source; nessuna licenza di riuso viene concessa implicitamente. Le dipendenze mantengono le proprie licenze.

[VoiceStudio](https://github.com/debpalash/voicestudio) è un riferimento per l'esperienza di installazione e gestione modelli. Non è stato copiato codice da VoiceStudio e questo progetto non è affiliato al suo autore.

## Attivazione della CI

I test sono eseguibili localmente. Il modello di workflow è in `docs/ci-workflow.yml`: deve essere spostato in `.github/workflows/ci.yml` quando la credenziale GitHub dispone del permesso `workflow`. La CI GitHub non è ancora attiva. Dopo la prima esecuzione, rendere obbligatorio il controllo `backend-tests` nella protezione di `main`.

## Importare una lezione

Sono accettati MP3, WAV, M4A e FLAC, fino a 512 MiB per file. L'importazione legge il contenuto, verifica che corrisponda all'estensione e prova a decodificare tutta la traccia audio con FFmpeg locale. Il pacchetto `imageio-ffmpeg` fornisce il binario: non serve un'installazione separata nel percorso standard.

Sostituire `SUBJECT_ID` con l'identificativo restituito dalla creazione della materia:

```sh
curl -X POST http://127.0.0.1:8765/api/v1/subjects/SUBJECT_ID/lessons \
  -H "Authorization: Bearer $AULALOCALE_TOKEN" \
  -F 'title=Introduzione alla materia' \
  -F 'teacher=Docente' \
  -F 'lecture_date=2026-10-31' \
  -F 'file=@/percorso/lezione.mp3'
```

Titolo obbligatorio; docente e data facoltativi. Il server restituisce identificativo, hash SHA-256, dimensione, durata stimata dai metadati, frequenza di campionamento e numero di canali. Non restituisce percorsi locali. La copia archiviata mantiene esattamente i byte dell'originale e usa un nome interno generato dall'app.

| Metodo | Endpoint | Risultato |
|---|---|---|
| POST | `/api/v1/subjects/{id}/lessons` | Importazione multipart |
| GET | `/api/v1/subjects/{id}/lessons?limit=50&offset=0` | Lezioni della materia |
| GET | `/api/v1/lessons/{id}` | Metadati della lezione |
| GET | `/api/v1/lessons/{id}/audio` | Audio originale, con richieste HTTP Range |

Tutti richiedono il token bearer, incluso l'audio; il futuro lettore dovrà gestire questa autenticazione. I duplicati identici nella stessa materia restituiscono HTTP 409 con il riferimento alla lezione esistente. Lo stesso audio può essere associato a materie diverse, per ora con copie distinte.

La validazione è sincrona con timeout di 180 secondi: la coda persistente arriverà nella fase successiva. Gli import falliti vengono ripuliti; un arresto improvviso del processo fra filesystem e commit SQLite può lasciare file orfani, la cui riconciliazione non è ancora implementata. Il limite applicativo viene verificato dopo il parsing multipart e durante la copia: non è ancora un limite preventivo sul traffico HTTP; per questo la versione rimane esclusivamente locale.

L'aggiornamento del database dalla versione 1 alla 2 conserva le materie esistenti. Non sono supportati downgrade del database.

## Dipendenze audio

Mutagen è utilizzato per i metadati (licenza GPL, vedere il pacchetto upstream). `imageio-ffmpeg` distribuisce un binario FFmpeg con condizioni proprie della build. Queste dipendenze richiedono una verifica di compatibilità prima della scelta della licenza del prodotto e della distribuzione di installer. Nessun codice VoiceStudio è incluso.

## Interfaccia locale (anteprima 0.3)

La pagina iniziale permette di accedere, creare e scegliere materie, caricare registrazioni con titolo, docente e data, consultare i metadati e ascoltare l'originale. Il lettore offre i controlli nativi del browser e velocità da 0,75× a 2×. Le materie e le lezioni vengono caricate mediante paginazione; testo inserito dagli utenti viene reso come testo semplice.

Le operazioni con sessione browser richiedono la stessa origine dell'applicazione; gli altri client continuano a poter usare il token bearer. Le risorse dell'interfaccia sono incluse nel repository, senza CDN o font esterni. Questa prima interfaccia usa HTML/CSS/JavaScript senza build Node per rendere verificabile il flusso completo prima del contenitore desktop. La distribuzione multiutente resta da implementare.

Il caricamento mostra uno stato di attesa durante upload e validazione, senza percentuali simulate. La compatibilità di riproduzione dipende anche dai codec del browser. Le funzionalità IA non vengono simulate nell'interfaccia: pulizia, trascrizione e dispense sono ancora pianificate.

## Importazione assistita

Nel modulo Aggiungi lezione è possibile trascinare una singola registrazione nell'area dedicata oppure selezionarla con il controllo file, utilizzabile anche da tastiera.

Prima del salvataggio l'app propone:

- Titolo: tag del file quando presente, altrimenti nome ripulito da prefisso della materia e data riconosciuta.
- Docente: tag artista, se disponibile, con avviso di verifica; il tag artista non garantisce l'identità del docente.
- Data: data completa ISO nei tag o nel nome. Date senza anno, come `10-31`, non vengono completate automaticamente.

Le proposte sono modificabili e riportano la provenienza. I campi compilati manualmente non vengono sovrascritti quando arriva la risposta dei metadati. Non viene ancora analizzato il parlato: il riconoscimento semantico del titolo e del docente richiede la futura pipeline di trascrizione.

L'endpoint autenticato `POST /api/v1/audio/preview` riceve un file multipart e legge i tag senza creare lezioni o originali nell'archivio. Per ora il file viene inviato al backend locale una volta per l'anteprima e nuovamente all'importazione; il riuso di un upload temporaneo è un miglioramento futuro, soprattutto per la distribuzione server. Se i metadati non sono leggibili si può compilare manualmente; la decodifica completa avviene comunque all'importazione.

## Pulizia audio integrata (anteprima 0.4)

Aprire una lezione, scegliere l'intensità e premere **Migliora audio**. Il risultato viene salvato separatamente dall'originale; i pulsanti **Originale / Migliorato** consentono di confrontare le versioni mantenendo la posizione, la velocità e lo stato pausa/riproduzione. Le versioni dei diversi preset restano disponibili scegliendo la relativa intensità.

- Leggera: riduzione rumore e guadagno più contenuti.
- Bilanciata: impostazione di partenza per il confronto.
- Intensa: trattamento più marcato, da valutare per possibili artefatti.

Questa versione usa FFmpeg: passa-alto, riduzione spettrale, normalizzazione dinamica e limitatore con compensazione della latenza. Non isola il docente dalle altre persone e non usa ancora modelli IA. I preset non sono stati qualificati percettivamente su un insieme di lezioni; un volume maggiore non dimostra da solo una migliore intelligibilità.

Il risultato è un MP3 a 96 kbit/s: può occupare più spazio dell'originale senza recuperare dettagli assenti nella registrazione. L'originale non viene modificato. La durata utile rimane invariata nella prova completa effettuata; l'allineamento dovrà essere validato su altri formati prima della sincronizzazione con trascrizioni.

### Coda e ripresa

SQLite conserva lavori, preset, parametri, motore e avanzamento. Un thread di orchestrazione avvia un processo FFmpeg alla volta, lasciando libere le API e l'interfaccia. L'avanzamento deriva dal tempo audio elaborato; il 100% viene mostrato solo dopo la pubblicazione del risultato.

L'annullamento ferma il processo e ripulisce il risultato parziale. Al riavvio i lavori rimasti in esecuzione o interrotti ripartono dall'inizio della fase; non riprendono dal campione esatto. I risultati completati vengono riutilizzati a parità di lezione, preset e filtri. La migrazione porta il database alla versione 3.

Avviare **un solo processo Uvicorn per archivio**, senza `--workers`: un lock di filesystem rifiuta un secondo worker sullo stesso archivio. La coda è locale a questa installazione; non è una coda distribuita. Non sono ancora disponibili anteprima su intervallo, regolazione continua dei filtri o gestione grafica globale di tutti i lavori.

| Metodo | Endpoint | Risultato |
|---|---|---|
| POST | `/api/v1/lessons/{id}/enhancements` | Crea/riutilizza un lavoro; JSON `{"preset":"balanced"}` |
| GET | `/api/v1/lessons/{id}/enhancements` | Versioni e lavori della lezione |
| GET | `/api/v1/audio-jobs/{id}` | Stato e avanzamento |
| POST | `/api/v1/audio-jobs/{id}/cancel` | Annulla un lavoro attivo |
| GET | `/api/v1/audio-jobs/{id}/audio` | Versione completata, con supporto Range |

Tutti gli endpoint richiedono autenticazione. Nessun audio o metadato viene inviato a servizi esterni di elaborazione.
