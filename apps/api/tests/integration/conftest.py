"""Integration test fixtures: a real Postgres container via testcontainers.

Pinned to the same postgres:16.4-alpine tag as docker-compose.yml (see ADR
0004) — not the floating :16-alpine tag that caused a genuine multi-hour
outage this session. Using a different, unpinned tag here would silently
reintroduce the exact risk that ADR exists to close off.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

_ALEMBIC_INI = "alembic.ini"


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16.4-alpine", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="session")
def migrated_database_url(postgres_container: PostgresContainer) -> str:
    """Run real Alembic migrations against the test container, once per
    test session — proves the migrations themselves work, not just that
    SQLAlchemy can talk to a database with a schema created some other way.

    Runs the migration through a plain SYNC driver (psycopg2), not the
    app's normal asyncpg URL. migrations/env.py calls asyncio.run()
    internally (the async template Alembic generated), and asyncio.run()
    cannot be invoked from inside an already-running event loop — which is
    exactly the context pytest-asyncio's test session creates. Migrations
    are DDL; they don't need to be async at all, so swapping the driver
    just for this step sidesteps the conflict entirely rather than fighting
    it. The URL returned to tests is still the real asyncpg one, used for
    all actual queries.
    """
    async_url = postgres_container.get_connection_url()
    sync_url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    alembic_cfg = Config(_ALEMBIC_INI)
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_cfg, "head")

    return async_url


@pytest_asyncio.fixture
async def db_session(migrated_database_url: str) -> AsyncGenerator[AsyncSession]:
    """A fresh session per test, with all data truncated afterward.

    session.rollback() alone is NOT sufficient here: PostgresRunStore.add()
    calls session.commit() internally (a real write path, not a
    test-only convenience), so by the time a test finishes, its data is
    already durably committed to the shared container and rollback() is a
    no-op against it. Truncating explicitly is what actually isolates
    tests that share one container across a whole test session — a fresh
    container per test would also work but pays full startup cost every
    time for no real isolation benefit beyond what truncation gives here.
    """
    engine = create_async_engine(migrated_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with session_factory() as cleanup:
        await cleanup.execute(
            text("TRUNCATE test_results, test_runs, test_identity CASCADE")
        )
        await cleanup.commit()

    await engine.dispose()
