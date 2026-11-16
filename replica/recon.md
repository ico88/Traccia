# Recon map: Plaud software patterns for Traccia

Date: 2026-11-15. Target: Plaud Web 4.x, with Desktop capture and explicitly labelled mobile references. Audience: university students using Traccia on Apple Silicon or a self-hosted server. Scope was explicitly confirmed in chat: software patterns for university lectures on Mac/web, with free local processing and no Plaud hardware or cloud services. This is a research deliverable, not authorization to implement the entire Plaud product.

## Sources

Public documentation only. No Plaud account was accessed, no recordings uploaded, no private endpoints or application code inspected. Read individually on the date above. Claims below use these source IDs; platform/version differences are intentional.

| ID | Source | URL | Evidence and limits |
| --- | --- | --- | --- |
| P01 | Italian Note Pro page | https://it.plaud.ai/pages/plaud-note-pro | Product positioning; capture highlights, text and image context. Hardware claims are outside scope. |
| P02 | Web file import, 4.x | https://support.plaud.ai/hc/en-us/articles/63431016171545-File-import-on-Plaud-Web-for-v4-0-x-or-later | File entry points, limits, duplicate handling and date sorting. |
| P03 | Web transcription, 4.x | https://support.plaud.ai/hc/en-us/articles/63431016241433-Transcription-on-Plaud-Web-for-v4-0-x-or-later | Manual generation dialog and original/cleaned text versions. |
| P04 | Web recording, 4.x | https://support.plaud.ai/hc/en-us/articles/63431044149273-Record-on-Plaud-Web-for-v4-0-x-or-later | Browser hands recording to Desktop. |
| P05 | Web templates, 4.x | https://support.plaud.ai/hc/en-us/articles/63431072621081-Summary-templates-on-Plaud-Web-for-v4-0-x-or-later | Template preview, favorites, personal prompts, replacement or additional notes. |
| P06 | Desktop generation and Q&A | https://support.plaud.ai/hc/en-us/articles/53793130069657-Transcribe-and-summarize | Auto/custom paths, vocabulary, questions and possible transcript references; version not specified. |
| P07 | Web automation, 4.3+ | https://support.plaud.ai/hc/en-us/articles/63431015738393-Automatic-transcription-and-summary-settings-on-Plaud-Web-for-v4-3-0-or-later | Rule settings; not assumed present on all 4.x deployments. |
| P08 | Mobile summary and mind map | https://support.plaud.ai/hc/en-us/articles/55624401842841-How-to-Generate-a-Summary-and-Mindmap | Mobile flow; does not establish Web layout. |
| P09 | Web file management, <=3.30 | https://support.plaud.ai/hc/en-us/articles/51073437504665-Rename-delete-move-merge-and-restore-files | Historical organization/batch actions; current Web details need verification. |
| P10 | Export, mobile <=3.30 | https://support.plaud.ai/hc/en-us/articles/50835453223705-Export-recordings-transcripts-and-summaries-in-Plaud-App | Historical export choices; not proof of current Web formats. |
| P11 | Global pricing | https://www.plaud.ai/pages/plaud-ai-plan-pricing | Usage allowances and commercial packaging; not an Italian price quote. |
| P12 | Public website terms | https://www.plaud.ai/policies/terms-of-service | Public terms inspected, including IP section; not a complete audit of account-specific terms. |
| P13 | Web login, <=3.30 | https://support.plaud.ai/hc/en-us/articles/52921405622425-Log-into-the-Plaud-Web | Historical account/cloud relationship; not current Web navigation evidence. |

No changelog, current App Store screenshots, public walkthrough, or public API documentation was needed to substantiate this limited map. Those remain evidence gaps, not invented sources. No application screenshots were captured; `screens/README.md` records the reference policy.

## Core loop and product boundary

Capture or import a recording → obtain transcript and structured notes → review, retrieve and reuse the content [P02–P06]. For Traccia the loop becomes: add lecture → confirm suggested subject/title/date → process locally → inspect sources and improved audio → accept an update to the course handout. The second sentence is our design proposal.

