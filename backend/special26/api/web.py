"""Serve the built React app with an SPA fallback (04 §1). /api and /public stay with the API routers."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

STATIC = Path(os.environ.get("SPECIAL26_STATIC_DIR", Path(__file__).resolve().parents[3] / "frontend/dist"))


def index_html() -> str:
    return (STATIC / "index.html").read_text()


def mount(app: FastAPI) -> None:
    if not (STATIC / "index.html").exists():
        return
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/s/{token}", include_in_schema=False)
    async def share_page(token: str, request: Request):
        from special26.api.share import og_page, shared_view
        from special26.errors import Special26Error
        try:
            v = shared_view(request.app.state.s26, token, count=False)
        except Special26Error:
            return HTMLResponse(index_html())
        verdict = v.get("verdict") or {}
        reasons = verdict.get("reasons") or [{}]
        return og_page(index_html(), verdict.get("headline", "Special26"), reasons[0].get("message", ""))

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith(("api/", "public/")):
            raise HTTPException(404)
        f = STATIC / path
        if path and f.is_file() and STATIC in f.resolve().parents:
            return FileResponse(f)
        return HTMLResponse(index_html())
