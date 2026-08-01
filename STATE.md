# Project State — AI Multi-Agent Website Generator (v2)

Living status doc. Last updated: 2026-07-15.

---

## 1. What this is

A university project that turns a chat interview into a complete, multi-page
website through a team of AI agents, with a premium dark, single-accent UI.
Rebuilt from a Gradio prototype (v1, now deleted) into a FastAPI backend + a
React/Vite/Tailwind frontend.

**Pipeline:**
```
interviewer (chat)
   → [ copywriter ∥ designer ]        (parallel spec agents, strict JSON handoffs)
   → builder: shared CSS, then [ pages ∥ script.js ]   (parallel per-file)
   → review loop: audit → recheck → re-audit … until clean
```
After a build, the same chat becomes an **editor** — plain-language change requests
are applied to the files live.

---

## 2. How to run

- **One click:** `start.bat` (real API) or `start-mock.bat` (free, canned demo data).
  Backend serves the built frontend, so it's a single process on http://localhost:8000.
- **First-time setup:** `cd backend && pip install -r requirements.txt`,
  then `cd frontend && npm install && npm run build`.
- **Dev with hot reload:** `uvicorn app:app --port 8000 --reload` + `npm run dev`
  (Vite on 5173, proxies /api + /preview). Run `npm run build` after FE changes so
  start.bat serves them.
- **Tests:** `cd backend && python -m pytest tests -q` (27 passing).
- **Optional visual audit:** `pip install playwright && playwright install chromium`.

**Provider:** any OpenAI-compatible endpoint via `OPENROUTER_BASE_URL` (defaults to
`https://openrouter.ai/api/v1`), key in `backend/.env` (or overridden in Settings). Pin
`openai/gpt-4o-mini` per agent for fast, cheap builds; `"auto"` routing is slow/unreliable.

---

## 3. Architecture

### Backend (`backend/`)
- `app.py` — FastAPI app, CORS, routers, lifespan (DB init, mark orphaned builds
  failed, serve `frontend/dist`).
- `config.py` — env, paths, timeouts, MOCK_LLM, SELF_URL.
- `db.py` — aiosqlite (WAL, FK on), one shared connection; sessions / messages /
  builds / artifacts (revisioned) / settings.
- `models.py` — Pydantic contracts: ProjectBrief, CopyDeck, DesignSpec, AuditReport,
  AppSettings; `safe_page_filename` (Windows reserved-name guard).
- `llm.py` — AsyncOpenAI factory + Settings credential override; retry w/ jitter;
  continuation-on-length; JSON complete + repair; `complete_json_image` (vision);
  per-request status logging.
- `events.py` — replay-safe per-run event bus (history + subscriber queues, monotonic seq).
- `orchestrator.py` — the pipeline; parallel fan-outs, per-page semaphore, review loop,
  all SSE emission; `_files_for_recheck` scoping.
- `agents/` — interviewer, copywriter, designer, builder (css/page/js), rechecker, auditor, editor.
- `prompts/` — one prompt per agent + shared `CLASS_CONTRACT`.
- `checks.py` — 12 deterministic machine checks (structure, links, forbidden APIs,
  forms, animations, alt text, **image lazy-load + dimensions**, **WCAG AA contrast computed from :root**).
- `fallback.py` — deterministic HTML/CSS/JS renderer (mock mode + failed-page self-heal).
- `writer.py` — disk export, clean_name, above-the-fold JS injection.
- `vision.py` — optional Playwright screenshot (lazy import, graceful None fallback).
- `routes/` — sessions, chat (interview OR edit routing), builds (+ cancel), files,
  preview, export, settings (+ fetch-models, shutdown), dev (seed-brief).

### Frontend (`frontend/src/`)
- `state/store.ts` — single zustand store; SSE handlers mutate it from outside React.
- `lib/{api,sse,types}.ts` — REST wrappers, EventSource clients (seq-dedupe), TS types.
- `components/` — sidebar (sessions), chat (list/composer, streaming caret),
  workspace (tabs: Preview / Code / Agents / Audit / Logs), preview (sandboxed iframe +
  device toggles), code (Monaco + file tree), agents (timeline + cards), audit (score ring +
  issues), console (dev logs), settings (modal).
- `styles/tokens.css` — dark single-accent tokens; Tailwind v4.

---

## 4. Done (features & fixes)

**Core product**
- Multi-agent pipeline with visible parallelism (copywriter ∥ designer; pages ∥ js).
- Persistent sessions & message history; auto-titled from first prompt.
- SSE streaming; replay-safe bus; reconnect-safe (seq dedupe); DB replay reconstructs a
  finished build so all agent cards show done after reload.
