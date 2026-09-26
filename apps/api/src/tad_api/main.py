"""Application entrypoint: wires config, logging, storage, and routers."""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from tad_api.config import settings
from tad_api.logging import configure_logging
from tad_api.routers import analytics, health, reports
from tad_api.storage.memory import InMemoryRunStore

configure_logging(settings.log_level)
log = structlog.get_logger()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Binds a request ID to every log line emitted while handling a request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.run_store = InMemoryRunStore()
    log.info("startup", environment=settings.environment)
    yield
    log.info("shutdown")


app = FastAPI(title="Test Analytics Platform API", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)

app.include_router(health.router)
app.include_router(reports.router)
app.include_router(analytics.router)
