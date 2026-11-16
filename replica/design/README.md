# Traccia design workshop

An isolated component catalog, not a new production UI or a working AI demo. Original Traccia assets, system fonts, synthetic text, no external libraries or network calls. Nothing is uploaded or saved.

From the repository root:

```sh
python3 replica/design/build_tokens.py
python3 ~/.codex/skills/replica-design/contrast.py replica/design/tokens.json
python3 -m http.server 8782 --bind 127.0.0.1
```

Open **http://127.0.0.1:8782/replica/design/**. The static server binds to localhost only. Stop it with Ctrl+C. Serving from the repository root lets the catalog reuse the existing original Traccia SVG; the design folder alone is not a standalone asset bundle.

- `tokens.json`: role-based colors, type, layout, spacing, motion and allowed contrast pairs.
- `tokens.css`: generated CSS variables, also synchronized to `aulalocale/web/tokens.css` by the builder.
- `tailwind.config.cjs`: optional Tailwind 3 mapping; not a new application dependency.
- `primitives.css`, `primitives.js`, `index.html`: native accessible primitives and interactive specimens.
- `components.md`: component states, measurement provenance, integration boundaries and verification limits.
- `contrast-report.txt`: 49 declared combinations, zero AA failures; palette validation, not full WCAG certification.

Existing application routes and archive schema are unchanged. Do not confuse selected files in the catalog with imported or validated lecture recordings. Production integration follows replica-build and the architecture milestones.
