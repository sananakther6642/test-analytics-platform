import asyncio
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import order matters: this must run before target_metadata is read, since
# it's what registers every table on Base.metadata.
from tad_api.config import settings  # noqa: E402
from tad_api.db.models import Base  # noqa: E402

target_metadata = Base.metadata

# Use our own Settings (env-based, TAD_DATABASE_URL) as the single source of
# truth for the DB URL, rather than duplicating it in alembic.ini — one
# place to change, and it matches how every other setting in this app is
# configured.
#
# IMPORTANT: only when the caller hasn't already set one. Tests
# (tests/integration/conftest.py) deliberately pass a different URL — a
# sync driver, to run migrations outside pytest-asyncio's event loop —
# and unconditionally overwriting it here silently discarded that and
# broke test isolation from the real app database. Config's ini-file
# default is the sentinel: if it's still that placeholder-less empty
# string, nothing else has set it yet.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Branches on driver: a sync URL (e.g. postgresql+psycopg2://, used by
    the integration-test fixture to avoid asyncio.run() conflicting with
    pytest-asyncio's already-running event loop) runs synchronously; the
    app's normal asyncpg URL runs through the async path as before.
    """
    url = config.get_main_option("sqlalchemy.url") or ""
    if "+asyncpg" in url:
        asyncio.run(run_async_migrations())
    else:
        connectable = create_engine(url, poolclass=pool.NullPool)
        with connectable.connect() as connection:
            do_run_migrations(connection)
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
