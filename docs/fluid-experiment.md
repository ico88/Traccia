# Prova locale Fluid Speech Pro MLX

Esperimento separato dall'app di produzione: nessuna modifica al motore predefinito, all'archivio o alle dispense. Fluid Speech Pro by FluidVoice, modello CC BY 4.0, è eseguito offline usando la variante MLX 8 bit su Apple Silicon. Nessun token necessario.

## Ambiente isolato

Creare una seconda venv e installare `requirements-fluid-probe.txt`. Il normale ambiente AulaLocale continua a usare `requirements.txt`. Il programma di confronto viene eseguito dall'ambiente AulaLocale, mentre `--fluid-python` indica il Python della seconda venv. Non risolvere il symlink del Python della venv al binario di sistema: si perderebbe l'ambiente isolato.

Pesi e adattatore devono essere preparati in una cartella locale separata, mai dentro Git:

- Repository: [FluidVoice-Labs/fluid-speech-pro-mlx](https://huggingface.co/FluidVoice-Labs/fluid-speech-pro-mlx).
- Revisione fissata: `aeb1d4e43487586b15d86c0a1dd4511e1cf6b7a0`.
- File: `config.json`, `model.8bit.safetensors`, `fluid_speech_mlx.py`.
- Download pesi: 751.204.956 byte. SHA-256 e hash dell'adattatore/configurazione in `scripts/compare_asr.py`, verificati prima di eseguire il codice. Non sostituirli con file generici da `main`.
- Il piccolo adattatore upstream è stato letto prima dell'esecuzione; serve per il blocco aggiuntivo del modello e per le feature NeMo. Il caricatore standard Parakeet non è equivalente. Il codice upstream non viene copiato nel repository AulaLocale o incluso nel DMG.
- Modalità clean disattivata; inferenza greedy e calcolo bfloat16 con pesi a 8 bit.

Esempio, sostituendo i percorsi locali:

```sh
python scripts/compare_asr.py \
  --source /archivio/originals/lezione.mp3 \
  --output /risultati/nuovo-confronto \
  --fluid-model /modelli/fluid-mlx \
  --fluid-python /ambienti/fluid/bin/python \
  --whisper-model /modelli/ggml-large-v3-turbo-q8_0.bin \
  --whisper-bin /runtime/whisper-cli \
  --gtcrn-model /modelli/gtcrn_simple.onnx
```

Il comando non scarica file; la cartella di output deve essere nuova. Fonte, WAV intermedi, testo, log e risultati sono privati. Non pubblicarli nel repository pubblico. SHA-256 anche per Whisper e GTCRN; nessun codice remoto eseguito durante la trascrizione. FFmpeg è fornito dalla dipendenza già presente nell'app; il worker Fluid usa un collegamento temporaneo locale.

## Metodo

Tre estratti da 45 secondi, con inizio a 120, 2100 e 4200 secondi. Per entrambi i modelli vengono forniti gli stessi WAV 16 kHz mono:

1. Originale decodificato.
2. Originale normalizzato `loudnorm=I=-20:TP=-2:LRA=11`.
3. GTCRN leggero, miscela neurale 35%, poi la stessa normalizzazione.

GTCRN viene eseguito separatamente su ciascun estratto: ai confini il contesto differisce dal denoising della lezione intera. Nessun postfiltro di riascolto o ricompressione MP3. Whisper Turbo Q8 usa lingua italiana, 4 thread, senza prompt; Fluid identifica automaticamente la lingua e non riceve un prompt. Tutti gli estratti vengono elaborati in un blocco. Queste condizioni differiscono dalla trascrizione lunga dell'app con contesto della materia e blocchi di dieci minuti.

Ogni caso parte in un processo nuovo. `wall_seconds` include importazioni, caricamento e inferenza; preparazione audio esclusa. Per Fluid sono registrati anche tempi di caricamento/inferenza e memoria MLX / picco RSS del processo. Queste due misure di memoria non sono sommabili. Cache dei file e compilazione Metal influenzano i tempi; una singola esecuzione non è un benchmark generalizzabile. Nessun tempo misurato su M4 viene attribuito al server i7.

## Accuratezza e riferimento umano

Senza trascrizione verificata da una persona, WER/CER restano `null`. Non usare il testo di Whisper, Fluid o un LLM come verità di riferimento. La leggibilità non misura omissioni, termini tecnici o fedeltà al parlato.

Il confronto produce `references.template.json` con una voce per estratto. Dopo averlo compilato e verificato ascoltando l'originale:

```sh
python scripts/score_asr.py \
  --results /risultati/nuovo-confronto/results.json \
  --references /risultati/riferimenti-umani.json \
  --output /risultati/confronto-con-misure.json
```

Non serve rieseguire i modelli. WER è distanza di Levenshtein sulle parole, CER sui caratteri senza spazi. Normalizzazione NFC, minuscole, punteggiatura sostituita da spazi; accenti e numeri mantenuti. Non viene normalizzata l'equivalenza tra numeri scritti in lettere e cifre. Le misure vanno affiancate a controllo di termini farmacologici, negazioni, quantità, omissioni e timestamp. Anche i riferimenti parziali rimangono esplicitamente non misurati per gli estratti mancanti.

## Cosa manca all'integrazione nell'app

Gestione download multi-file verificati, worker annullabile, selettore del modello, persistenza della provenienza, test delle revisioni e packaging MLX con relative licenze. Il runtime ONNX per CPU e il server i7 non sono stati provati. Il DMG 0.6 continua a includere Whisper e GTCRN, senza Fluid.

## Risultati della prima esecuzione — 14 novembre 2026

18 trascrizioni completate, 9 WAV con 720.000 campioni ciascuno. Timestamp presenti e compresi negli estratti; non è stata misurata la precisione dell'allineamento.

| Motore | Tempo mediano per estratto | Intervallo osservato |
|---|---:|---:|
| Whisper Turbo Q8 | 3,37 s | 3,12–3,86 s |
| Fluid MLX 8 bit | 2,46 s | 2,25–2,81 s |

Il primo caricamento Fluid nella prova preliminare ha richiesto circa 19,09 secondi, seguito da circa 2,42 secondi di inferenza. Il confronto successivo usa processi nuovi ma beneficia delle cache già riscaldate: i valori in tabella non descrivono il primo avvio su una macchina pulita. Picco memoria MLX dichiarato dall'API: circa 1,66 GB; picco RSS del processo circa 0,95–0,97 GB. Misure distinte, non sommabili.

Entrambi producono passaggi dubbi nel testo della registrazione. La pulizia modifica alcune ipotesi di entrambi i motori, ma senza riferimento umano non possiamo quantificare miglioramenti o peggioramenti. WER/CER restano non misurati; non è stato dichiarato un vincitore. Gli artefatti privati comprendono tutti i testi e WAV, JSON con parametri/hash, pagina HTML offline per il confronto e modello vuoto per i riferimenti.

62 test superati al momento della prova; la suite verifica anche calcolo WER/CER, normalizzazione Unicode e rifiuto di asset Fluid alterati. Le prove di accuratezza linguistica non sono coperte dai test automatici.
