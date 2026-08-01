"""Builds: start the pipeline, inspect state, stream progress (replay-safe)."""

import asyncio
import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

import db
import events
import orchestrator

router = APIRouter(tags=["builds"])

# Running build tasks, so the Stop button can cancel one mid-flight.
_running: dict[str, asyncio.Task] = {}


@router.post("/api/sessions/{session_id}/builds")
async def start_build(session_id: str):
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if not session["brief_json"]:
        raise HTTPException(409, "no brief yet — finish the interview first")
    build_id = await db.create_build(session_id, json.loads(session["brief_json"]))
    events.bus(build_id)  # create the bus before the task so no event is lost
    task = asyncio.get_running_loop().create_task(orchestrator.run_build(build_id))
    _running[build_id] = task
    task.add_done_callback(lambda _t: _running.pop(build_id, None))
    return {"build_id": build_id}


@router.post("/api/builds/{build_id}/cancel")
async def cancel_build(build_id: str):
    """Stop a running build — the agents halt at their next await."""
    task = _running.get(build_id)
    if task and not task.done():
        task.cancel()
        return {"ok": True}
    return {"ok": False, "detail": "no running build to stop"}


@router.get("/api/builds/{build_id}")
async def get_build(build_id: str):
    build = await db.get_build(build_id)
    if build is None:
        raise HTTPException(404, "build not found")
    detail = {
        "id": build["id"],
        "session_id": build["session_id"],
        "status": build["status"],
        "created_at": build["created_at"],
        "brief": json.loads(build["brief_json"]) if build["brief_json"] else None,
        "copy_deck": json.loads(build["copy_json"]) if build["copy_json"] else None,
        "design_spec": json.loads(build["design_json"]) if build["design_json"] else None,
        "audit": json.loads(build["audit_json"]) if build["audit_json"] else None,
        "files": await db.list_artifacts(build_id),
    }
    return detail


async def _replay_from_db(build: dict):
    """Synthetic replay for streams requested after the live bus was evicted."""
    seq = 0

    def item(event: str, data: dict) -> dict:
        nonlocal seq
        seq += 1
        return {"event": event, "data": json.dumps({"seq": seq, **data})}

    def agent_for(filename: str) -> str:
        if filename == "style.css":
            return "builder:css"
        if filename == "script.js":
            return "builder:js"
        if filename.endswith(".html"):
            return f"builder:{filename}"
        return "builder"

    succeeded = build["status"] == "done"
    artifacts = await db.list_artifacts(build["id"])

    yield item("run_start", {"build_id": build["id"], "kind": "build", "replay": True})

    # Reconstruct the finished pipeline so a reopened build shows every agent as
    # completed (the live per-agent events are gone once the bus is evicted).
    if build["copy_json"]:
        deck = json.loads(build["copy_json"])
        pages = [{"filename": p["filename"], "title": p.get("title", "")}
                 for p in deck.get("pages", [])]
        yield item("pages_planned", {"pages": pages})
        if succeeded:
            yield item("agent_done", {"agent": "copywriter"})
    if build["design_json"] and succeeded:
        yield item("agent_done", {"agent": "designer"})

    for artifact in artifacts:
        agent = agent_for(artifact["filename"])
        if succeeded:
            yield item("agent_done", {"agent": agent})
        yield item("file_written", {**artifact, "agent": agent})

    if succeeded and any(a["revision"] > 1 for a in artifacts):
        yield item("agent_done", {"agent": "recheck"})
    if build["audit_json"]:
        if succeeded:
            yield item("agent_done", {"agent": "audit"})
        yield item("audit", {"report": json.loads(build["audit_json"])})

    yield item("done", {"status": build["status"], "build_id": build["id"],
                        "replay": True})


@router.get("/api/builds/{build_id}/stream")
async def stream_build(build_id: str):
    if events.exists(build_id):
        return EventSourceResponse(events.bus(build_id).subscribe())
    build = await db.get_build(build_id)
    if build is None:
        raise HTTPException(404, "build not found")
    # Bus is gone (server restart or eviction) — replay terminal state from the DB
    return EventSourceResponse(_replay_from_db(build))