- Live preview: sandboxed iframe (`allow-scripts allow-forms`, never `allow-same-origin`),
  per-build backend route, device toggles (375/768/full), refresh, open-in-new-tab,
  assembles page-by-page during build.
- Monaco editor: file tree, revision badges, debounced save → revision bump → preview refresh.
- Export: zip download + save-to-Desktop folder (opens on Windows).
- **Edit mode:** after a build, chat routes to an editor agent that applies precise file
  changes (can add pages); preview refreshes live.

**Visual richness (2026-07-14)**
- **Imagery:** copywriter emits a concrete photo `image` subject per section/card (also
  the alt text); designer owns an `imagery` treatment direction. Builder renders photo
  heroes (`.hero.has-photo` + `hero-bg` + brand `hero-overlay`), `.media`/`.media-row`
  figures, `.gallery` grids and `.team` photos. Image URLs are deterministic
  `picsum.photos/seed/<slug>/W/H`. Every `<img>` carries alt + width/height + loading
  (hero eager, rest lazy) — enforced by a new machine check.
- **Offline safety:** `AppSettings.use_photos` (default on) toggles between real photos
  and pure brand-gradient SVG fills (`.media--gradient`, zero external URLs). Regardless,
  `script.js` swaps any failed photo for an inline brand-gradient SVG data-URI, so exported
  offline sites never show a broken-image icon. Threaded orchestrator → `build_page` → `fallback.render_page`.
- **Richer colour:** gradient `.btn-primary` with brand-tinted shadows, one gradient-text
  heading per page, brand-tinted card/media shadows, gradient (not flat) bold sections.
  Designer prompt got a "COLOR APPLICATION" section (gradients, derived tints/shades,
  accent-as-light) + a full-bleed photo hero default.
- **More animations:** reveal set expanded to `.fade-in/.slide-up/.slide-left/.slide-right/
  .zoom-in` (one generalized IntersectionObserver, staggered), CSS hero entrance, count-up
  `stats` sections, a subtle ambient gradient drift on the bold section, image hover-zoom —
  all behind a `prefers-reduced-motion` guard.
- Mock fixtures showcase it (photo hero, stats, gallery) so **mock-mode demos** render the
  new look with no API spend.

**Review loop**
- Audit-first: 12 machine checks (ground truth) + LLM report (scored /100).
- Recheck fixes ONLY the audit's findings (fed the issue list), then re-audit.
- **Stops when the audit's `issues` list is empty**, or weighted-severity progress
  stalls for two consecutive passes, or the `MAX_FIX_PASSES=4` cap is hit. Machine
  failure / build note never gets skipped. (See §5 for the weighted-progress rationale
  that replaced the old raw-count drift guard.)
- Mock demonstrates it: 88 (3 issues) → recheck → 97 (0 issues) → stop.

