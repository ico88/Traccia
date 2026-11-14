# Prova MOSS-Transcribe-Diarize su Mac M4

Esperimento locale separato dall’app. Modello OpenMOSS-Team/MOSS-Transcribe-Diarize, Apache 2.0. Nessun audio o testo personale viene caricato in servizi esterni. Pesi e codice upstream sono conservati fuori da Git. Il codice personalizzato è stato letto, confrontato con il sorgente ufficiale e verificato contro manifest della revisione prima delle prove riproducibili.

## Revisioni e ambiente

- Pesi/codice Hugging Face: `10304d926740cf5a5cee05a268086e3265197910`.
- Helper ufficiali GitHub: `79c675f0670cc2f824bcbcdd98263704f40f1f7e`.
- Download pesi: 1.817.113.576 byte. SHA-256 in `scripts/moss-assets.json`, insieme a configurazione, tokenizer e codice. Le differenze tra il codice HF e GitHub riguardano il supporto Flash Attention, il metodo di legatura dei pesi e il nome di un metodo del processore; le prove usano la versione HF fissata senza modifiche.
- Seconda venv sperimentale con `requirements-moss-probe.txt`; non è una dipendenza dell’app o del DMG.
- Torch 2.15.0, Transformers 5.23.0. Pesi caricati in float32, attenzione SDPA, greedy, prompt ufficiale predefinito, inferenza locale senza download di ripiego.
- Il resolver ufficiale «auto» sceglie CUDA o CPU; il test seleziona esplicitamente MPS. Nessun ripiego CPU automatico e nessuna abilitazione di fallback per operatori MPS non supportati.

## Ripetere la prova

Preparare la cartella del modello dalla revisione esatta e una copia del sorgente GitHub alla revisione esatta sopra. `--helpers` indica la cartella `moss_transcribe_diarize` nel sorgente. Il programma controlla gli hash prima di caricare codice custom e legge gli stessi WAV/hash del precedente confronto Fluid/Whisper. Non modifica l’archivio AulaLocale.

```sh
/ambiente-moss/bin/python scripts/probe_moss.py \
  --model /modelli/moss \
  --helpers /sorgenti/MOSS-Transcribe-Diarize/moss_transcribe_diarize \
  --comparison /risultati/confronto-fluid-whisper/results.json \
  --output /risultati/nuova-prova-moss \
  --device mps --condition normalized
```

`--sample sample-1` permette un controllo su un solo estratto; `--device cpu` disattiva MPS. Il limite predefinito è 2048 nuovi token: quando raggiunto il risultato è segnalato incompleto. Un limite diagnostico inferiore non dimostra da solo un errore: occorre verificare la ripetizione e la copertura del parlato.

I segmenti vengono letti dal parser ufficiale. Il risultato conserva testo grezzo, testo dei segmenti completi, etichette anonime, timestamp, conteggio token e flag di limite raggiunto. La memoria RSS e quella MPS non sono sommabili; MPS current/driver sono letture a fine caso, non picchi. La misura temporale del programma condivide il caricamento del modello fra casi: non va confrontata direttamente con i tempi di avvio completo delle prove Fluid/Whisper.

## Limiti della verifica

Nessun riferimento umano: WER/CER e correttezza dei parlanti non misurati. Etichette S01/S02 non identificano il docente e non dimostrano una diarizzazione corretta. Gli estratti della lezione non costituiscono un benchmark con parlanti annotati. Compatibilità del caricamento e generazione di testo non equivalgono a qualità didattica.

Non è stata eseguita la lezione intera, né una prova sul server i7. MOSS non viene aggiunto al selettore dell’app o al DMG sulla base di queste prove.

## Risultati osservati

Primo estratto originale, 45 secondi: caricamento MPS riuscito; generazione circa 90,08 secondi, 2048 token. Dopo circa dieci secondi di parlato rappresentato il modello ripete «a fare» fino al limite e lascia il segmento finale incompleto. Controllo CPU sul medesimo WAV: 26,98 secondi fino al limite diagnostico di 512 token, stessa ripetizione. I tempi hanno limiti diversi e non costituiscono un confronto di velocità CPU/MPS.

Sui tre estratti normalizzati (limite 1024 token):

| Estratto | Generazione e preprocessing | Risultato strutturale |
|---|---:|---|
| Inizio, 120–165 s | 12,17 s | 333 token, 10 segmenti, termine regolare |
| Centro, 2100–2145 s | 9,72 s | 266 token, 8 segmenti, termine regolare |
| Fine, 4200–4245 s | 36,40 s | 1024 token, ripetizione «di» e uscita incompleta |

Le uscite terminano entro l’intervallo temporale; questo non misura la precisione dei timestamp. Tutti i segmenti completi riportano S01: non dimostra che il modello distingua correttamente docente e studenti. Nei testi sono presenti formulazioni dubbie e termini farmacologici alterati. Senza riferimento umano non si assegna WER/CER né si dichiara una superiorità di accuratezza rispetto a Whisper o Fluid.

Nella serie normalizzata: picco RSS del processo circa 5,84 GB; memoria allocata dal driver MPS a fine caso circa 4,98 GB. Sono misure distinte e non sommabili. Il caricamento è condiviso; importazioni iniziali Torch/Transformers escluse dai tempi di caso.

Con GTCRN leggero (miscela 35%) seguito dalla stessa normalizzazione, tutti e tre gli estratti terminano senza raggiungere il limite di 1024 token:

| Estratto | Tempo di caso | Token | Segmenti | Etichette |
|---|---:|---:|---:|---|
| Inizio | 13,34 s | 372 | 12 | S01 |
| Centro | 9,45 s | 256 | 8 | S01 |
| Fine | 11,48 s | 319 | 9 | S01, S02 |

La pulizia elimina le ripetizioni osservate in questi tre casi, ma non dimostra una migliore accuratezza: anche i testi puliti alterano termini e frasi. La comparsa di S02 non è stata confrontata con annotazioni umane e non viene considerata un successo di diarizzazione. Sono 8 esecuzioni MOSS complessive: originale MPS e controllo CPU sul primo estratto, tre normalizzate MPS e tre pulite/normalizzate MPS. Non sono stati provati gli altri due originali con MOSS.

Decisione: mantenere MOSS come candidato sperimentale, senza sostituire Whisper né includerlo nel pacchetto Mac. Prima dell’integrazione servono riferimenti umani, test con parlanti annotati, gestione delle generazioni ripetitive e delle uscite incomplete. Nessun tentativo di mascherare il problema con postcorrezione LLM. 64 test automatici superati; il numero non certifica l’accuratezza dei modelli. Gli output personali restano fuori dal repository.
