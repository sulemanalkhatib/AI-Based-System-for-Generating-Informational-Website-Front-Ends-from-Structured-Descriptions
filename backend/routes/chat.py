"""Chat: POST a message → interviewer OR editor runs in the background.

Routing: before a build exists the chat is the interview; once the session has
a completed build with files, the same chat becomes the site editor — messages
turn into file edits applied to the latest build.
"""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import db
import events
import orchestrator
import writer
from agents import editor, interviewer
from models import CopyDeck, DesignSpec, ProjectBrief

router = APIRouter(tags=["chat"])


class MessageIn(BaseModel):
    content: str


async def _run_edit_turn(session_id: str, build: dict, content: str,
                         history: list[dict], bus, settings) -> None:
    build_id = build["id"]
    files = await db.get_build_files(build_id)

    if not settings.is_enabled("builder"):
        reply = ("The builder agent is currently stopped in Settings, so I can't "
                 "apply edits — switch it back on and ask again.")
        await db.add_message(session_id, "assistant", reply, agent="editor")
        await bus.emit("message_done", {"content": reply})
        return

    async def on_status(text: str) -> None:
        await bus.emit("agent_status", {"agent": "editor", "text": text})

    await on_status("Reading your site…")

    def _load(model_cls, key):
        try:
            return model_cls.model_validate_json(build[key]) if build.get(key) else None
        except Exception:
            return None

    # Editor has its own model slot; left on "auto" it follows the builder's model
    # (an edit is builder-like work), so existing setups behave exactly as before.
    editor_model = settings.model_for("editor")
    if editor_model == "auto":
        editor_model = settings.model_for("builder")

    reply, changed = await editor.run(
        content, history,
        _load(ProjectBrief, "brief_json"),
        _load(CopyDeck, "copy_json"),
        _load(DesignSpec, "design_json"),
        files,
        model=editor_model,
        on_status=on_status)

    for filename, new_content in changed.items():
        if filename == "script.js":
            new_content = writer.inject_above_fold(new_content)
        revision = await db.write_artifact(build_id, filename, new_content)
        await bus.emit("file_written", {"filename": filename, "revision": revision,
                                        "size": len(new_content), "agent": "editor"})

    await db.add_message(session_id, "assistant", reply, agent="editor")
    await bus.emit("message_done", {"content": reply})


async def _run_chat_turn(session_id: str, content: str, run_id: str) -> None:
    bus = events.bus(run_id)
    try:
        await bus.emit("run_start", {"run_id": run_id, "kind": "chat"})
        settings = await orchestrator.load_settings()
        history = await db.list_messages(session_id)  # snapshot BEFORE this message
        await db.add_message(session_id, "user", content)

        # Auto-title new sessions from the first prompt
        session = await db.get_session(session_id)
        if session and session["title"] == "New website" and not history:
            await db.rename_session(session_id, content[:48])

        # Route: a session with a finished build is in EDIT mode
        builds = await db.list_builds(session_id)
        latest = builds[0] if builds else None
        if latest and latest["status"] == "running":
            reply = ("The build is still running — I'll take edit requests the "
                     "moment it finishes.")
            await db.add_message(session_id, "assistant", reply, agent="system")
            await bus.emit("message_done", {"content": reply})
            await bus.emit("done", {"status": "done"})
            return
        if latest:
            full_build = await db.get_build(latest["id"])
            if full_build and await db.list_artifacts(latest["id"]):
                await _run_edit_turn(session_id, full_build, content, history,
                                     bus, settings)
                await bus.emit("done", {"status": "done"})
                return

        async def on_token(text: str) -> None:
            await bus.emit("token", {"agent": "interviewer", "text": text})

        reply, brief = await interviewer.run_turn_streaming(
            history, content, model=settings.model_for("interviewer"),
            on_token=on_token)

        await db.add_message(session_id, "assistant", reply, agent="interviewer")
        await bus.emit("message_done", {"content": reply})

        if brief is not None:
            await db.set_session_brief(session_id, brief.model_dump())
            await db.rename_session(session_id, brief.business_name)
            await bus.emit("brief_ready", {"brief": brief.model_dump()})

        await bus.emit("done", {"status": "done"})
    except Exception as error:
        await bus.emit("error", {"message": str(error), "fatal": True})
        await bus.emit("done", {"status": "failed"})
    finally:
        events.evict_later(run_id, 120)


@router.post("/api/sessions/{session_id}/messages")
async def post_message(session_id: str, body: MessageIn):
    if await db.get_session(session_id) is None:
        raise HTTPException(404, "session not found")
    if not body.content.strip():
        raise HTTPException(422, "empty message")
    run_id = uuid.uuid4().hex
    events.bus(run_id)  # create the bus before the task so no event is lost
    asyncio.get_running_loop().create_task(
        _run_chat_turn(session_id, body.content.strip(), run_id))
    return {"run_id": run_id}


@router.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    if not events.exists(run_id):
        raise HTTPException(404, "run not found (it may have expired)")
    return EventSourceResponse(events.bus(run_id).subscribe())
