# Traccia component system

Status: isolated, interactive design proposal for the recon/architecture scope. Not integrated into the production application. English specimen copy; product implementation must use existing English/Italian catalogs. Source reference: `../recon.md` S01–S14. Start at `index.html`, served from the repository root as explained in README.md.

## Evidence and measurement ledger

There are no authenticated Plaud screenshots in `../screens/`. Consequently **none** of this palette, typography, spacing or layout is claimed as a measured Plaud specification. The user's earlier import reference establishes the click-or-drop pattern; no pixel/color measurements were extracted from that attachment during this phase. We use public documented workflows, original Traccia design choices and existing repository assets.

| Property | Existing Traccia evidence | This proposal |
| --- | --- | --- |
| Identity | `aulalocale/web/style.css`: warm paper, terracotta #a45438/#85412c; existing original Traccia icon | Preserve the identity, darken action accent to #91462f for contrast; do not adopt Plaud colors/assets. |
| Typography | Existing CSS declares Inter with system fallback; no font copied from Plaud | Use system sans and monospace stacks, zero font network/download/bundling requirements. |
| Type scale | Existing CSS includes 12/14/19/36 px among others | Proposed 12/14/16/20/28/40 px; 18/20/24/28/36/48 px line heights. Body 14, reading text 16. |
| Spacing | Existing app has mixed values | Proposed four-pixel base: 0,4,8,12,16,20,24,32,40,48,64. |
| Sidebar | Existing `.shell` column 245 px | Proposed 240 px; library panel 260 px; content max 1440 px; header 72 px. |
| Responsive | Existing app has 760 px compact breakpoint | Proposed 1100 px workspace stacking and 720 px compact navigation; no implied Plaud breakpoint. |
| Radius/shadow | Existing app mostly 8–16 px corners, subtle cards | Proposed 6/10/16 px plus pill; card/pop shadows. |
| Motion | No Plaud measurements | Proposed 120/200 ms; reduced-motion override; no animated progress pretending to be real work. |

Native WebKit desktop at approximately 1280 px and actual 520 px in-app-browser layout were inspected. The in-app viewport override did not change its reported width; do not interpret the requested override sizes as measured 390/1280 px browser tests. At 520 px, a navigation min-content overflow was found and fixed. Full minimum-width, zoom, forced-color and screen-reader qualification remain future acceptance work.

## Tokens and allowed roles

`tokens.json` is the source of truth. `build_tokens.py` generates `tokens.css` and optional `tailwind.config.cjs`. Traccia continues to use plain CSS; the mapping targets Tailwind 3 configuration syntax and does not add Tailwind to the application. Role names remain stable if values change.

Colors: bg, surface, surface-subtle, text, text-muted, accent, accent-hover, accent-soft, on-accent, border, border-input, focus, danger/success/warning with soft surfaces, disabled-bg/text. Five neutral background/border roles plus two neutral text roles; semantic roles are separate. Decorative borders are not relied on to identify inputs. Input borders and focus rings use the contrast-tested roles. Status meaning always has visible text, not color alone.

The 49 declared foreground/background pairs pass the supplied checker: text >=4.5:1, essential UI boundaries >=3:1. Disabled text is checked too, even though disabled elements have WCAG contrast exceptions. This is a palette check, **not a full WCAG conformance certification**. Browser-native control rendering, focus occlusion, zoom and assistive technologies require separate checks. Third-party OS/native-control colors and the existing brand image are outside the token-pair report.

Prohibited: raw color literals in component rules, low-opacity disabled labels, making color the only status signal, claiming quote matching certifies an answer, and adding network fonts/analytics. Raw shadow/backdrop alpha values are decorative token/overlay choices, not text surfaces.

## Common interaction rules

- Native `<button>`, `<input>`, `<select>`, `<textarea>`, `<dialog>`, `<progress>` first. No React/accessibility-framework migration for this stack.
- Interactive target minimum 44 px high; inline text links retain normal link semantics. Display-only badges are not buttons.
- Focus-visible: 2 px focus role with 4 px gap; no outline removal. Keyboard order follows document order. Icon-only actions have explicit accessible names.
- Disabled: readable disabled tokens, true disabled property. Loading retains a meaningful label plus `aria-busy`; real cancellation waits for worker acknowledgement.
- Text may wrap; no clipping of lecture titles, filenames, error explanations or translated labels. Compact layout stacks panels; horizontal navigation is locally scrollable rather than causing document overflow.
- Announce completion/error summaries, not every percentage tick. Preserve user input after recoverable errors. Avoid unexpected focus movement except dialogs and explicit navigation.
- No automatic audio playback. User data inserted with textContent, never innerHTML. Catalog files stay in memory; no backend, fetch, model call or persistent storage.

## Components

