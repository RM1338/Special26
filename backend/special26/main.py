"""FastAPI app factory, error envelope, request ids, lifespan (05 §1, 07 §9)."""
import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from special26.api import checks, health, web
from special26.config import Settings, get_settings
from special26.deps import build
from special26.errors import Special26Error
from special26.pipeline.events import Events
from special26.probes.base import validate_ruleset
from special26.storage.retention import run_retention, seed_known_entities

log = logging.getLogger("special26")


@dataclass
class State:
    settings: Settings
    repo: object
    serp: object
    events: Events
    http: httpx.AsyncClient
    tasks: set = field(default_factory=set)


def envelope(code: str, message: str, details: dict, request_id: str, status: int, headers=None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, "details": details}, "request_id": request_id},
                        status_code=status, headers=headers)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    validate_ruleset()                         # refuse to start on a missing weight or copy (T1.6)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        http = httpx.AsyncClient()
        repo, serp = build(settings, http)
        seed_known_entities(repo.db)
        run_retention(repo.db)
        app.state.s26 = State(settings, repo, serp, Events(repo), http)

        async def hourly():
            while True:
                await asyncio.sleep(3600)
                run_retention(repo.db)
        job = asyncio.create_task(hourly())
        yield
        job.cancel()
        for t in list(app.state.s26.tasks):
            t.cancel()
        await http.aclose()

    app = FastAPI(title="Special26", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = "req_" + secrets.token_hex(8)
        request.state.rid = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(Special26Error)
    async def s26_error(request: Request, e: Special26Error):
        headers = {"Retry-After": str(e.details["retry_after"])} if "retry_after" in e.details else None
        return envelope(e.code, e.message, e.details, getattr(request.state, "rid", ""), e.http_status, headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, e: RequestValidationError):
        first = e.errors()[0] if e.errors() else {}
        field_ = ".".join(str(x) for x in first.get("loc", [])[1:])
        return envelope("VALIDATION_ERROR", first.get("msg", "invalid request"), {"field": field_},
                        getattr(request.state, "rid", ""), 422)

    @app.exception_handler(Exception)
    async def internal(request: Request, e: Exception):
        log.exception("unhandled", extra={"path": request.url.path})
        return envelope("INTERNAL", "Something went wrong.", {}, getattr(request.state, "rid", ""), 500)

    app.include_router(checks.router)
    app.include_router(health.router)
    web.mount(app)                             # after the API routers: the SPA fallback must come last
    return app
