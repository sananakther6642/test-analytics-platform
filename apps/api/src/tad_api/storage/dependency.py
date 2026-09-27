"""FastAPI dependencies for storage.

get_run_store wires a fresh PostgresRunStore per request. Each request
gets its own DB session (via get_session's per-call
async_session_factory()) and its own PostgresRunStore wrapping it —
SQLAlchemy async sessions are not safe to share across concurrent requests,
so a single store constructed once at app startup (as InMemoryRunStore
was in Phase 1) cannot work correctly here.

get_blob_store is different: it returns the single ReportBlobStore built
once in main.py's lifespan and shared across all requests via
app.state — see that module's comment for why blob storage doesn't need
the per-request treatment RunStore does.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tad_api.db.session import get_session
from tad_api.storage.blob import ReportBlobStore
from tad_api.storage.postgres import PostgresRunStore


async def get_run_store(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[PostgresRunStore]:
    yield PostgresRunStore(session)


def get_blob_store(request: Request) -> ReportBlobStore:
    return request.app.state.blob_store
