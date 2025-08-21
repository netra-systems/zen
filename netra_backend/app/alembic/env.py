import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from netra_backend.app.db.base import Base
from netra_backend.app.db.models_postgres import *
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _configure_offline_context() -> None:
    """Configure context for offline migrations."""
    url = config.get_main_option("sqlalchemy.url")
    # Ensure synchronous URL for offline migrations
    if url:
        url = _ensure_sync_database_url(url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"})

def run_migrations_offline() -> None:
    """Run migrations in offline mode using URL configuration."""
    _configure_offline_context()
    with context.begin_transaction():
        context.run_migrations()


def _ensure_sync_database_url(url: str) -> str:
    """Ensure database URL uses synchronous driver for migrations."""
    if not url:
        return url
    
    # Remove async driver if present
    if "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        # Convert ssl back to sslmode for psycopg2
        if "ssl=" in url and "/cloudsql/" not in url:
            url = url.replace("ssl=", "sslmode=")
    
    # Ensure we're using psycopg2 (sync) driver
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    return url

def _get_configuration() -> dict:
    """Get database configuration from environment."""
    from netra_backend.app.config import get_config
    app_config = get_config()
    configuration = config.get_section(config.config_ini_section, {})
    if app_config.database_url:
        # Ensure synchronous URL for migrations
        sync_url = _ensure_sync_database_url(app_config.database_url)
        configuration['sqlalchemy.url'] = sync_url
    return configuration

def _create_connectable(configuration: dict):
    """Create database connectable."""
    return engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool)

def _execute_online_migrations(connection) -> None:
    """Execute migrations with connection."""
    context.configure(
        connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in online mode with Engine and connection."""
    configuration = _get_configuration()
    connectable = _create_connectable(configuration)
    with connectable.connect() as connection:
        _execute_online_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()