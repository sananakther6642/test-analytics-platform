"""Application entrypoint: wires config, logging, storage, and routers."""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from tad_api.config import settings
from tad_api.logging import configure_logging
from tad_api.routers import analytics, health, reports
from tad_api.storage.blob import AzureBlobStore, NullBlobStore, ReportBlobStore

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
    # No app.state.run_store here anymore (Phase 1 had one, constructed
    # once at startup) — PostgresRunStore needs a fresh DB session per
    # request, not one shared instance for the app's whole lifetime, so
    # it's built per-request via the get_run_store dependency instead.
    #
    # blob_store is different: the Azure SDK's async clients are built to
    # be shared and reused across requests (they pool connections
    # internally), so unlike RunStore this one lives on app.state and is
    # constructed once here, not per-request.
    blob_store: ReportBlobStore
    if settings.blob_account_url:
        blob_store = AzureBlobStore(settings.blob_account_url, settings.blob_container)
    else:
        blob_store = NullBlobStore()
    app.state.blob_store = blob_store

    log.info(
        "startup",
        environment=settings.environment,
        blob_configured=settings.blob_account_url is not None,
    )
    yield
    if isinstance(blob_store, AzureBlobStore):
        await blob_store.aclose()
    log.info("shutdown")


app = FastAPI(title="Test Analytics Platform API", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)

app.include_router(health.router)
app.include_router(reports.router)
app.include_router(analytics.router)