**Settings**
- Per-agent model selection (incl. the post-build **editor** — its dropdown defaults to
  "auto" = follow the builder's model) + **Fetch models** (provider list, OpenRouter fallback).
- Provider base URL + API key (show effective values, applied without restart).
- Per-agent **stop/skip** toggles (pipeline skips → deterministic fallback).
- **Developer mode** (Logs tab: per-request model, chars in/out, duration, tokens,
  retries, file writes — attributed to the real agent).
- **Visual audit** (off by default): Playwright screenshots the rendered home page and
  the auditor scores design from pixels; force-reveals animations before capture;
  graceful fallback if Playwright absent.
- Accent color.

**Reliability & UX**
- **Smart composer placeholder:** the message field reads the interviewer's latest
  question and suggests an example answer (name → "e.g. Ember & Oak", colors →
  "e.g. deep charcoal, warm cream…", confirm turn → "Type 'go' to start…"). Pure
  client-side heuristic (`lib/placeholder.ts`, keyword→example map), no LLM call;
  falls back to "Describe your business…". Edit mode keeps its own placeholder.
- Interviewer streaming with sentinel-masking tail buffer.
- Empty-response guard (never a blank bubble) + malformed-brief message.
- **Brief handoff works even without the READY_TO_BUILD sentinel** (masks from the
  `---BRIEF---` marker; raw JSON never leaks into chat).
- Lenient brief JSON (strips trailing commas / comments).
- **Stop button:** cancels a running build (`task.cancel` → graceful "stopped").
- Prompt quality pass: worked examples (copywriter, designer), fixed type/spacing scale
  (CSS), self-check checklists (builders), checkable contrast heuristics (designer),
  literal `section_rhythm`, `primary_goal` + `references` captured in the brief.
- Timeline UI redesign: aligned rail, state-coloured nodes, no dangling line.
- Single-process serving; start.bat/start-mock.bat; Stop-server button; graceful shutdown
  (WAL checkpoint); orphaned builds marked failed on startup.
- Fixes: composer focus outline removed, focus retained after send, longer recheck/audit
  timeouts (300s/240s), v1 folder removed (key moved to backend/.env).

---

## 5. Known issues & design tensions

- **Copy-is-law vs audit copy suggestions:** the auditor may flag copy wording, but
  recheck is forbidden to rewrite copy — so those issues can never be cleared by the loop
  (they persist as final warnings). Use edit mode to fix them manually.
- **Audit is stochastic:** it rarely reaches a literal zero issues. The loop now measures
  progress by **weighted severity** (critical 100 / warning 10 / info 1, failing machine
  checks = 100) instead of raw issue count, and tolerates ONE non-improving pass before
  stopping (two in a row ⇒ stuck), capped at MAX_FIX_PASSES=4. This pushes further than the
  old raw-count drift guard, which bailed the instant the count didn't strictly drop —
  masking real progress when a fixed warning was replaced by a fresh info nit. Copy-law
  paraphrase nits still can't be cleared by recheck (see below), so they cap the ceiling;
  90s scores with 1–2 minor warnings are normal and fine.
- **Recheck often gets the full site:** `_files_for_recheck` sends only flagged files +
  css/js by default, but any nav/menu/link/site-wide issue triggers sending everything —
  and menu/nav findings are common, so full-site rechecks happen often. The **editor**
  always gets the full site.
- **Provider limits:** on a credit-less/free account, agents are slow and can return empty
  responses (build never writes a file, or interviewer returns nothing). Fix = credits +
  pinned fast model. (Guards now make failures explanatory, not silent.)
- **Test-env only:** MCP screenshot tool intermittently times out (not a product issue);
  Windows console (cp1256) can't print some unicode in dev scripts.

---

## 6. Future work (offered, not yet done)

Prioritized; each is a self-contained change.

1. **Resolve the copy tension** (small): either let recheck apply the audit's *suggested*
   copy fixes, or stop the audit from raising copy-wording as a fixable warning — so the
   loop isn't chasing an issue it structurally can't clear.
2. **Smarter/looser loop termination** (partly DONE 2026-07-15): now weighted-by-severity
   with a one-pass stall tolerance and a 4-pass cap (see §5). Still open: track *which*
   specific issues persist across passes (vs. just weighted totals), and/or a
   user-configurable pass cap.
3. **Structured JSON output** (medium, reliability): use `response_format: json_schema`
   for copywriter / designer / audit on capable models — eliminates malformed-spec and
   empty-response failures and the repair round-trips. NOT for the HTML/CSS/JS blobs.
4. ~~**Stock imagery**~~ — **DONE (2026-07-14)**, see §4 "Visual richness". Photos +
   SVG fallback, behind a "Stock photography" toggle; topical relevance is limited by
   Picsum being seeded-random — swapping the base URL to an Unsplash/LoremFlickr key
   would make photos subject-accurate.
5. **Vision audit enhancements** (medium): screenshot multiple pages and a mobile viewport,
   not just the desktop home page; surface the screenshot in the Audit tab.
6. **Per-agent time summary** (small): a "copywriter 4s · designer 4s · builder 22s ·
   recheck 41s · audit 6s" line at the end of a build so the slowest stage is obvious.
7. **Stalled-build banner** (small): if no file is written within ~60s, hint that the model
   is slow (rate-limited free tier) and to pin a fast model.
8. **Multi-page vision / broader audits, image alt-quality, Lighthouse-style perf checks**
   (larger, later).

---

## 7. Key file map (for quick edits)

- Change agent behavior → `backend/prompts/*.py`
- Pipeline order / loop / stop conditions → `backend/orchestrator.py`
- Deterministic checks → `backend/checks.py`
- Which files recheck sees → `_files_for_recheck` in `orchestrator.py`
- Interview → build handoff / brief parsing → `backend/agents/interviewer.py`
- Edit-mode routing → `backend/routes/chat.py`
- Settings fields → `backend/models.py` (AppSettings) + `frontend/.../SettingsModal.tsx`
- Pipeline visualization → `frontend/src/components/agents/AgentPipeline.tsx`
- Dev logs → `frontend/src/components/console/ConsolePane.tsx` + `lib/sse.ts`
