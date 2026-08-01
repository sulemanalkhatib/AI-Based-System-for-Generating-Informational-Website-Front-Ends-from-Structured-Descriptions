"""LLM plumbing shared by every agent.

- one AsyncOpenAI client (120s read timeout — the SDK can otherwise hang ~10 min)
- retries with exponential jitter on 429 / timeouts / 5xx
- continuation loop when finish_reason == "length" (long code files)
- JSON completion with fence-stripping, brace-salvage, and one repair round-trip
"""

import asyncio
import base64
import random
import re
import time
from typing import Awaitable, Callable, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel

import config

StatusFn = Callable[[str], Awaitable[None]]
M = TypeVar("M", bound=BaseModel)

_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

_client: AsyncOpenAI | None = None
# Runtime overrides from Settings (empty = use .env values)
_override_key = ""
_override_base_url = ""


def configure(api_key: str = "", base_url: str = "") -> None:
    """Apply Settings overrides and drop the cached client so they take effect."""
    global _client, _override_key, _override_base_url
    _override_key = (api_key or "").strip()
    _override_base_url = (base_url or "").strip().rstrip("/")
    _client = None


def current_credentials() -> tuple[str, str]:
    """(api_key, base_url) after applying Settings overrides over .env."""
    return (_override_key or config.OPENROUTER_API_KEY,
            _override_base_url or config.OPENROUTER_BASE_URL)


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key, base_url = current_credentials()
        if not api_key:
            raise RuntimeError(
                "No API key configured — set it in Settings or in backend/.env "
                "(OPENROUTER_API_KEY=...), or run with MOCK_LLM=1")
        _client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=config.LLM_TIMEOUT_S,
            default_headers={"HTTP-Referer": "website-generator-v2",
                             "X-Title": "Website Generator v2"},
        )
    return _client


