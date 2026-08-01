"""Artifact files: list, read, and save (Monaco editor writes bump the revision)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db

router = APIRouter(tags=["files"])


class FilePut(BaseModel):
    content: str


@router.get("/api/builds/{build_id}/files")
async def list_files(build_id: str):
    if await db.get_build(build_id) is None:
        raise HTTPException(404, "build not found")
    return await db.list_artifacts(build_id)


@router.get("/api/builds/{build_id}/files/{filename}")
async def get_file(build_id: str, filename: str):
    artifact = await db.get_artifact(build_id, filename)
    if artifact is None:
        raise HTTPException(404, "file not found")
    return artifact


@router.put("/api/builds/{build_id}/files/{filename}")
async def put_file(build_id: str, filename: str, body: FilePut):
    existing = await db.get_artifact(build_id, filename)
    if existing is None:
        raise HTTPException(404, "file not found — only existing files can be edited")
    revision = await db.write_artifact(build_id, filename, body.content)
    return {"filename": filename, "revision": revision}
