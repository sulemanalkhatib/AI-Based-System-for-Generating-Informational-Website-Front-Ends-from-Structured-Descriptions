# AI Website Generator v2 — Multi-Agent Edition

A university project: describe your business in a chat interview, then watch a
team of AI agents build a complete multi-page website — live.

```
you ──► Interviewer ──► ┌ Copywriter ┐          ┌ page ∥ page ∥ page ┐
        (chat brief)    │     ∥      │ ──► CSS ─│        ∥           │ ──► Recheck ──► Audit
                        └ Designer   ┘          └     site script    ┘    (fixes)     (scores)
                          in parallel                 in parallel
```

- **Copywriter** owns every word; **Designer** owns the whole look — they run
  **in parallel** and hand the builder strict JSON specs.
- **Builders** generate the shared stylesheet first, then **every page in
  parallel**, plus the shared script.
- **Review loop** — the **Audit** scores the site first (12 deterministic
  machine checks + an LLM review, 0–100, shown in the UI); if it finds problems
  the **Recheck** agent fixes exactly those findings; then we re-audit. It
  repeats until the audit reports **zero open issues**, or the site stops
  measurably improving (weighted by issue severity, tolerating one flat pass),
  or a 4-pass cap is hit — so it always terminates.

The app around it: persistent chat sessions (SQLite), a live preview that
assembles page-by-page during the build, a Monaco code editor (edits refresh
the preview and bump file revisions), zip / Desktop export, and per-agent model
settings — in a dark, single-accent UI.

**Edit mode:** once a build finishes, the same chat becomes the site editor.
Ask in plain language — "change the phone number", "make the hero bolder",
"add a gallery page" — and an editor agent (running on the builder's model)
applies precise file changes, the preview refreshes live, and each touched
file's revision ticks up in the Code tab.

## Requirements

- Python 3.12+ (tested on 3.14)
- Node.js 18+ (tested on 22)
- An OpenRouter-compatible API key in `backend/.env` (or the old
  `website-generator/.env` — it is picked up automatically):
  `OPENROUTER_API_KEY=sk-...`

## Run it

**Double-click `start.bat`** — it launches the whole app (one process) and
opens http://localhost:8000. Use **`start-mock.bat`** for free demo mode: every
agent returns canned data with realistic delays — perfect for rehearsing
without spending tokens (chat anything, then say `go`).

First-time setup only:

```powershell
cd backend;  pip install -r requirements.txt
cd frontend; npm install; npm run build
```

### Development mode (hot reload)

Terminal 1: `cd backend; python -m uvicorn app:app --port 8000 --reload`
Terminal 2: `cd frontend; npm run dev` → http://localhost:5173 (proxies /api).
After frontend changes, `npm run build` refreshes what `start.bat` serves.

## Demo script

**3-minute version (mock):** start backend with `MOCK_LLM=1` → new session →
type anything → type `go` → the Agents tab opens itself: copywriter + designer
pulse side-by-side, then three page cards + the script build in parallel, the
preview assembles page-by-page, recheck bumps `index.html` to **r2**, audit
scores the site. Switch device widths in Preview, edit a headline in Code and
watch the preview refresh, open Audit for the score ring.

**Full version (real API):** same flow without `MOCK_LLM`; answer the
interviewer's questions (it suggests pages). Builds take a few minutes —
narrate the agent cards while they run. Finish with "Save to Desktop" in the
Code tab, which opens the exported folder.

## Settings

Sidebar → Settings:

- **Provider** — base URL + API key (stored in the local DB; empty fields fall
  back to `backend/.env`). Applied immediately, no restart needed.
- **Fetch models** — pulls the provider's model list (falls back to
  OpenRouter's public catalog) and fills every agent's dropdown.
- **Models per agent** — "auto" routes automatically; pin a concrete id for
  builder + recheck for the most consistent code.
- **Agent switches** — stop any pipeline agent; the build skips it (card shows
  "skipped") and continues using a deterministic built-in fallback: fallback
  copy/design specs, template-rendered pages, machine-checks-only audit.
- **Stock photography** — on by default: generated sites use real stock photos
  (deterministic Picsum URLs) for heroes, galleries and story sections, layered
  under brand-color gradient overlays. Turn it off to build with brand-gradient
  SVG placeholders only — no external image URLs, so exported sites work fully
  offline. Either way, a small script swaps any photo that fails to load for a
  branded gradient, so an offline export never shows a broken-image icon.
- **Accent color** — the single saturated color used across the app.

The **Stop server** button at the bottom of the sidebar shuts the local server
down cleanly from the UI.

**Visual audit** (Settings → Visual audit, off by default) makes the auditor
screenshot the rendered home page and score the design from what it actually
looks like — not just the code. It needs a vision-capable audit model (e.g.
`openai/gpt-4o-mini`) and Playwright installed once on the server:

```powershell
pip install playwright
playwright install chromium
```

If Playwright isn't installed, the audit silently falls back to the code-only
review, so the build never breaks. It's slower and costs a little more per build.

**Developer mode** (Settings → Developer mode, on by default) adds a live **Logs**
tab: a timestamped console of every agent request — which model it called, chars
in/out, response time, token usage, retries and continuations, and every file
write — colour-coded per agent. It's the fastest way to see *where a slow build
is spending its time* (each request line shows its duration).

## Tests

```powershell
cd backend
python -m pytest tests -q
```

Covers the output parsers (fences, recheck `---FILE---` blocks, truncation),
the deterministic audit checks against a clean and a broken fixture site, and
the DB layer (revisions, cascades).

## Layout

```
start.bat            one-click launcher (start-mock.bat = free demo mode)
backend/             FastAPI + agents + orchestrator + SQLite (data/app.db)
frontend/            Vite + React + Tailwind v4 + zustand + Monaco
```

Key backend files: `orchestrator.py` (the pipeline + SSE events),
`agents/` (one file per agent), `prompts/` (contracts that keep
parallel-generated files coherent), `checks.py` (machine checks),
`events.py` (replay-safe event bus).

## Troubleshooting

- **Port already in use** — kill the old process:
  `Get-NetTCPConnection -LocalPort 8000 | % { Stop-Process -Id $_.OwningProcess -Force }`
- **`pip install` fails on very new Python** — install Python 3.12
  side-by-side and use `py -3.12 -m pip ...` / `py -3.12 -m uvicorn ...`.
- **Rate limits (429) mid-build** — agents retry automatically with backoff;
  free-tier OpenRouter caps are low, so mock mode is your friend on demo day.
- **Interviewer replies with "the model returned an empty response" (or a build
  that never writes a file)** — the selected model is returning nothing, which
  free/credit-less OpenRouter models do on the demanding brief-and-build turns.
  Add credits and pin a real model (Settings), or use `start-mock.bat` to see the
  full flow offline. (The app never shows a blank bubble now — it explains this.)
- **Recheck/audit extremely slow (5–10 min) or timing out** — with zero
  OpenRouter credits, "auto" can only route to slow free-tier models, and
  recheck is the biggest call (the whole site in one prompt). Fix: add ~$10
  of credits, then pin a fast model (e.g. `openai/gpt-4o-mini`) for
  builder + recheck in Settings — a full
  build costs a few cents and recheck drops to under a minute. The pipeline
  still completes on free models: recheck gives up gracefully after its
  retries and the audit falls back to machine checks if needed.
