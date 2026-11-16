# Traccia build log

Checkpoint: 2026-11-16, `sviluppo`, application 0.11.0.dev1, archive schema 7. Real authenticated archive services are used throughout; workshop seed data is not a production fallback. Test archives contain public/synthetic fixtures only. Personal lectures and model weights remain outside Git.

## Screen register

“Implemented” records usable functionality, not completion of every qualification item. **11/14 recon views have working Traccia equivalents; 3 remain partial or deliberately mapped differently.** Strict per-screen acceptance (every error/permission state, complete keyboard flow at both widths and assistive technology verification) is not claimed complete for any of the 14 views. The next phase is replica-test, not a production release.

| ID | Date | Implementation | Remaining qualification / difference |
| --- | --- | --- | --- |
| S01 | 2026-11-16 | Implemented: real library, subject selection, search/empty/error messages, token shell | Full error-state, zoom and assistive-technology matrix remains. Long titles and 390/1440 layouts checked. |
| S02 | 2026-11-16 | Implemented: click/drop multi-file queue, per-file metadata review, duplicate/failure outcomes | Queue is session-local, not durable staging. Real OS drag gesture and large-file qualification pending. |
| S03 | 2026-11-16 | Partial/mapped: native Traccia window plus explicit browser/server mode | No Plaud browser-to-Desktop handoff; this separate screen is unnecessary for Traccia. |
| S04 | 2026-11-16 | Partial: existing recorder, PCM chunks, draft recovery and source preservation retained | Fresh physical microphone, OS denial, sleep/unplug and real capture session need qualification. |
| S05 | 2026-11-16 | Implemented: audio/transcript/context workspace and unchanged original/derivative services | Native visual review and tab keyboard behavior checked; full screen-reader qualification pending. |
| S06 | 2026-11-16 | Implemented: explicit language/configuration and durable transcription→note proposal | Existing study_jobs reused; enhancement/speaker analysis remain explicit separate jobs. |
| S07 | 2026-11-16 | Implemented: revision-aware transcript editing, history and source navigation | No new WER/CER claim; human references and perceptual audio qualification remain necessary. |
| S08 | 2026-11-16 | Implemented: proposals, manual chapter protection, history and changed-template rebuild | Proposals never auto-accept; full cross-state UI acceptance pending. |
| S09 | 2026-11-16 | Implemented: original local templates, creation/editing and optimistic revisions | No community marketplace, favorites or template deletion UI. |
| S10 | 2026-11-16 | Implemented: source search, independent local questions, checked citations, abstention and save-as-proposal | Lexical retrieval, not FTS/embedding search; not a threaded agent. A matching quote does not prove semantic entailment. Latest 20 questions shown. |
| S11 | 2026-11-16 | Implemented: persistent course language, summary language, template and glossary | No generic automation rule language, external email or silent model installation. |
| S12 | 2026-11-16 | Implemented: playback-time highlights, text notes and course-image references | Capture-time draft annotations, annotation edit/delete and automatic visual understanding deferred. |
| S13 | 2026-11-16 | Implemented: revision-specific TXT/Markdown/SRT export with timing/available speaker options; existing course-note exports | SRT always has timing. DOCX and broader export layouts are not implemented. |
| S14 | 2026-11-16 | Partial: existing read-only archive health and closed-archive backup/reconciliation | No destructive rename/move/merge/trash UI; explicit lifecycle design remains required. |

## Feature matrix interpretation

`features.csv` records feature capability, separately from screen qualification. Must-haves: **13 yes, 1 partial out of 14**. The partial item is fresh microphone capture qualification. Other implemented features still need the stated quality/performance/accessibility checks. This is not a measured Plaud parity percentage, and no unavailable Plaud states were invented.

## Evidence

- 115 backend tests passed locally, including installed GTCRN integration tests.
- Meaningful new tests cover stale preference/template revisions, annotation ranges/scope/retry identity, current-revision search, checkpoint recovery without duplicate transcripts/proposals, schema-6 upgrade, backup preservation, protected manual chapters on template change, question citation/quantity refusal, idempotent answer proposals, stale-source rejection and export revision/timing/speaker options.
- English/Italian interpolation, persistence, recording/unsaved-change guards and JavaScript syntax checks passed through the Node runtime.
- A real public speech fixture was imported through the UI, its duplicate skipped, and an MP4 audio container accepted. A corrupt WAV produced a persistent per-file error without changing completed imports.
- Installed Whisper and Qwen completed the real transcription→proposal flow. This checks execution, not transcript or summary accuracy.
- Student notes/highlights and a synthetic figure were saved through the real services. Source search linked back to the actual generated transcript.
- Actual local Qwen Q&A returned an abstention on an incomplete speech excerpt; positive-answer/proposal behavior is covered by controlled backend tests. Do not describe this as measured answer accuracy.
- Read-only viewport checks report no document overflow at 390 and 1440 CSS px for nine views; see clone-screens/viewport-report.json. Native windows were also inspected at those widths. Keyboard tab selection was exercised on the real UI. Native AX tooling did not consistently expose dynamically revealed regions, so assistive-technology acceptance remains pending.
- Palette report remains 49 declared combinations with zero AA failures; it is not full application WCAG certification.

## Migration and release boundary

Schema 7 adds five small tables, preserving the seven baseline tables and their immutable source records. Current restoration accepts schemas 5, 6 and 7 into a **new** directory. Pending restored jobs remain cancelled until explicitly restarted. An older application must not open the upgraded archive; keep a verified pre-upgrade backup. Tests used disposable archives, not the user's personal archive.

The proposed full architecture is implemented incrementally: import staging and FTS/thread tables remain unimplemented; current pipelines use existing durable jobs and questions use a compact archive-owned table. No duplicate scheduler, hosted inference, cloud storage, payment system or new model dependency was introduced.

A new local ad-hoc Mac development package is built separately. The public README's tagged 0.10 download has not been replaced, and promotion of development code to main does not replace that tagged download. Developer ID signing/notarization, clean-Mac validation, real i7 benchmarks, multiuser isolation and manual quality evaluation remain outside this completion claim.

## Promotion review fixes

Question citations now record cited revisions separately from full-transcript coverage, so accepting a short answer cannot block later summarization of the remaining lecture. Course-note status includes pipeline jobs, with frontend regression coverage for progress polling, proposal refresh and failure feedback. The full backend suite passes 115 tests.