P02 documents click/drop import for audio, video, images, documents and text. Its published limits are 500 MB/24 h for audio/video (split above 5 h), 20 MB for images, 15 MB for documents and 2 MB for text. It describes duplicate skipping and sorting by original creation date. These are Plaud limits, not specifications to copy into Traccia.

P03 describes a generation dialog with audio language, voice labeling, template, summary language and model options. It distinguishes original text from optional cleaned-up text. Cleaning transcript prose is different from denoising playback audio; no claim that Plaud exposes a GTCRN-style A/B audio control was established.

P04 documents browser-to-Desktop recording handoff. Traccia already has its own native window and recording flow; reproducing that handoff is unnecessary.

P05 describes template search/preview/favorites, personal named prompts and either replacing or adding an output. P06 describes questions grounded in recordings, possible quote/timestamp references, saved answers, cross-recording search and custom vocabulary. Exact current Q&A placement remains unobserved.

P07 describes optional generation rules with keyword/duration/source conditions and language/template/model actions. This supports studying configurable defaults, not silently enabling cloud processing or email in Traccia.

P08 documents a mobile mind map derived from the summary. P09 documents older Web organization and batch operations. P10 lists historical export formats: MP3/WAV audio; TXT/SRT/DOCX/PDF transcripts; TXT/Markdown/DOCX/PDF summaries; PNG/Markdown maps. Current Web availability must be checked separately.

P11 advertises minute-based tiers (300 monthly Starter, 1,200 Pro, up to 24 h/day Unlimited). The relevant lesson is clear resource/status feedback; Traccia retains free local inference, without subscriptions or artificial minute quotas.

## Screen inventory

These are documentation-derived views/dialogs, not verified routes or a measured full screen count. No interactive state was directly observed. “Documented” means described by a source; “to verify” means a needed QA state rather than an observed behavior.

| ID | View | How reached | Purpose / key components | Evidence / states |
| --- | --- | --- | --- | --- |
| S01 | Library | Web navigation | File rows, dates, add control | P02; imported/duplicate documented; empty/loading/error to verify |
| S02 | Import dialog | Add → Import files or drop | Drop zone, file selection, upload | P02; transcoding/upload/duplicate documented; cancel/partial failure to verify |
| S03 | Desktop handoff | Add → Start recording | Browser open-app prompt, installer fallback | P04; installed/not installed documented; permission denial to verify |
| S04 | Desktop recorder | Open Desktop | Start/stop capture, context actions | P01/P04; recording conceptual; permission/pause/interruption to verify |
| S05 | Recording detail | Select a library file | Audio, generation entry, artifacts | P03/P06; ready/generating/result documented; exact layout unknown |
| S06 | Generation settings | Detail → Generate | Languages, template, model, voice options | P03; configuration documented; missing entitlement/failure to verify |
| S07 | Transcript | Detail after processing | Original/cleaned selector, speaker/timing references | P03/P06; text versions documented; playback synchronization to verify |
| S08 | Summary/artifacts | Detail after processing | Structured output, new note/regenerate | P05; replace/add documented; failed generation to verify |
| S09 | Templates browser/editor | Tools → Templates | Search, categories, preview, favorite, personal prompt | P05; saved/personal documented; empty results to verify |
| S10 | Ask recording(s) | Ask Plaud, exact current path unknown | Question, answer, references, save answer | P06; functional description only; no-answer/error to verify |
| S11 | Generation preferences | Settings → Preferences | Rules, condition/action editor, enabled switch | P07, 4.3+ only; default/custom documented; validation to verify |
| S12 | Context/highlights | During capture/detail, platform-dependent | Marker, text note, image | P01 marketing evidence; exact timing/editor behavior unknown |
| S13 | Export | Content export action | Content/format/options selector | P10 older mobile; current Web route and states unknown |
| S14 | File actions | Row menu/batch selection | Rename, move, merge, trash/restore | P09 older Web only; destructive semantics need current verification |

## User flows

