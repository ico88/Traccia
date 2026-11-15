# Private lecture evaluation

`evaluate_lectures.py` compares normalized originals and GTCRN-balanced audio using the pinned Whisper Turbo model. It samples explicit intervals from multiple local recordings and can compare one recognition pass with two passes split at a real ten-minute boundary. Normalization is held constant to isolate the recognition-boundary effect.

Example manifest (keep actual manifests, recordings and output outside Git):

```json
{"language":"it","samples":[{"id":"lecture-a-1","audio":"/private/lecture.mp3","start":570,"duration":60,"boundary":600,"reference":"","reference_reviewed":false}]}
```

```sh
python scripts/evaluate_lectures.py --manifest /private/manifest.json --output /private/new-results --models /private/models --whisper ./runtimes/whisper-cli
```

The output includes WAV comparisons, raw recognizer output, model/source hashes, timings and a reference template. It refuses existing output directories and does not download weights. Source files are read only.

**WER/CER require a manually corrected reference explicitly marked `reference_reviewed: true`.** Automatic transcripts are not reference text. Empty or unreviewed references remain unmeasured. Specialist-term mentions are presence indicators, not correctness judgments. Timing includes fresh model loading and is not an i7 server benchmark.

## First multi-recording trial

On the development M4, three user-provided university recordings supplied nine distinct intervals, totaling 7.5 minutes of source audio. The run completed 24 condition results, including split-boundary comparisons. Median recognition real-time factor was 0.084; cumulative recognition wall time was 109.68 seconds, excluding preparation/denoising.

No human-reviewed references were provided, so **zero WER/CER values are reported**. No subjective denoising score or semantic accuracy is claimed. Audio, hypotheses and source filenames remain private. Broader representative evaluation and human listening remain pending.

The listening worksheet and post-hoc scorer are described in [0.11 evaluation tools](roadmap-0.11.md#human-review-and-scoring). All three source recordings retained their original SHA-256 after the trial.
