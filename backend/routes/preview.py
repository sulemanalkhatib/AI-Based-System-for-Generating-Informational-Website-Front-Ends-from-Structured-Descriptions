"""Preview: serve the latest revision of build files so multi-page links work.

Deliberately NOT under /api — pages reference each other and their assets with
relative paths (about.html, style.css), which resolve against this route.
"""

from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, Response

import db

router = APIRouter(tags=["preview"])

_MIME = {
    ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
    ".svg": "image/svg+xml", ".json": "application/json", ".txt": "text/plain",
}


@router.get("/preview/{build_id}")
@router.get("/preview/{build_id}/")
async def preview_index(build_id: str):
    return RedirectResponse(f"/preview/{build_id}/index.html")


@router.get("/preview/{build_id}/{filename}")
async def preview_file(build_id: str, filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(404, "not found")
    artifact = await db.get_artifact(build_id, filename)
    if artifact is None:
        raise HTTPException(404, "not found")
    media_type = _MIME.get(PurePosixPath(filename).suffix.lower(), "text/plain")
    return Response(
        content=artifact["content"],
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )
