"""App settings — per-agent models, theme accent, API credentials.

Saving credentials reconfigures the LLM client immediately (no restart needed).
"""

import asyncio
import os
import signal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
import llm
from models import AppSettings

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
async def get_settings() -> AppSettings:
    stored = await db.get_settings_json()
    settings = AppSettings.model_validate(stored) if stored else AppSettings()
    # Show the EFFECTIVE credentials (including .env fallbacks), not blanks —
    # the UI displays exactly what the pipeline will use.
    key, base = llm.current_credentials()
    if not settings.api_key:
        settings.api_key = key
    if not settings.base_url:
        settings.base_url = base
    return settings


@router.put("/settings")
async def put_settings(body: AppSettings) -> AppSettings:
    await db.put_settings_json(body.model_dump())
    llm.configure(body.api_key, body.base_url)
    return body


class FetchModelsIn(BaseModel):
    base_url: str = ""   # draft values from the Settings form (may be unsaved)
    api_key: str = ""


@router.post("/models/fetch")
async def fetch_models(body: FetchModelsIn):
    """List model ids from the provider; falls back to OpenRouter's public list."""
    saved_key, saved_base = llm.current_credentials()
    base = (body.base_url or saved_base).rstrip("/")
    key = body.api_key or saved_key

    candidates = [f"{base}/models"]
    if "openrouter" not in base:
        candidates.append("https://openrouter.ai/api/v1/models")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as http:
        for url in candidates:
            try:
                headers = {"Authorization": f"Bearer {key}"} if key else {}
                response = await http.get(url, headers=headers)
                data = response.json()
                items = data.get("data", data) if isinstance(data, dict) else data
                ids = sorted({m["id"] for m in items
                              if isinstance(m, dict) and m.get("id")})
                if ids:
                    return {"models": ids, "source": url}
            except Exception:
                continue
    raise HTTPException(
        502, "Could not fetch a model list from the provider — check the URL and key")


@router.post("/shutdown")
async def shutdown():
    """Stop the local server (wired to the power button in the UI)."""
    async def _exit() -> None:
        await asyncio.sleep(0.4)          # let the response flush first
        try:                              # flush WAL so no committed write can be lost
            await db.conn().execute("PRAGMA wal_checkpoint(FULL)")
        except Exception:
            pass
        signal.raise_signal(signal.SIGINT)  # graceful uvicorn shutdown
        await asyncio.sleep(6)
        os._exit(0)                        # hard fallback if graceful hangs
    asyncio.get_running_loop().create_task(_exit())
    return {"ok": True, "message": "server shutting down"}
