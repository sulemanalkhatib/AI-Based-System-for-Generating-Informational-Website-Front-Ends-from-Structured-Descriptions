"""FastAPI entry point — run with:  uvicorn app:app --reload --port 8000"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
import db
from routes import builds, chat, export, files, preview, sessions, settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await db.init_db()
    # A build can't survive a restart — mark any orphaned "running" rows failed
    await db.conn().execute("UPDATE builds SET status='failed' WHERE status='running'")
    await db.conn().commit()
    # Apply saved credential overrides so Settings survive restarts
    stored = await db.get_settings_json()
    if stored:
        import llm
        llm.configure(stored.get("api_key", ""), stored.get("base_url", ""))
    yield
    await db.close_db()


app = FastAPI(title="Website Generator v2", lifespan=lifespan)

# The Vite dev proxy avoids CORS entirely; this is the belt-and-braces fallback
# so the frontend can also talk to :8000 directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(builds.router)
app.include_router(files.router)
app.include_router(preview.router)
app.include_router(export.router)
app.include_router(settings.router)

if config.DEV_ROUTES:
    from routes import dev
    app.include_router(dev.router)


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "mock_llm": config.MOCK_LLM,
        "api_key_present": bool(config.OPENROUTER_API_KEY),
        "base_url": config.OPENROUTER_BASE_URL,
    }


# Serve the built frontend (frontend/dist) so one process runs the whole app.
# Registered last: /api/* and /preview/* routes above always win.
_dist = config.ROOT_DIR / "frontend" / "dist"
if _dist.exists():
    from fastapi.staticfiles import StaticFiles

    class _FrontendStatic(StaticFiles):
        """Serve the SPA, but NEVER let the browser cache the HTML shell — otherwise
        after a rebuild the browser keeps showing a stale index.html that points at
        asset hashes which no longer exist (blank page). Hashed assets in /assets are
        content-addressed and stay cacheable; only the HTML is marked no-cache."""

        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            media = response.headers.get("content-type", "")
            if path in ("", ".", "/") or path.endswith(".html") or media.startswith("text/html"):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            return response

    app.mount("/", _FrontendStatic(directory=_dist, html=True), name="frontend")