def strip_fences(text: str) -> str:
    """Remove a leading ```lang fence and trailing ``` if the model added them."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def _with_retries(fn: Callable[[], Awaitable], on_status: StatusFn | None = None):
    delay = 2.0
    for attempt in range(config.LLM_MAX_RETRIES):
        try:
            return await fn()
        except _RETRYABLE as error:
            if attempt == config.LLM_MAX_RETRIES - 1:
                raise
            wait = random.uniform(0.5, delay)  # full jitter — avoids thundering herd on 429
            if on_status:
                await on_status(f"{type(error).__name__} — retrying in {wait:.1f}s")
            await asyncio.sleep(wait)
            delay = min(delay * 2, 30.0)


async def complete_chat(
    messages: list[dict],
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.7,
    on_status: StatusFn | None = None,
) -> str:
    """One chat completion over a full message list (used by the interviewer)."""
    in_chars = sum(len(m.get("content", "")) for m in messages)
    if on_status:
        await on_status(f"→ request to {model} · {in_chars:,} chars in · max_tokens {max_tokens:,}")
    t0 = time.monotonic()
    response = await _with_retries(
        lambda: client().chat.completions.create(
            model=model, messages=messages,
            max_tokens=max_tokens, temperature=temperature),
        on_status)
    text = response.choices[0].message.content or ""
    if on_status:
        await on_status(f"← {model} · {len(text):,} chars · "
                        f"{response.choices[0].finish_reason} · {time.monotonic() - t0:.1f}s")
    return text


async def stream_chat(
    messages: list[dict],
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.7,
    on_status: StatusFn | None = None,
):
    """Streaming chat completion — yields text deltas as they arrive."""
    stream = await _with_retries(
        lambda: client().chat.completions.create(
            model=model, messages=messages,
            max_tokens=max_tokens, temperature=temperature, stream=True),
        on_status)
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def complete_text(
    system: str,
    user: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.3,
    on_status: StatusFn | None = None,
    timeout: float | None = None,
) -> str:
    """System+user completion with automatic continuation on token-limit cutoff."""
    api = client().with_options(timeout=timeout) if timeout else client()
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    parts: list[str] = []
    for step in range(config.MAX_CONTINUATIONS + 1):
        in_chars = sum(len(m.get("content", "")) for m in messages)
        if on_status:
            kind = "continuation request" if step else "request"
            await on_status(f"→ {kind} to {model} · {in_chars:,} chars in · "
                            f"max_tokens {max_tokens:,}")
        t0 = time.monotonic()
        response = await _with_retries(
            lambda: api.chat.completions.create(
                model=model, messages=messages,
                max_tokens=max_tokens, temperature=temperature),
            on_status)
        choice = response.choices[0]
        text = choice.message.content or ""
        parts.append(text)
        usage = getattr(response, "usage", None)
        out_tok = getattr(usage, "completion_tokens", None) if usage else None
        if on_status:
            tok = f" · {out_tok:,} out-tok" if out_tok else ""
            await on_status(f"← {model} · {len(text):,} chars · {choice.finish_reason} · "
                            f"{time.monotonic() - t0:.1f}s{tok}")
        if choice.finish_reason != "length":
            break
        if on_status:
            await on_status("output hit the token limit — continuing…")
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content":
                         "Continue EXACTLY where you left off. Do not repeat anything "
                         "already written. Output only the remaining content, nothing else."})
    return "".join(parts)


def extract_json(text: str) -> str:
    """Salvage the outermost JSON object from model output."""
    text = strip_fences(text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return text[start:end + 1]


async def complete_json(
    model_cls: type[M],
    system: str,
    user: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.7,
    on_status: StatusFn | None = None,
    timeout: float | None = None,
) -> M:
    """JSON completion validated against a Pydantic model, with one repair round."""
    raw = await complete_text(system, user, model=model, max_tokens=max_tokens,
                              temperature=temperature, on_status=on_status,
                              timeout=timeout)
    try:
        result = model_cls.model_validate_json(extract_json(raw))
        if on_status:
            await on_status(f"✓ parsed valid {model_cls.__name__}")
        return result
    except Exception as first_error:
        if on_status:
            await on_status(f"{model_cls.__name__} JSON invalid — asking the model to repair it")
        repair_user = (
            f"The JSON you produced failed validation with this error:\n{first_error}\n\n"
            f"Return ONLY the corrected JSON object — no commentary, no code fences.\n\n"
            f"Your previous output:\n{raw[:12000]}")
        raw2 = await complete_text(system, repair_user, model=model,
                                   max_tokens=max_tokens, temperature=0.2,
                                   on_status=on_status, timeout=timeout)
        return model_cls.model_validate_json(extract_json(raw2))


async def complete_json_image(
    model_cls: type[M],
    system: str,
    user: str,
    image_png: bytes,
    *,
    model: str,
    max_tokens: int,
    temperature: float = 0.3,
    on_status: StatusFn | None = None,
    timeout: float | None = None,
) -> M:
    """JSON completion that also sees an image (used by the visual audit).

    Requires a vision-capable model. Falls back to a text-only repair round if the
    first response fails validation.
    """
    api = client().with_options(timeout=timeout) if timeout else client()
    b64 = base64.b64encode(image_png).decode()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": [
            {"type": "text", "text": user},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]},
    ]
    if on_status:
        await on_status(f"→ request to {model} · with rendered screenshot "
                        f"({len(image_png) // 1024} KB)")
    t0 = time.monotonic()
    response = await _with_retries(
        lambda: api.chat.completions.create(
            model=model, messages=messages,
            max_tokens=max_tokens, temperature=temperature),
        on_status)
    raw = response.choices[0].message.content or ""
    if on_status:
        await on_status(f"← {model} · {len(raw):,} chars · {time.monotonic() - t0:.1f}s")
    try:
        return model_cls.model_validate_json(extract_json(raw))
    except Exception as error:
        if on_status:
            await on_status(f"{model_cls.__name__} JSON invalid — repairing")
        repair = (f"The JSON you produced failed validation:\n{error}\n\n"
                  f"Return ONLY the corrected JSON object.\n\n{raw[:10000]}")
        raw2 = await complete_text(system, repair, model=model, max_tokens=max_tokens,
                                   temperature=0.2, on_status=on_status, timeout=timeout)
        return model_cls.model_validate_json(extract_json(raw2))