Click counts below are documentation-derived lower bounds, not measured timings. File picker interaction, typing, scrolls, automatic processing and waiting are excluded. Unknown flows are not assigned invented counts.

| ID | Goal / path | Happy-path actions | Edges to verify |
| --- | --- | --- | --- |
| F01 | Import: S01 → S02 → S05 | Menu path at least 3 activations (Add, Import, chooser); drop alternative | Unsupported/oversize/duplicate, cancel, failed transcoding, file-date surprises |
| F02 | Record: S01 → S03 → S04 → S05 | At least 3 to reach recorder (Add, Start, browser Open); start/stop count unverified | Missing app, microphone denial, sleep, device unplugged |
| F03 | Manual generation: S05 → S06 → S07/S08 | At least 2 (Generate, Generate now), excluding option changes | Wrong language, insufficient quota, processing failure |
| F04 | Change text version: S07 → S07 | Exact dropdown interaction count unmeasured | Cleaned text changes meaning/numbers; preserve original |
| F05 | Add alternate note: S08 → S09 → S08 | At least 2 (+ New note, choose template); confirmation unverified | Preserve current note; distinguish outputs |
| F06 | Ask and inspect evidence: S05 → S10 → S07 | Unmeasured | Unsupported premise, missing citation, irrelevant passage, cancelled request |
| F07 | Add capture context: S04 → S12 | Unmeasured; hardware short press is not a software click benchmark | Image timing, deleted marker, note not saved |
| F08 | Configure automatic processing: S11 → S06/S08 | Unmeasured | Rule conflict, default fallback, disabled rules, resource contention |
| F09 | Reuse/export: S07/S08 → S13 | Historical mobile at least 4 (export entry, type, format, export) | Missing sources/images, overwrite, invalid filenames |
| F10 | Organize recordings: S01 → S14 → S01 | Historical Web rename menu at least 2; edit confirmation unmeasured | Batch partial failure, accidental deletion, restore conflicts |

For Traccia, proposed F01 target: one drop, then one confirmation of suggested metadata. Do not claim AI can reliably infer date/teacher from speech without evidence. Filename metadata should remain editable and be labelled as suggestions.

## Repeated components

All visual states (hover/focus/disabled/loading/error) need direct observation or original Traccia design; none were measured on Plaud.

| Component | Variants / required states | Screens |
| --- | --- | --- |
| Navigation/library row | selected/unselected; ready/processing/failed | S01,S05,S09,S11 |
| Drop area and queue | idle/dragging/valid/rejected/uploading/duplicate | S02 |
| Audio transport | original/improved in Traccia; play/pause/seek/speed/loading | S04,S05,S07 |
| Metadata form | suggested/manual/unknown/invalid | S02,S05; Traccia proposal |
| Generation controls | default/custom; queued/running/cancelled/failed | S05,S06,S11 |
| Segmented output tabs | transcript/notes/context; original/cleaned | S05,S07,S08,S12 |
| Source anchor | timestamp/quote; available/missing | S07,S08,S10 |
| Template card/editor | preview/favorite/personal; unsaved/invalid | S09 |
| Question composer | idle/sending/cancelled/no evidence | S10 |
| Marker/context card | timestamp/text/image; edit/delete | S12 |
| Overflow/batch toolbar | single/multi-select; confirmation | S01,S14 |
| Export dialog/status notice | content/format; ready/failure | S13 and asynchronous flows |

## Inferred data model

Conceptual entities only: no claims about Plaud's private schema or endpoints.

