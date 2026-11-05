import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import SessionLocal, init_db
from .routers import (admin, auth, collaboration, documents, entrepreneurs, evaluations, ideas, messages,
                      notifications, profiles, public)
from .services.seed import bootstrap

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ideabridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        init_db()
    with SessionLocal() as db:
        bootstrap(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="IdeaBridge API", version="1.0.0", lifespan=lifespan,
                  description="AI-powered innovation marketplace. Interactive docs: /docs")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    for r in (auth, profiles, public, ideas, documents, evaluations, entrepreneurs, collaboration, messages,
              notifications, admin):
        app.include_router(r.router, prefix="/api")

    @app.get("/api/health", tags=["public"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
