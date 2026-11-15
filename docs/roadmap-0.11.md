# Roadmap implementation — 0.11 development

The downloadable tagged **0.10** preview remains separate from these additions. See [release](https://github.com/ico88/Traccia/releases/tag/v0.10.0). Original lecture recordings are never overwritten.

| Workstream | Implemented / verified | Still requires qualification or access |
|---|---|---|
| Lecture quality | Private three-recording trial, nine source intervals, 24 conditions; original/GTCRN and chunk-boundary comparisons; human-reference and A/B worksheet tools | Human-corrected references, WER/CER and perceptual ratings. No accuracy numbers are invented. |
| Thematic notes and citations | BM25-style rare-term/title retrieval; optional queued local claim/source review, with verbatim-quote and quantity checks | Representative course-level relevance and entailment evaluation. A model-assisted verdict is not independent verification. |
| Audio preview | GTCRN/traditional preview of 0.5–60 seconds, original-interval replay, separate cached derivative and cancellation | Listening qualification on classroom noise; VoxLock preview is not included. |
| History and archive health | Accepted note revision history, read-only historical views; missing/orphan asset report; reversible derivative quarantine/restore | Recovery cannot reconstruct missing source recordings. Quarantine is intentionally outside normal backups. |
| PDF and study diagrams | Embedded raster figure extraction, page/object/PDF fingerprint provenance; source-linked diagrams from accepted notes | Vector-only figures, automatic figure placement, and generated scientific illustrations are not implemented. |
| Server | GitHub CI Linux container build, startup/authentication and native-runtime smoke check passed | i7 benchmark deferred at the owner's request. Multi-user authentication and isolated account archives follow that server validation. |
| Distribution | GPL-3.0-or-later, third-party notices, audio-only source-pinned FFmpeg, corresponding source archive, downloadable non-notarized DMG | No valid Developer ID identity found on this Mac. Notarization, unattended signed updates and clean-second-Mac checks remain pending. |
| CI | Backend checks and Linux container smoke tests active; `backend-tests` required on main | Runtime quality checks need local weights and private references; these are not uploaded to public CI. |

## Archive compatibility

Development 0.11 upgrades archive/backup metadata to schema 6 so 0.10 refuses to open newer job types rather than processing them incorrectly. Keep a 0.10 backup before trying development code. The new restorer accepts both schema-5 and schema-6 backups, always into a new folder; existing originals and manual revisions are preserved. Do not attempt an in-place downgrade. Pending jobs in restored backups are marked cancelled and must be started explicitly from the app; stored job payloads are not automatically executed. Completed results and manual revisions are preserved.

## Using audio previews

Open a lecture, choose GTCRN or traditional filters and expand **Preview audio cleanup**. Set an interval within the recording (0.5–60 seconds), then prepare the preview. The original button plays the chosen interval of the unmodified recording. The enhanced player starts at zero for the clip. Preview jobs cannot be selected as full-lecture transcription inputs. Full enhancement jobs remain separate.

## Note revision history

The course-note selector lists accepted revisions. Historical text has no edit controls; it does not replace the current revision. Generating new proposals and archive exports continue to use the current accepted revision. Printing reflects the displayed view. Source links still open the cited historical transcript.

## Model-assisted citation review

Use **Review citations with local AI** on a sourced chapter/proposal. Qwen runs locally in the existing queue. It reviews at most eight sentences with a bounded source context, classifying support and offering exact quotations. Unsupported quotations or changed dose quantities are downgraded to uncertain. Source snapshots and results are stored separately; notes are not rewritten. Review can be cancelled.

A matched quotation is not proof of entailment. The model can still miss omissions, negation errors and specialist misunderstandings. Student approval and listening remain necessary. Larger chapters explicitly report sentences outside the eight-sentence limit.

## PDF extraction and diagrams

**Extract PDF figures** supports unencrypted files up to 50 MiB / 200 pages, at most 100 embedded raster images, each at most 20 megapixels, with 100 MiB total extracted output. A timed subprocess isolates parsing. Unsupported image objects are reported. Encrypted PDFs are refused; pages made only of vector drawings may yield no images.

The original PDF is not stored inside the archive: keep the source slides. PNG metadata retains the PDF SHA-256, page number and object reference; captions identify the source filename/page. Backups preserve the extracted images and their metadata. Figures are materials, not automatically placed into generated chapters.

**Generate source-linked diagram** connects accepted chapters to their existing lecture references. Edges mean “cites”, never cause or correctness. It adds no new scientific facts. Display limits are eight chapters / three references per chapter, with source anchors retained in PNG metadata.

## Archive reconciliation

**Archive health** is read-only. For maintenance, close the application/server first:

```sh
python -m aulalocale.archive_health --data /path/to/archive
python -m aulalocale.archive_health --data /path/to/archive --quarantine
python -m aulalocale.archive_health --data /path/to/archive --restore /path/to/archive/quarantine/UUID/manifest.json
```

Only recognized unreferenced derivatives are moved into a reversible quarantine. Original recordings, drafts, unknown files and database rows are never deleted. Restore checks hashes and refuses overwrites. Managed symlink directories are refused. Interrupted quarantine/restore can be recovered from the manifest. Keep quarantine manifests and files separately if backing up the archive; ordinary backup includes referenced assets only.

## Human review and scoring

Prepare a private offline worksheet from benchmark outputs:

```sh
python scripts/prepare_human_review.py --results /private/results.json --output /private/new-review-folder
python scripts/score_evaluation.py --results /private/results.json --review /private/exported-human-review.json --output /private/new-scored-results.json
```

The worksheet includes an unfiltered original for reference transcription and two label-hidden comparison tracks (normalized original versus GTCRN-balanced plus the same loudness normalization). It contains no model hypotheses. These listening conditions do not measure the final playback MP3 or VoxLock. It exports explicitly reviewed references and label-hidden A/B listening ratings. WER/CER aggregate actual edit counts over reference words/characters, not an unweighted average of clip percentages. Unreviewed references remain unmeasured. Self-reported 1–5 listening ratings are aggregated separately by the hidden algorithm label, with count and arithmetic mean; they are not population-level quality certification. Keep all generated audio/text outside Git.