| Entity / suggested fields | Evidence | Confidence |
| --- | --- | --- |
| Workspace: id, display_name, preferences | P07 workspace settings | medium |
| Recording: id, title, source, recorded_at, duration, audio_ref, status | P02/P03/S01/S05 | high |
| Container: id, name, parent_id optional | P09/S14, older Web | medium; hierarchy not established for Web |
| TranscriptRevision: id, recording_id, kind, language, segments | P03/S07 original/cleaned | high concept; storage guessed |
| Speaker: id, label; Segment: speaker_ref, start, end, text | P03/P06/S07 | medium; segmentation schema inferred |
| Artifact: id, recording_id, kind, body, template_ref | P05/S08 multiple notes | high concept |
| Template: id, name, prompt, favorite, provenance | P05/S09 | high |
| ContextItem: id, recording_id, kind, text_or_asset, time optional | P01/S12 | medium; timing linkage not confirmed |
| QuestionThread: id, scope_refs; Answer: text, source_refs, saved_artifact | P06/S10 | medium |
| GenerationRule: conditions, actions, enabled, default_flag | P07/S11 | high concept |
| ProcessingJob: id, recording_ref, stage, state, error | P02/P03 generating states | inferred implementation entity |
| ExportRequest: content_refs, format, options | P10/S13 older mobile | medium; persisted storage not established |

Twelve entity groups above; speaker/segment and thread/answer are grouped for sizing, not a normalized SQL design. Relationships: recording → transcript revisions/artifacts/context; transcript → segments → speaker labels; artifact → source references; rule → processing configuration; answer → evidence passages. Traccia additionally needs Subject → Lessons and versioned CourseHandout → Chapters → immutable source anchors. Those are our requirements, not a claimed Plaud model.

## Feature matrix and existing Traccia baseline

See `features.csv`: 14 must, 12 should, 3 could, 5 skip (34 rows). `clone=no` intentionally starts the NEW recon acceptance matrix unverified, as required by this workflow. It does **not** mean existing Traccia features are absent. No parity percentage can be honestly calculated until each row is verified against this scope. `original=unverified` or `no evidence` is not a claim of absence.

Baseline inspected at commit 266c67b: Traccia already implements subjects, import/drop and metadata suggestions, local recording, playback and enhanced versions, local ASR/speakers, editable transcripts, cumulative course notes with source links/manual protections, note history, evidence review, PDF raster extraction and backup/reconciliation. Relevant files: `aulalocale/lessons.py`, `suggestions.py`, `enhancement.py`, `study.py`, `materials.py`, `web/preview.js`, `web/study.js`. This was a code/document review, not a new interactive acceptance run.

Priorities for the next design pass:
1. One import queue with per-file status and editable metadata suggestions; reusable per-subject processing defaults.
2. A lecture workspace with audio/transcript/notes/context and clearly distinct source versus AI text.
3. Timestamped student highlights and notes, then local course Q&A with mandatory inspectable source anchors.
4. Small original academic templates (lecture, definitions, comparisons, exam review), preserving manual edits and versions.
5. Improve full-text retrieval before adding broad automation or collaboration.

## Exclusions and terms boundary

P12 reserves Plaud content, marks and trade dress. We do not copy its source, logos, text, proprietary templates, assets, private APIs or hardware. Public website terms were inspected; this is not clearance to use a logged-in account for competitive analysis. Any future account session requires checking its actual applicable terms first. Reference screenshots, if added, remain local and are never shipped.

Hardware recording range, microphone arrays, firmware, device pairing and battery claims are excluded. Also excluded: Plaud-hosted cloud sync, paid model access, template marketplace/community content, commercial minute quotas, partner integrations and customer data. Self-hosted multiuser work remains a separate Traccia roadmap stage. Scientifically accurate generated illustrations are a separate qualification problem; a mind map is not proof of correct scientific diagrams.

## Size, uncertainty and next step

14 documentation-derived views; 10 flows; 12 conceptual entity groups. Full new implementation of this slice would be L (roughly a quarter for a small team, a sizing category rather than a delivery commitment). Incremental improvements on existing Traccia are M in scope before qualification, with no fixed calendar promise.

Three hardest parts: (1) reliable source-grounded course Q&A across evolving lectures, (2) interruption-safe local audio/model jobs on limited hardware, (3) multimodal context and handout updates that preserve student edits and provenance. A second tranche of evidence should directly observe library/detail/import states and current export behavior, if authorized access becomes available.

Next: `/replica-architect`, adapting the existing Python/SQLite/WebKit architecture instead of replacing it with a cloud stack. Decide acceptance criteria for import defaults, capture context and sourced Q&A before implementation.
