"""Readiness probe tests — deliberately in tests/integration/, not
tests/unit/, since the whole point of /readyz is checking a real database
connection. A mocked-DB version of this test would only prove the mock
behaves as told, not that the endpoint actually detects a real outage.
"""

import httpx
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tad_api.db.session import get_session
from tad_api.main import app


@pytest.mark.asyncio
async def test_readyz_passes_with_a_real_database(migrated_database_url: str):
    # One engine for the whole test, matching how the real app's
    # db/session.py does it (module-level engine, session-per-request) —
    # the earlier version created a fresh engine *and* wrapped it in an
    # extra explicit Connection inside the generator override, which raced
    # with asyncpg's own connection state during FastAPI's dependency
    # teardown and produced a spurious "cannot switch to state" error on
    # cleanup, unrelated to whether the database was actually reachable.
    engine = create_async_engine(migrated_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        async with LifespanManager(app) as manager:
            transport = ASGITransport(app=manager.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as c:
                resp = await c.get("/readyz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_readyz_returns_503_when_database_is_unreachable():
    # Port 1 is a privileged, essentially-never-listening port on any real
    # host — connection is refused immediately rather than timing out slowly,
    # so this test proves the failure path without being slow itself.
    unreachable_url = "postgresql+asyncpg://nobody:nothing@localhost:1/nowhere"
    engine = create_async_engine(unreachable_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        async with LifespanManager(app) as manager:
            transport = ASGITransport(app=manager.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as c:
                resp = await c.get("/readyz")
        assert resp.status_code == 503
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