### Navigation and library row
- Variants: section navigation; course/lecture row; selected/unselected; ready/processing/failed.
- Tokens: surface-subtle, text, text-muted, accent-soft; radius md; spacing 12/16.
- States: hover border/soft surface, visible focus, selected text/outline, empty and filtered-empty. Demo includes populated and filtered-empty; failed row uses shared status/notice spec.
- Accessibility: links for destinations, buttons for local selection. `aria-current` on navigation, `aria-pressed` on toggled sample lecture rows. Selection doesn't auto-play audio.
- Used on: S01,S05,S09,S11. Code: sidebar, lecture-row, lecture-search.

### Button and icon action
- Variants: primary, secondary, ghost, danger; optional icon next to text; close icon has a label.
- Sizes: default min 44 px; future compact 32 px only in dense pointer UI with separate accessible target qualification; touch/primary 44–48 px.
- States: default, hover, pressed, focus-visible, disabled, loading. Demo loading lasts one second, labels itself a sample and performs no work.
- Tokens: accent/on-accent, surface/text/border-input, danger/on-accent; radius md; sm/600.
- Accessibility: button type explicit in forms; disabled property; aria-busy during loading; destructive action opens named confirmation with safe action first.
- Used on: all screens. Code: .button, loading-demo, confirm-dialog.

### Metadata form, selector and checkbox
- Variants: text/search/date in the eventual import form; select; multiline context; consent/default checkbox.
- States: editable suggestion, confirmed manual input, unknown/empty, focused, invalid, disabled, saving, stale-revision conflict.
- Tokens: surface/text, border-input, text-muted hints; danger error text. Label 14/600; inputs 44 px minimum; text area resizable.
- Accessibility: persistent label, help/error IDs via aria-describedby; aria-invalid only after validation. Required fields use native validation in this specimen. Product validation must add field-level text, preserve values, focus the first invalid field, and surface 409 conflicts without overwriting edits.
- Used on: S02,S05,S06,S11. Demo implements title required/max length and independent language selects. Date inference, custom field-error rendering and optimistic conflicts are specified, not connected to a backend here.

### Import drop area and queue
- Variants: dialog drop area; batch rows; review, receiving, ready, duplicate, failed, cancelled.
- States: idle, focus-within, dragging, selected, unsupported type, oversize, empty queue; backend-only states have static visual specimens/specification.
- Tokens: bg, border-input dashed, accent-soft drag surface, focus outline, text/text-muted; radius md; 260 px proposed desktop drop target.
- Accessibility: actual multiple file input with visible associated label; keyboard selection works without dragging. Live result region announces per-file selection. Dialog remains closable. Body drops are prevented from accidentally navigating to a file.
- Used on: S02. Demo lists at most 20 filenames, flags extension or >512 MiB; it **does not decode, hash, upload, detect true duplicates or enforce production validation**. Queue duplicate row is synthetic.

### Dialog and confirmation
- Variants: import, student note, source excerpt, destructive confirmation.
- States: open, closed, scrollable on short screens, invalid form; processing modal closure is not cancellation.
- Tokens: surface/text, border-input, radius lg, shadow pop; 680 px max and 16 px viewport margins; dim decorative backdrop.
- Accessibility: native showModal focus containment, Escape close and focus return; aria-labelledby, descriptive text for import; safe confirmation action autofocus. No nested dialogs. Close is always reachable by keyboard.
- Used on: S02,S06,S12,S13,S14. Code: four native dialogs. Native Mac and browser Escape behavior verified; native model download/real destructive operations aren't part of this catalog.

### Output tabs and segmented controls
- Variants: transcript / study notes / my context tabs; original / improved audio button group.
- States: selected, unselected, hover, focus, unavailable. Each panel has its own label and visible source context.
- Tokens: text-muted, accent, border and accent-soft; 44 px targets; no color-only selection.
- Accessibility: tabs have aria-controls/selected and roving tabindex; Left/Right/Home/End navigation; panels hidden when inactive. Audio selector uses aria-pressed buttons, not tab semantics.
- Used on: S05,S07,S08,S12. Arrow-key selection and panel visibility verified in browser.

### Audio transport and comparison
- Variants: original/full improved/interval preview; volume and speed in product integration.
- States: no audio, metadata loading, ready, playing, paused, failed, cancelled preview; preserve source/time when changing supported full versions.
- Tokens: accent seek track, text-muted timing, surface panel, border divider; numeric timing uses monospace.
- Accessibility: labelled seek range and output; buttons announce action; no autoplay; original and enhanced never play simultaneously. Do not equate a 5-second preview's clock with the entire lecture's clock.
- Used on: S04,S05,S07. Catalog transport is explicitly a visual sample without loaded audio; real player behaviors reuse current Traccia services and need integration tests.

### Transcript passage and source anchor
- Variants: speaker/time/text, selected passage, human-reviewed checkbox, unavailable source.
- States: original versus edited revision, active playback, historical read-only, missing source, text correction conflict.
- Tokens: base text 16/24, sm metadata, accent-soft anchor, underline; source target 44 px.
- Accessibility: descriptive time-link action, inspectable exact revision/segment/time, text never depends on audio alone. Missing source retains the reference and explains its absence instead of linking another revision.
- Used on: S07,S08,S10. Demo source dialog contains synthetic text only; it does not seek real audio.

