"""Dev-only helpers (mounted when DEV_ROUTES=1): skip the interview for demos/tests."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from models import ProjectBrief

router = APIRouter(prefix="/api/dev", tags=["dev"])


class SeedBrief(BaseModel):
    session_id: str
    brief: ProjectBrief | None = None


@router.post("/seed-brief")
async def seed_brief(body: SeedBrief):
    if await db.get_session(body.session_id) is None:
        raise HTTPException(404, "session not found")
    brief = body.brief
    if brief is None:
        from mock.fixtures import MOCK_BRIEF
        brief = MOCK_BRIEF
    await db.set_session_brief(body.session_id, brief.model_dump())
    await db.rename_session(body.session_id, brief.business_name)
    await db.add_message(body.session_id, "assistant",
                         f"[dev] Brief seeded for {brief.business_name} — ready to build.",
                         agent="interviewer")
    return {"ok": True, "brief": brief.model_dump()}
