"""Interviewer agent — one chat turn; detects READY_TO_BUILD and extracts the brief."""

import asyncio
import re
from typing import Awaitable, Callable

import config
import llm
from models import ProjectBrief
from prompts.interviewer import INTERVIEWER_PROMPT

TokenFn = Callable[[str], Awaitable[None]]

# Held-back tail so the sentinel/brief can never leak into the streamed UI text.
# Must comfortably exceed len("READY_TO_BUILD") plus surrounding whitespace.
_TAIL_CHARS = 48

# Sentinel must appear alone on its own line (same proven pattern as v1)
SENTINEL_RE = re.compile(r"^\s*READY_TO_BUILD\s*$", re.MULTILINE)
BRIEF_RE = re.compile(r"---BRIEF---(.*?)---END BRIEF---", re.DOTALL)

# Shown instead of a blank bubble when the model returns nothing — almost always
# a rate-limited or credit-less free model rather than an app fault.
EMPTY_REPLY_MSG = (
    "The model returned an empty response. That usually means the selected model is "
    "rate-limited or unavailable — very common on free models when the OpenRouter "
    "account has no credits. Please send your message again, or open Settings to add "
    "credits and pin a specific model (e.g. openai/gpt-4o-mini).")

# Shown when the model tried to finish but its brief JSON was malformed.
BRIEF_FORMAT_MSG = (
    "I have your details, but the model returned the final brief in a broken format "
    "(free/rate-limited models often mangle it). Please send \"go\" once more, or pin a "
    "stronger model for the interviewer in Settings and try again.")


def _lenient_json(raw: str) -> str:
    """Repair the JSON quirks free models commonly emit (comments, trailing commas)."""
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
    raw = re.sub(r"//[^\n]*", "", raw)
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    return raw


def extract_brief(text: str) -> ProjectBrief | None:
    match = BRIEF_RE.search(text)
    if not match:
        return None
    try:
        raw = llm.extract_json(match.group(1))
    except ValueError:
        return None
    for candidate in (raw, _lenient_json(raw)):
        try:
            return ProjectBrief.model_validate_json(candidate)
        except Exception:
            continue
    return None


def _finish(text: str) -> tuple[str, ProjectBrief | None]:
    """Detect the build handoff and extract the brief.

    The handoff is marked by READY_TO_BUILD and/or the ---BRIEF--- block. Weaker
    models sometimes emit the brief without the exact sentinel line, so the brief
    block itself counts as a valid handoff — and we mask everything from whichever
    marker appears first so the raw JSON never shows in chat.
    """
    if not text.strip():
        return EMPTY_REPLY_MSG, None

    sentinel = SENTINEL_RE.search(text)
    brief_pos = text.find("---BRIEF---")
    markers = [p for p in (sentinel.start() if sentinel else None,
                           brief_pos if brief_pos != -1 else None) if p is not None]
    if not markers:
        return text, None  # still interviewing — nothing to hand off

    brief = extract_brief(text)
    if brief is None:
        return BRIEF_FORMAT_MSG, None

    visible = text[:min(markers)].strip()
    if not visible:
        visible = "Perfect — I have everything I need. The team is starting your build now!"
    return visible, brief


def _build_messages(history: list[dict], user_message: str) -> list[dict]:
    messages = [{"role": "system", "content": INTERVIEWER_PROMPT}]
    for entry in history:
        if entry.get("role") in ("user", "assistant") and entry.get("content"):
            messages.append({"role": entry["role"], "content": entry["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


async def run_turn(history: list[dict], user_message: str,
                   *, model: str) -> tuple[str, ProjectBrief | None]:
    """Returns (visible_reply, brief). brief is None until the interview finishes."""
    if config.MOCK_LLM:
        from mock import fixtures
        return await fixtures.interviewer_turn(history, user_message)

    text = await llm.complete_chat(_build_messages(history, user_message), model=model,
                                   max_tokens=config.INTERVIEWER_MAX_TOKENS,
                                   temperature=0.7)
    return _finish(text)


async def run_turn_streaming(history: list[dict], user_message: str,
                             *, model: str, on_token: TokenFn,
                             ) -> tuple[str, ProjectBrief | None]:
    """Streaming variant: forwards visible tokens as they arrive while holding
    back a tail buffer so READY_TO_BUILD and the JSON brief never reach the UI.

    Returns the same (visible_reply, brief) as run_turn.
    """
    if config.MOCK_LLM:
        from mock import fixtures
        reply, brief = await fixtures.interviewer_turn(history, user_message)
        for i in range(0, len(reply), 12):  # chunked so the caret demo looks real
            await on_token(reply[i:i + 12])
            await asyncio.sleep(0.04)
        return reply, brief

    full = ""
    emitted = 0
    masked = False
    async for delta in llm.stream_chat(_build_messages(history, user_message),
                                       model=model,
                                       max_tokens=config.INTERVIEWER_MAX_TOKENS,
                                       temperature=0.7):
        full += delta
        if masked:
            continue
        sentinel = SENTINEL_RE.search(full)
        brief_marker = full.find("---BRIEF---")
        if sentinel or brief_marker != -1:
            cut = sentinel.start() if sentinel else brief_marker
            visible_target = full[:cut].rstrip()
            if len(visible_target) > emitted:
                await on_token(visible_target[emitted:])
                emitted = len(visible_target)
            masked = True
            continue
        safe = max(0, len(full) - _TAIL_CHARS)
        if safe > emitted:
            await on_token(full[emitted:safe])
            emitted = safe

    if not masked and len(full) > emitted:
        await on_token(full[emitted:])

    return _finish(full)
