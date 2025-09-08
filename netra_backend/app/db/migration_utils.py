"""Database migration utilities split from main.py for modularity."""

from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine

import alembic.config
import alembic.script
from alembic.runtime.migration import MigrationContext

from netra_backend.app.core.unified_logging import get_logger


def _get_alembic_ini_path() -> str:
    """Get absolute path to alembic.ini file with fallback paths for different deployment scenarios."""
    # Try multiple possible locations for alembic.ini
    possible_paths = [
        # Standard development/local structure
        Path(__file__).parent.parent.parent.parent / "config" / "alembic.ini",
        
        # Cloud Run deployment structure (common patterns)
        Path("/app/config/alembic.ini"),
        Path("/app/alembic.ini"), 
        Path("/usr/src/app/config/alembic.ini"),
        Path("/usr/src/app/alembic.ini"),
        
        # Current working directory fallbacks
        Path.cwd() / "config" / "alembic.ini",
        Path.cwd() / "alembic.ini",
        
        # Relative to migration utils file
        Path(__file__).parent / "alembic.ini",
        Path(__file__).parent.parent / "alembic.ini",
        Path(__file__).parent.parent.parent / "alembic.ini",
    ]
    
    # Return the first path that exists
    for path in possible_paths:
        if path.exists():
            return str(path.absolute())
    
    # If no existing path found, return the default (development) path
    # This maintains backward compatibility and provides a clear error message
    default_path = Path(__file__).parent.parent.parent.parent / "config" / "alembic.ini"
    return str(default_path.absolute())


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
    """Create Alembic configuration with enhanced error handling and fallback mechanisms."""
    alembic_ini_path = _get_alembic_ini_path()
    
    if not Path(alembic_ini_path).exists():
        # Enhanced error message with troubleshooting information
        error_msg = f"""
Alembic configuration file not found at: {alembic_ini_path}

This typically happens in one of these scenarios:
1. Container deployment where alembic.ini wasn't copied to expected location
2. Working directory changed from project root
3. File system permissions preventing access

Troubleshooting:
- Verify alembic.ini exists in container at deployment time
- Check if current working directory is correct: {Path.cwd()}
- Verify file permissions allow reading alembic.ini

For staging/production deployments, ensure alembic.ini is included in the container build.
"""
        raise FileNotFoundError(error_msg.strip())
    
    try:
        cfg = alembic.config.Config(alembic_ini_path)
        cfg.set_main_option("sqlalchemy.url", database_url)
        return cfg
    except Exception as e:
        raise RuntimeError(f"Failed to create Alembic configuration from {alembic_ini_path}: {e}")
        
def create_alembic_config_with_fallback(database_url: str) -> alembic.config.Config:
    """Create Alembic configuration with graceful fallback for missing alembic.ini.
    
    This function attempts to create a basic Alembic configuration programmatically
    if the alembic.ini file is not found, allowing the system to continue operating
    in environments where the configuration file is missing.
    """
    try:
        return create_alembic_config(database_url)
    except FileNotFoundError:
        # Create a basic configuration programmatically as fallback
        logger = get_logger(__name__)
        logger.warning("alembic.ini not found, creating basic configuration programmatically")
        
        # Create a minimal Alembic configuration
        cfg = alembic.config.Config()
        cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Set basic migration directory (consistent with alembic.ini)
        project_root = Path(__file__).parent.parent.parent.parent
        alembic_dir = project_root / "netra_backend" / "app" / "alembic"
        cfg.set_main_option("script_location", str(alembic_dir))
        
        # Set other essential options
        cfg.set_main_option("version_locations", str(alembic_dir / "versions"))
        cfg.set_main_option("file_template", "%%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s")
        
        logger.info(f"Created fallback Alembic configuration with migrations at: {alembic_dir}")
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


class DatabaseMigrator:
    """Database migrator class that wraps migration utilities."""
    
    def __init__(self, database_url: str):
        """Initialize database migrator."""
        self.database_url = database_url
        self.sync_url = get_sync_database_url(database_url)
        self.logger = get_logger(__name__)
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        return get_current_revision(self.sync_url)
    
    def get_head_revision(self) -> str:
        """Get head revision from migrations."""
        cfg = create_alembic_config(self.sync_url)
        return get_head_revision(cfg)
    
    def needs_migration(self) -> bool:
        """Check if migration is needed."""
        current = self.get_current_revision()
        head = self.get_head_revision()
        return needs_migration(current, head)
    
    def execute_migration(self) -> None:
        """Execute database migration."""
        execute_migration(self.logger)
    
    def validate_url(self) -> bool:
        """Validate database URL."""
        return validate_database_url(self.database_url, self.logger)
    
    def create_config(self) -> alembic.config.Config:
        """Create Alembic configuration."""
        return create_alembic_config(self.sync_url)