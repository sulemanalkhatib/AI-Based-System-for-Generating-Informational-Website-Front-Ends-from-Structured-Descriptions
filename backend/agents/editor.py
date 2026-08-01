"""Editor agent — turns chat messages into precise file changes after a build.

Uses the editor's configured model, which defaults to the builder's model when
left on "auto" (an edit is builder-like work; see routes/chat.py). Output contract:
---REPLY--- for the user, then ---FILE: name--- blocks with complete files.
New .html pages are allowed (sanitized); everything else must already exist.
"""

import asyncio

import config
import llm
from models import CopyDeck, DesignSpec, ProjectBrief, safe_page_filename
from prompts.editor import EDITOR_PROMPT


def _safe_artifact_name(name: str, known_files: set[str]) -> str | None:
    name = name.strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    if name in known_files:
        return name
    # New files: only additional pages are allowed to appear out of thin air
    if name.endswith((".html", ".htm")) or "." not in name:
        return safe_page_filename(name)
    return None


def parse_editor_output(text: str, known_files: set[str]) -> tuple[str, dict[str, str], bool]:
    """Returns (reply, changed_files, truncated)."""
    text = llm.strip_fences(text)
    chunks = text.split("---FILE:")
    reply = chunks[0].replace("---REPLY---", "").strip()

    changed: dict[str, str] = {}
    truncated = False
    for i, chunk in enumerate(chunks[1:], start=1):
        header, sep, body = chunk.partition("---")
        if not sep:
            truncated = True
            continue
        filename = _safe_artifact_name(header, known_files)
        if filename is None:
            continue
        is_last = i == len(chunks) - 1
        end_index = body.find("---END FILE---")
        if end_index == -1:
            if is_last:
                truncated = True  # cut off mid-file — half a file is worse than none
                continue
            content = body
        else:
            content = body[:end_index]
        if content.strip():
            changed[filename] = content.strip() + "\n"
    return reply, changed, truncated


async def run(request: str, history: list[dict], brief: ProjectBrief | None,
              deck: CopyDeck | None, design: DesignSpec | None,
              files: dict[str, str], *, model: str,
              on_status: llm.StatusFn | None = None,
              ) -> tuple[str, dict[str, str]]:
    """Returns (reply_for_user, changed_files)."""
    if config.MOCK_LLM:
        await asyncio.sleep(1.4)
        changed = {}
        if "index.html" in files:
            edited = files["index.html"].replace("</h1>", " ★</h1>", 1)
            changed["index.html"] = edited.replace(
                "</body>", f"  <!-- edit applied: {request[:60]} -->\n</body>")
        return ("Done! As a demo edit I marked your home hero heading with a star. "
                "[mock] On the real API this would apply exactly what you asked for."), changed

    context_lines = "\n".join(
        f"{m['role']}: {m['content'][:300]}" for m in history[-6:]
        if m.get("role") in ("user", "assistant"))
    file_dump = "\n\n".join(
        f"===== {name} =====\n{content}" for name, content in files.items())
    user = (
        f"SITE BRIEF:\n{brief.model_dump_json(indent=2) if brief else 'n/a'}\n\n"
        f"COPY DECK:\n{deck.model_dump_json(indent=2) if deck else 'n/a'}\n\n"
        f"DESIGN SPEC:\n{design.model_dump_json(indent=2) if design else 'n/a'}\n\n"
        f"RECENT CONVERSATION:\n{context_lines or '(none)'}\n\n"
        f"CURRENT SITE FILES:\n{file_dump}\n\n"
        f"OWNER'S EDIT REQUEST:\n{request}")

    raw = await llm.complete_text(EDITOR_PROMPT, user, model=model,
                                  max_tokens=config.RECHECK_MAX_TOKENS,
                                  temperature=0.3, on_status=on_status,
                                  timeout=config.RECHECK_TIMEOUT_S)
    reply, changed, truncated = parse_editor_output(raw, set(files))
    if not reply:
        reply = ("Done — I've applied your change." if changed
                 else "I couldn't work out a concrete change from that — could you rephrase?")
    if truncated:
        reply += (" (One file came back incomplete and was not applied — "
                  "please ask me to try that part again.)")
    return reply, changed
