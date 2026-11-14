# AulaLocale

Da una lezione registrata a materiale di studio organizzato per materia, sul proprio computer.

**Progetto in sviluppo iniziale. Non è ancora disponibile un'app installabile.** Il nome è provvisorio.

AulaLocale è pensato per studenti universitari: conservare e riascoltare le lezioni con audio migliorato, correggere le trascrizioni e costruire dispense che crescono con il corso. L'elaborazione IA sarà locale, senza API di inferenza esterne o abbonamenti obbligatori.

Il codice applicativo è sul branch [`sviluppo`](https://github.com/ico88/aulalocale/tree/sviluppo); `main` conserva la documentazione iniziale fino alla prima approvazione.

## Stato attuale

Questa prima base implementa un'API locale con archivio SQLite, creazione e consultazione delle materie, autenticazione tramite token locale e test automatici. Non implementa ancora importazione audio, trascrizione, denoising, dispense o interfaccia grafica.

| Funzione | Stato |
|---|---|
| Archivio persistente delle materie | Implementato nelle API |
| Miglioramento audio e lettore sincronizzato | Pianificato |
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

Il token deve essere esportato anche nel secondo terminale. `GET /health` è pubblico e riporta soltanto lo stato del servizio. La documentazione interattiva è disattivata nella base corrente. Non esporre questa versione su Internet: il sistema multiutente e l'installazione server non sono ancora implementati.

```sh
python -m pytest
```

## Architettura prevista

Interfaccia React/TypeScript condivisa fra contenitore desktop Electron e browser; backend FastAPI, SQLite e file locali; worker separati per le elaborazioni lunghe. La prima implementazione copre solo il backend delle materie.

Candidati da qualificare: whisper.cpp per trascrivere, DeepFilterNet per ridurre il rumore, llama.cpp e un modello multilingue quantizzato per generare dispense. Le versioni, i modelli e le licenze saranno selezionati tramite benchmark, senza promettere qualità o tempi prima delle misure.

## Dati e modelli

Audio originali conservati e derivati separati. Le future dispense avranno riferimenti alla lezione e al minuto sorgente, cronologia e protezione delle correzioni manuali. Il miglioramento audio dovrà servire anche al riascolto.

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
