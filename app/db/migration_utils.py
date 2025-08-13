"""Database migration utilities split from main.py for modularity."""

import alembic.config
import alembic.script
from sqlalchemy import create_engine
from alembic.runtime.migration import MigrationContext
from typing import Optional, Tuple
import logging


def get_sync_database_url(database_url: str) -> str:
    """Convert async database URL to sync for Alembic."""
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return database_url


def get_current_revision(database_url: str) -> Optional[str]:
    """Get current database revision."""
    engine = create_engine(database_url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def get_head_revision(alembic_cfg: alembic.config.Config) -> str:
    """Get the head revision from Alembic scripts."""
    script = alembic.script.ScriptDirectory.from_config(alembic_cfg)
    return script.get_current_head()


def create_alembic_config(database_url: str) -> alembic.config.Config:
    """Create Alembic configuration."""
    cfg = alembic.config.Config("config/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def needs_migration(current: Optional[str], head: str) -> bool:
    """Check if migration is needed."""
    return current != head


def execute_migration(logger: logging.Logger) -> None:
    """Execute database migration to head."""
    logger.info("Executing database migration...")
    alembic.config.main(argv=["--raiseerr", "upgrade", "head"])
    logger.info("Migration completed successfully")


def log_migration_status(logger: logging.Logger, current: Optional[str], head: str) -> None:
    """Log migration status."""
    if needs_migration(current, head):
        logger.info(f"Migrating from {current} to {head}")
    else:
        logger.info("Database is up to date")


def should_continue_on_error(environment: str) -> bool:
    """Determine if app should continue after migration error."""
    return environment != "production"


def validate_database_url(database_url: Optional[str], logger: logging.Logger) -> bool:
    """Validate database URL is configured."""
    if not database_url:
        logger.warning("No database URL configured")
        return False
    return True