"""Designer agent — ProjectBrief → DesignSpec (owns the complete visual identity)."""

import asyncio
import re

import config
import llm
from models import DesignSpec, ProjectBrief
from prompts.designer import DESIGNER_PROMPT

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_REQUIRED_KEYS = ("primary", "primary_dark", "accent", "bg", "surface", "text", "muted")


def _normalize(spec: DesignSpec, brief: ProjectBrief) -> DesignSpec:
    """Backfill any missing/invalid palette entries from the safe fallback."""
    safe = DesignSpec.fallback(brief).palette
    for key in _REQUIRED_KEYS:
        value = spec.palette.get(key, "")
        if not _HEX_RE.match(value or ""):
            spec.palette[key] = safe[key]
    return spec


async def run(brief: ProjectBrief, *, model: str,
              on_status: llm.StatusFn | None = None) -> DesignSpec:
    if config.MOCK_LLM:
        from mock import fixtures
        await asyncio.sleep(1.1)
        return fixtures.design_spec(brief)

    spec = await llm.complete_json(
        DesignSpec, DESIGNER_PROMPT, brief.model_dump_json(indent=2),
        model=model, max_tokens=config.SPEC_MAX_TOKENS,
        temperature=0.8, on_status=on_status)
    return _normalize(spec, brief)
