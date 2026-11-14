# Valutazione modelli audio — 14 novembre 2026

La categoria [Audio-Text-to-Text](https://huggingface.co/models?pipeline_tag=audio-text-to-text&sort=likes) comprende modelli di dialogo e comprensione audio oltre ai trascrittori. L'ordinamento per like non misura accuratezza in italiano, termini universitari, consumi o facilità di installazione. Consultata anche tramite API pubblica Hugging Face perché la pagina filtrata non era accessibile dal lettore web.

## Candidati e decisioni

| Modello | Funzione / condizioni dichiarate | Decisione per AulaLocale |
|---|---|---|
| [Fluid Speech Pro](https://huggingface.co/FluidVoice-Labs/fluid-speech-pro) | ASR 0,63B, italiano tra 25 lingue europee, CC BY 4.0 con attribuzione. Varianti MLX, ONNX, GGUF e Core ML | Primo nuovo candidato da misurare: MLX su M4, ONNX sul server CPU. [Prova MLX su M4 completata](fluid-experiment.md); non ancora integrato nell’app |
| [pyannote segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) | Segmentazione parlato e sovrapposizioni, componente di diarizzazione; MIT, download con condizioni/account/token | Non sostituisce ASR o denoising. Per identità coerenti sull'intera lezione serve una pipeline completa. Accesso gated rende meno semplice l'installazione |
| [Nemotron-3-Diarization](https://huggingface.co/nvidia/Nemotron-3-Diarization) | Diarizzazione streaming/offline fino a 8 parlanti, OpenMDW 1.1; documentato anche runtime nativo NeMo-Speech.cpp | Candidato per docente/domande studenti. Non estrae la voce né trascrive da solo; compatibilità e prestazioni sui due computer non ancora provate |
| [MOSS-Transcribe-Diarize 0.9B](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize) | ASR, timestamp e parlanti, 50+ lingue, audio fino a 90 minuti dichiarati, Apache 2.0; codice Transformers personalizzato | Interessante per lezioni lunghe e italiano; da qualificare runtime, memoria e accuratezza prima di integrazione |
| [VibeVoice-ASR](https://huggingface.co/microsoft/VibeVoice-ASR) | ASR con timestamp e parlanti, 50+ lingue, audio fino a 60 minuti dichiarati, MIT | Alternativa da valutare dopo i modelli più compatti; memoria su audio lungo non deducibile dai soli pesi |
| [Voxtral Mini 3B](https://huggingface.co/mistralai/Voxtral-Mini-3B-2507) | Trascrizione, comprensione e riassunto, italiano incluso, Apache 2.0 | Interessante in seguito per domande sull'audio; la documentazione di riferimento usa vLLM/Transformers, integrazione Mac ancora da provare |
| [Qwen3-ASR 1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) | ASR con italiano, Apache 2.0 | Altro candidato per il confronto controllato, distinto dal Qwen3 4B usato per le dispense |

Le schede Fluid dichiarano risultati favorevoli anche in italiano e disponibilità di runtime specifici per i nostri hardware. Sono dichiarazioni dell'autore e benchmark su altri corpora: non dimostrano una superiorità sulla registrazione di Farmacologia. Le velocità su GPU NVIDIA non vanno applicate a M4 o i7. La modalità «clean» modifica il testo eliminando ripetizioni e intercalari: per il confronto della trascrizione fedele va disattivata.

## Ordine di lavoro

1. Chiudere la prima integrazione di denoising GTCRN, mantenendo FFmpeg per conversioni e controllo volume. È l'unico motore neurale di pulizia implementato in questa versione.
2. Confrontare Whisper Turbo e Fluid sullo stesso campione e sulle stesse varianti audio, con riferimento umano, WER/CER, termini specialistici, omissioni, timestamp, durata e memoria massima. Confrontare anche Whisper Large v3 completo se necessario. Nessuna sostituzione automatica sulla base dei like.
3. Valutare diarizzazione e ASR con parlanti come funzione separata. Etichette «Parlante 1/2» non identificano automaticamente il docente: l'utente deve poter correggere il ruolo.

Nessun nuovo modello di questa tabella è stato scaricato, eseguito o aggiunto all'app durante questa ricerca. I dati restano locali. Fonte della scheda Fluid letta dal README pubblico grezzo dello stesso repository; nessun codice personalizzato del modello è stato eseguito.
