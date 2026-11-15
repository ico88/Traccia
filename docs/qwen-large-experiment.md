# Prova Qwen3-ASR 1.7B e Whisper Large v3 completo

Esperimento offline su M4 con 24 GB, separato dall'app e dall'archivio. Stessi nove WAV/hash del confronto Fluid/Whisper: tre estratti da 45 secondi (120, 2100, 4200 s), ciascuno originale, normalizzato e con GTCRN leggero seguito dalla stessa normalizzazione. Nessun prompt terminologico aggiunto. Nessun riferimento umano disponibile: WER/CER non misurati.

## Modelli e runtime

| Modello | Variante provata | Revisione |
|---|---|---|
| Qwen3-ASR 1.7B | MLX 8 bit, 2.463.307.541 byte di pesi | `mlx-community/Qwen3-ASR-1.7B-8bit`, `a8379a2e2f9e313c9292cdf1af4055ab56d50d55` |
| Whisper Large v3 completo | FP16, 3.095.033.483 byte | `ggerganov/whisper.cpp`, `5359861c739e955e79d9a303bcbc70fb988958b1` |

SHA-256 di tutti i file Qwen e dei pesi Whisper in `scripts/qwen-large-assets.json`. I file piccoli Qwen sono stati confrontati anche con i blob della revisione ufficiale e i pesi con il digest LFS. Nessun file remoto eseguito dal repository del modello Qwen: caricamento dell'implementazione distribuita dal pacchetto mlx-audio.

- Qwen: ambiente isolato `requirements-qwen-asr-probe.txt`, mlx-audio 0.6.5, MLX/Metal 0.32.4, lingua Italian, temperatura 0, massimo 1024 token, nessun glossario o penalità aggiuntiva per le ripetizioni. Caricamento locale strict, cache e inferenza senza accesso Hugging Face.
- Whisper: runtime whisper.cpp già compilato per l'app, lingua it, quattro thread, nessun prompt, stesse opzioni del confronto Turbo precedente.
- Il Turbo di riferimento usa Q8; il Large completo usa FP16. Il confronto non isola l'architettura dalla precisione numerica e non attribuisce ogni differenza al numero di strati.
- I segmenti Qwen in questa prova sono i confini del blocco audio, non timestamp di parole o frasi. L'allineatore Qwen non è stato caricato. I segmenti Whisper sono quelli generati dal motore; accuratezza temporale non qualificata.

## Ripetere

Scaricare i file alle revisioni esatte in cartelle esterne al repository, preparare la venv Qwen e usare l'ambiente normale AulaLocale per l'orchestrazione:

```sh
python scripts/probe_qwen_large.py \
  --comparison /risultati/confronto-fluid-whisper/results.json \
  --output /risultati/nuova-prova-qwen-large \
  --qwen-model /modelli/qwen-asr \
  --qwen-python /ambienti/qwen-asr/bin/python \
  --whisper-model /modelli/ggml-large-v3.bin \
  --whisper-bin /runtime/whisper-cli
```

Il comando non scarica nulla e rifiuta un output esistente. Controlla i pesi e gli hash dei WAV prima dell'inferenza. `--engine qwen` oppure `--engine whisper` limita il motore, mantenendo le verifiche degli asset locali. Ogni caso viene eseguito in un nuovo processo, uno alla volta. `wall_seconds` include avvio, caricamento e inferenza; il worker Qwen verifica anche i propri file. Cache e precedenti compilazioni Metal influenzano i tempi. È una prova delle pipeline locali, non un confronto puro dei soli kernel dei modelli.

Su macOS `/usr/bin/time -l` misura il picco RSS di ciascun processo. Qwen registra anche memoria MLX e tempi separati di caricamento/inferenza. RSS e memoria MLX non vanno sommate. Non sono misure del server i7.

Gli output JSON conservano testo, segmenti, parametri, tempi, memoria e segnalazione del limite token Qwen. Il motore dell'app, le trascrizioni già archiviate e le dispense non vengono sostituiti. Pesi e registrazioni personali restano fuori da Git; nessuna modifica al DMG 0.6.

## Risultati — 14 novembre 2026

18 nuove trascrizioni completate (9 per motore). Qwen termina tutti i casi senza raggiungere il limite di 1024 token. Il caricamento strict dei pesi e l’inferenza MLX funzionano sul M4.

| Motore | Tempo mediano di processo per 45 s | Intervallo | Picco RSS osservato |
|---|---:|---:|---:|
| Qwen3-ASR 1.7B MLX 8 bit | 6,57 s | 5,90–7,08 s | 2,70–2,73 GB |
| Whisper Large v3 FP16 | 8,54 s | 6,85–9,19 s | 4,19–4,22 GB |

Qwen registra anche un picco MLX di circa 3,70 GB, che non va sommato al picco RSS. Singola esecuzione per caso, ordine fisso Whisper poi Qwen; nessuna prova a cache fredda o sul server i7.

Sul primo originale Whisper completo produce soltanto una formula da sottotitoli («Sottotitoli e revisione a cura di QTSS»), non una trascrizione sostanziale della lezione. Normalizzazione e pulizia modificano il risultato. Qwen produce testo della lezione nelle tre condizioni, ma con ipotesi instabili sui termini specialistici; anche il Large normalizzato contiene passaggi dubbi. La variazione di nomi e frasi fra le condizioni non dimostra quale testo sia corretto. Non viene dichiarata una superiorità di accuratezza né un beneficio uniforme della pulizia.

Sono conservati un confronto privato fra tutti e quattro i motori (Turbo, Fluid, Qwen, Large completo), i nove WAV identici, 36 ipotesi testuali e il modello dei riferimenti umani. Tutti i punteggi WER/CER restano null. I timestamp Qwen sono solo confini del blocco; i segmenti Whisper rientrano nell’intervallo degli estratti, senza valutazione dell’allineamento.

Decisione: nessuna sostituzione automatica nell’app. Qwen rimane candidato per una scelta sperimentale dopo verifica dei testi, allineamento e integrazione del download multi-file; il Large completo non dimostra, su questo campione, un miglioramento sufficiente a giustificare una promozione automatica. Nessun peso o testo personale incluso nella pubblicazione Git.

65 test automatici superati, incluse le verifiche dei checksum dei candidati e l’esportazione HTML con testo escapato. Le prove dei modelli reali sopra sono distinte dai test automatici.