### Template card/editor
- Variants: original academic default, custom private prompt, favorite; preview before apply.
- States: saved/unsaved favorite, empty search, creating/saving/invalid prompt, referenced-template deletion conflict.
- Tokens: surface, text/text-muted, radius md, accent; 14/20 explanatory copy.
- Accessibility: toggle favorite has a constant accessible name plus aria-pressed; prompt editor has a persistent label and length hint. Applying a template never silently replaces manual text.
- Used on: S09. Catalog has favorite toggle and descriptive card; actual prompt CRUD/default references are architecture-stage contracts.

### Question composer and answer/evidence card
- Variants: lecture/course scope; answer with sources, uncertain/abstained, failed/cancelled request.
- States: empty, sending, cancel requested, no evidence, complete, saved as proposal; scoped source changes require new retrieval.
- Tokens: surface/text for answer, success-soft or warning-soft with matching semantic text; no unsupported green “verified” stamp.
- Accessibility: explicit question label, submit only valid input, live completion summary; citations have meaningful names. Do not move focus on every streamed token. Saving an answer creates a proposal with provenance.
- Used on: S10. Demo submits locally to reveal a static incomplete-evidence card; never sends question text to a model.

### Marker/context card
- Variants: highlight, student text, image with caption/page/source, capture draft.
- States: editing/unsaved/saved, missing asset, pending capture promotion, range invalid, conflict.
- Tokens: surface-subtle, text/text-muted, badge, spacing 16/20; image object-fit contain and useful alt text when integrated.
- Accessibility: time is navigable, student authorship visible; captions do not claim AI image understanding. Provide an equivalent keyboard path to every capture action.
- Used on: S04,S12. Demo text context and note dialog are interactive; image timeline binding and capture journaling await implementation.

### Job timeline, progress and recovery
- Variants: queued, running, blocked/model missing, completed, failed, interrupted, cancelling, cancelled.
- States: bounded per-stage progress; indeterminate when unknown; partial results remain visible; retry doesn't duplicate effects.
- Tokens: neutral badge for current/waiting, success/danger/warning labels, native progress accented; ordered vertical list.
- Accessibility: real labelled progress element, current step identified, state messages do not rely on colored dots. Cancellation remains a request until acknowledged.
- Used on: S02,S05,S06,S11. Demo 62% is fixed synthetic data, never a real progress estimate.

### History and acceptance control
- Variants: current accepted note, unaccepted proposal, historical accepted revision; conflict warning.
- States: current editable by creating a new revision, historical read-only, saving, stale base, empty history.
- Tokens: warning notice for proposal, neutral history hint; same select/input styles.
- Accessibility: visible read-only explanation and disabled edit control; selection never changes accepted version. Proposal acceptance requires separate human action and source inspection.
- Used on: S07,S08. Historical selector demonstrably disables edit in the catalog; it does not mutate notes.

### Overflow/batch actions and export
- Variants: single selection, batch selection, content/format/options chooser.
- States: no selection, available action, working, partial failure, source unavailable, conflicting destination.
- Tokens: secondary/ghost actions, surface popover, pop shadow, danger confirmation.
- Accessibility: prefer native select and ordinary buttons initially; use a disclosure with aria-expanded if a menu is later added, never a hover-only menu. Selection count announced, destructive actions require confirmation.
- Used on: S01,S13,S14. Component contract only in this phase; no fake export, file deletion or batch mutation control is shipped in the specimen.

### Notices, toast and empty state
- Variants: success, warning, error, neutral; persistent actionable notice; transient nonessential confirmation; empty collection and no search results.
- States: visible/dismissed, action available/disabled. Important errors and unsaved work must remain persistent; they never disappear only because a timer expires.
- Tokens: status foreground/soft surface pairs; toast surface/text/border-input; headings 20/28, explanation 14/24.
- Accessibility: role=status polite for nonurgent feedback; role=alert only for errors requiring immediate attention in production. Toast cannot be the sole record of an outcome. Empty state supplies one clear next action.
- Used on: all screens. Demo toast lasts seven seconds; persistent error/unsaved/model-empty cards also shown.

## Verification and remaining acceptance

Completed: 49 declared contrast pairs, zero AA failures; native WebKit desktop visual review; 520 px browser overflow check after fix; tab keyboard navigation; source modal Escape and focus return; historical edit disabled; no-result search; selecting two files displays accepted extension and rejected type; no browser console errors observed during those checks. File content was not read or sent anywhere. Drag handling exists in code but a real OS drag gesture, oversize-file UI, minimum 320 px layout and screen-reader output were not independently qualified.

Proof screenshots are private workspace outputs under `outputs/traccia-design/`, outside Git. No Plaud screenshot or user lecture is included. Next: `/replica-build`, integrating these primitives gradually into Traccia while keeping original audio, manual note protections and English/Italian catalogs intact.
