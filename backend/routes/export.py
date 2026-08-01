"""Export: zip download + v1-style desktop folder."""

import io
import json
import os
import sys
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

import db
import writer

router = APIRouter(tags=["export"])


async def _latest_files(build_id: str) -> tuple[dict, dict[str, str]]:
    build = await db.get_build(build_id)
    if build is None:
        raise HTTPException(404, "build not found")
    files: dict[str, str] = {}
    for meta in await db.list_artifacts(build_id):
        artifact = await db.get_artifact(build_id, meta["filename"])
        files[meta["filename"]] = artifact["content"]
    if not files:
        raise HTTPException(409, "build has no files yet")
    return build, files


def _site_name(build: dict) -> str:
    brief = json.loads(build["brief_json"]) if build["brief_json"] else {}
    return writer.clean_name(brief.get("business_name", "my-website"))


@router.get("/api/builds/{build_id}/export.zip")
async def export_zip(build_id: str):
    build, files = await _latest_files(build_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    buffer.seek(0)
    name = _site_name(build)
    return StreamingResponse(
        buffer, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'})


@router.post("/api/builds/{build_id}/export-to-desktop")
async def export_to_desktop(build_id: str):
    build, files = await _latest_files(build_id)
    brief = json.loads(build["brief_json"]) if build["brief_json"] else {}
    folder = writer.write_build_to_disk(brief.get("business_name", "my-website"), files)
    try:
        if sys.platform == "win32":
            os.startfile(folder)  # the satisfying v1 demo ending
    except Exception:
        pass
    return {"path": str(folder)}
