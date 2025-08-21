"""Database migration utilities split from main.py for modularity."""

import alembic.config
import alembic.script
from sqlalchemy import create_engine
from alembic.runtime.migration import MigrationContext
from pathlib import Path
from typing import Optional, Tuple
import logging


def _get_alembic_ini_path() -> str:
    """Get absolute path to alembic.ini file."""
    project_root = Path(__file__).parent.parent.parent.parent
    return str(project_root / "config" / "alembic.ini")


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
    alembic_ini_path = _get_alembic_ini_path()
    if not Path(alembic_ini_path).exists():
        raise FileNotFoundError(f"Alembic configuration file not found: {alembic_ini_path}")
    cfg = alembic.config.Config(alembic_ini_path)
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def needs_migration(current: Optional[str], head: str) -> bool:
    """Check if migration is needed."""
    return current != head


def execute_migration(logger: logging.Logger) -> None:
    """Execute database migration to head."""
    logger.info("Executing database migration...")
    alembic_ini_path = _get_alembic_ini_path()
    alembic.config.main(argv=["-c", alembic_ini_path, "--raiseerr", "upgrade", "head"])
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


def _is_database_url_empty(database_url: Optional[str]) -> bool:
    """Check if database URL is None or empty."""
    return not database_url


def _is_database_in_mock_mode(database_url: str) -> bool:
    """Check if database URL indicates mock mode."""
    return "mock" in database_url.lower()


def _log_and_return_for_empty_url(logger: logging.Logger) -> bool:
    """Log warning for empty database URL and return False."""
    logger.warning("No database URL configured")
    return False


def _log_and_return_for_mock_mode(logger: logging.Logger) -> bool:
    """Log info for mock mode and return False."""
    logger.info("Database in mock mode - skipping migrations")
    return False


def validate_database_url(database_url: Optional[str], logger: logging.Logger) -> bool:
    """Validate database URL is configured."""
    if _is_database_url_empty(database_url):
        return _log_and_return_for_empty_url(logger)
    if _is_database_in_mock_mode(database_url):
        return _log_and_return_for_mock_mode(logger)
    return True