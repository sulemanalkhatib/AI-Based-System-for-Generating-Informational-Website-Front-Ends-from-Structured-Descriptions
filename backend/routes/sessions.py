"""Session CRUD + message history."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str = "New website"


class SessionPatch(BaseModel):
    title: str


@router.post("")
async def create_session(body: SessionCreate | None = None):
    return await db.create_session((body.title if body else "New website") or "New website")


@router.get("")
async def list_sessions():
    return await db.list_sessions()


@router.get("/{session_id}")
async def get_session(session_id: str):
    session = await db.get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    session["brief"] = json.loads(session["brief_json"]) if session["brief_json"] else None
    del session["brief_json"]
    return {
        "session": session,
        "messages": await db.list_messages(session_id),
        "builds": await db.list_builds(session_id),
    }


@router.patch("/{session_id}")
async def rename_session(session_id: str, body: SessionPatch):
    if await db.get_session(session_id) is None:
        raise HTTPException(404, "session not found")
    await db.rename_session(session_id, body.title)
    return await db.get_session(session_id)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str):
    if await db.get_session(session_id) is None:
        raise HTTPException(404, "session not found")
    await db.delete_session(session_id)
