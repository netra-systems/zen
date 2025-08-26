"""Database migration utilities split from main.py for modularity."""

from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine

import alembic.config
import alembic.script
from alembic.runtime.migration import MigrationContext

from netra_backend.app.core.unified_logging import get_logger


def _get_alembic_ini_path() -> str:
    """Get absolute path to alembic.ini file."""
    project_root = Path(__file__).parent.parent.parent.parent
    return str(project_root / "config" / "alembic.ini")


def get_sync_database_url(database_url: str) -> str:
    """Convert async database URL to sync for Alembic.
    
    Handles various PostgreSQL URL formats:
    - postgresql:// -> postgresql+psycopg2://
    - postgres:// -> postgresql+psycopg2://
    - postgresql+asyncpg:// -> postgresql+psycopg2://
    """
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    elif database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg2://")
    elif database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg2://")
    return database_url


def get_current_revision(database_url: str) -> Optional[str]:
    """Get current database revision with table existence check."""
    from sqlalchemy import text
    engine = create_engine(database_url)
    with engine.connect() as connection:
        # Check if alembic_version table exists
        result = connection.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
        ))
        table_exists = result.scalar()
        
        if not table_exists:
            # No alembic_version table means no migrations have been applied
            return None
            
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
    # If current is None, we need migration/stamp
    if current is None:
        return True
    return current != head


def execute_migration(logger) -> None:
    """Execute database migration to head with idempotent handling."""
    logger.info("Executing database migration...")
    alembic_ini_path = _get_alembic_ini_path()
    
    try:
        # Use stamp if tables exist but no alembic_version table
        from netra_backend.app.core.configuration.base import get_unified_config
        config = get_unified_config()
        sync_url = get_sync_database_url(config.database_url)
        
        # Check if we need to stamp instead of migrate
        if _should_stamp_instead_of_migrate(sync_url, logger):
            logger.info("Tables exist but no migration tracking - stamping to latest revision")
            alembic.config.main(argv=["-c", alembic_ini_path, "--raiseerr", "stamp", "head"])
        else:
            alembic.config.main(argv=["-c", alembic_ini_path, "--raiseerr", "upgrade", "head"])
        
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Try to stamp if upgrade failed due to existing tables
        if "already exists" in str(e) or "DuplicateTable" in str(e):
            logger.warning("Migration failed due to existing tables - attempting to stamp")
            try:
                alembic.config.main(argv=["-c", alembic_ini_path, "--raiseerr", "stamp", "head"])
                logger.info("Successfully stamped database to current head")
            except Exception as stamp_error:
                logger.error(f"Stamp also failed: {stamp_error}")
                raise stamp_error
        else:
            raise e


def log_migration_status(logger, current: Optional[str], head: str) -> None:
    """Log migration status."""
    if needs_migration(current, head):
        logger.info(f"Migrating from {current} to {head}")
    else:
        logger.info("Database is up to date")


def should_continue_on_error(environment: str) -> bool:
    """Determine if app should continue after migration error."""
    return environment != "production"


def _should_stamp_instead_of_migrate(database_url: str, logger) -> bool:
    """Check if we should stamp instead of migrate (tables exist but no alembic tracking)."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)
        
        with engine.connect() as connection:
            # Check if core tables exist
            result = connection.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name IN ('users', 'threads', 'assistants')"
            ))
            existing_core_tables = [row[0] for row in result.fetchall()]
            
            # Check if alembic_version exists
            result = connection.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
            ))
            alembic_version_exists = result.scalar()
            
            # If core tables exist but no alembic_version, we should stamp
            should_stamp = len(existing_core_tables) > 0 and not alembic_version_exists
            
            if should_stamp:
                logger.info(f"Found {len(existing_core_tables)} core tables but no alembic_version table - will stamp")
            
            return should_stamp
            
    except Exception as e:
        logger.warning(f"Could not determine stamp vs migrate: {e}")
        return False


def _is_database_url_empty(database_url: Optional[str]) -> bool:
    """Check if database URL is None or empty."""
    return not database_url


def _is_database_in_mock_mode(database_url: str) -> bool:
    """Check if database URL indicates mock mode."""
    return "mock" in database_url.lower()


def _log_and_return_for_empty_url(logger) -> bool:
    """Log warning for empty database URL and return False."""
    logger.warning("No database URL configured")
    return False


def _log_and_return_for_mock_mode(logger) -> bool:
    """Log info for mock mode and return False."""
    logger.info("Database in mock mode - skipping migrations")
    return False


def validate_database_url(database_url: Optional[str], logger) -> bool:
    """Validate database URL is configured."""
    if _is_database_url_empty(database_url):
        return _log_and_return_for_empty_url(logger)
    if _is_database_in_mock_mode(database_url):
        return _log_and_return_for_mock_mode(logger)
    return True