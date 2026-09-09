import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.models  # noqa: F401 — registers every table on Base.metadata
from app.core.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )
    with context.begin_transaction():
        context.run_migrations()


def _bootstrap_if_empty(connectable) -> None:
    """Create the application schema when the target DB is empty.

    Sentinel also boots via `Base.metadata.create_all`, so a fresh database must
    match the model before migration files (which assume base tables exist) run.
    Existing databases with an `alembic_version` table are left untouched.
    """
    from sqlalchemy import inspect

    if "alembic_version" in inspect(connectable).get_table_names():
        return
    Base.metadata.create_all(bind=connectable)


def run_migrations_online() -> None:
    if os.environ.get("DATABASE_URL"):
        config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _bootstrap_if_empty(connectable)
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
