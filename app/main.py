"""
Application entrypoint.

Run with:
    uvicorn app.main:app --reload
"""
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.config import get_settings
from app.database import init_db
from app.logger import configure_logging, get_logger, request_id_ctx
from app.webhook import router as webhook_router

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("app_startup", extra={"ctx_environment": settings.environment})
    yield


app = FastAPI(
    title=settings.app_name,
    description="Parses WhatsApp shop messages into structured transactions using Claude.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attaches a request_id to every log line emitted while handling this request."""
    req_id = str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start = time.time()
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        "request_completed",
        extra={
            "ctx_path": request.url.path,
            "ctx_method": request.method,
            "ctx_duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = req_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", extra={"ctx_path": request.url.path, "ctx_error": str(exc)})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api_router, tags=["api"])
app.include_router(webhook_router, tags=["webhook"])
