# Verifica: modello e trattamento audio

Il riconoscimento corrente usa Whisper Large v3 Turbo Q8, con normalizzazione del volume. Dalla versione 0.6 è possibile scegliere originale o versione migliorata; per GTCRN viene usato il WAV prima della ricompressione MP3. La scelta non è automatica: occorre qualificare il trattamento.

Confrontare prima Turbo e Large v3 completo, mantenendo identiche lingua, impostazioni, segmentazione e precisione numerica comparabile. Per ogni modello usare gli stessi estratti in tre condizioni: originale, normalizzazione conservativa, normalizzazione con riduzione rumore leggera. Separare la variazione del modello da quella dei filtri.

Selezionare campioni con voce vicina, distante e rumore, oltre a termini specialistici. Preparare un testo di riferimento corretto ascoltando l'audio. Misurare WER/CER, correttezza dei termini tecnici, omissioni, testo nei silenzi, timestamp, tempo e memoria. La sola plausibilità del testo e il giudizio di un altro LLM non bastano a misurare l'accuratezza.

Qwen3-ASR-1.7B è un candidato indipendente successivo, con italiano dichiarato e inferenza locale: richiede qualificazione del runtime su Apple Silicon e un adattatore diverso dal motore delle dispense. Non è ancora integrato.

L'audio per il riascolto e quello destinato all'ASR possono richiedere trattamenti diversi. La pulizia aggressiva può alterare elementi utili al riconoscimento; la scelta va guidata dai risultati del confronto. Registrare sempre sorgente e filtri e conservare l'originale.

Riferimenti upstream:
- https://huggingface.co/openai/whisper-large-v3-turbo
- https://huggingface.co/openai/whisper-large-v3
- https://huggingface.co/Qwen/Qwen3-ASR-1.7B
- https://github.com/Rikorose/DeepFilterNet

Prima prova controllata Fluid/Whisper su tre estratti: [metodo e risultati](fluid-experiment.md). Nessun riferimento umano disponibile, quindi accuratezza non misurata.

Prova successiva completata con [Qwen3-ASR 1.7B MLX e Whisper Large v3 completo](qwen-large-experiment.md), nove WAV per ciascun modello. WER/CER ancora non misurati; testo, limiti e prestazioni documentati separatamente.
