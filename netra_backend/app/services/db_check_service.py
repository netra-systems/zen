from netra_backend.app.logging_config import central_logger
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import reflection
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from netra_backend.app.db.base import Base
from netra_backend.app.db.postgres import async_engine as engine

logger = central_logger.get_logger(__name__)

async def check_db_schema(db_session):
    """
    Validates the live database schema against the schema defined in the models and alembic revisions.
    """
    logger.info("Performing database schema self-check...")
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_validate_schema_with_alembic)
        logger.info("Database schema self-check passed.")
        return True
    except Exception as e:
        logger.error(f"Database schema self-check failed: {e}", exc_info=True)
        raise e

def _get_alembic_config() -> tuple[Config, ScriptDirectory]:
    """Get alembic configuration and script directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(current_dir, '..', '..', 'alembic.ini')
    logger.info(f"Loading Alembic config from: {alembic_ini_path}")
    alembic_cfg = Config(alembic_ini_path)
    script = ScriptDirectory.from_config(alembic_cfg)
    return alembic_cfg, script

def _get_head_revision(script: ScriptDirectory) -> str:
    """Get head revision from scripts."""
    logger.info("Getting head revision from scripts...")
    head_revision = script.get_current_head()
    logger.info(f"Head revision is: {head_revision}")
    return head_revision

def _get_current_revision(connection) -> str:
    """Get current revision from database."""
    logger.info("Getting current revision from database...")
    ctx = MigrationContext.configure(connection)
    current_rev = ctx.get_current_revision()
    logger.info(f"Current revision is: {current_rev}")
    return current_rev

def _validate_revisions(head_revision: str, current_rev: str) -> None:
    """Validate that head and current revisions match."""
    if head_revision != current_rev:
        error_msg = f"Database schema is out of date. Head revision is {head_revision}, but database is at {current_rev}. Please run migrations."
        raise Exception(error_msg)
    logger.info("Alembic revisions are up to date.")

def _get_database_tables(connection) -> list[str]:
    """Get table names from database."""
    logger.info("Comparing table names...")
    inspector = reflection.Inspector.from_engine(connection)
    db_tables = inspector.get_table_names()
    logger.info(f"Tables in database: {db_tables}")
    return db_tables

def _get_model_tables() -> set[str]:
    """Get table names from models."""
    model_table_names = set(Base.metadata.tables.keys())
    logger.info(f"Tables in models: {model_table_names}")
    return model_table_names

def _clean_database_tables(db_table_names: set[str]) -> set[str]:
    """Remove alembic_version table from database tables."""
    cleaned_tables = db_table_names.copy()
    if 'alembic_version' in cleaned_tables:
        cleaned_tables.remove('alembic_version')
    return cleaned_tables

def _create_table_mismatch_error(missing_in_db: set[str], missing_in_models: set[str]) -> str:
    """Create detailed error message for table mismatches."""
    error_message = "Database schema mismatch."
    if missing_in_db:
        error_message += f" Tables missing in the database: {missing_in_db}."
    if missing_in_models:
        error_message += f" Tables missing in the models: {missing_in_models}."
    return error_message

def _validate_table_names(model_table_names: set[str], db_table_names: set[str]) -> None:
    """Validate that model and database table names match."""
    cleaned_db_tables = _clean_database_tables(db_table_names)
    if model_table_names != cleaned_db_tables:
        missing_in_db = model_table_names - cleaned_db_tables
        missing_in_models = cleaned_db_tables - model_table_names
        error_message = _create_table_mismatch_error(missing_in_db, missing_in_models)
        raise Exception(error_message)
    logger.info("Table names match.")

def _perform_validation_checks(connection) -> None:
    """Perform all validation checks."""
    alembic_cfg, script = _get_alembic_config()
    head_revision = _get_head_revision(script)
    current_rev = _get_current_revision(connection)
    _validate_revisions(head_revision, current_rev)
    _validate_table_names(_get_model_tables(), set(_get_database_tables(connection)))

def _validate_schema_with_alembic(connection):
    """Validate database schema against alembic revisions and models."""
    logger.info("Starting schema validation with Alembic...")
    try:
        _perform_validation_checks(connection)
        logger.info("Schema validation with Alembic finished successfully.")
    except Exception as e:
        logger.error(f"Error during schema validation: {e}", exc_info=True)
        raise e
