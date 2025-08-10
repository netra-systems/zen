from app.logging_config import central_logger
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import reflection
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from app.db.base import Base
from app.db.postgres import async_engine as engine

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

def _validate_schema_with_alembic(connection):
    logger.info("Starting schema validation with Alembic...")
    try:
        # Construct the path to alembic.ini relative to this file
        # This makes the path independent of the current working directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_ini_path = os.path.join(current_dir, '..', '..', 'alembic.ini')
        logger.info(f"Loading Alembic config from: {alembic_ini_path}")
        alembic_cfg = Config(alembic_ini_path)
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get the head revision from the scripts
        logger.info("Getting head revision from scripts...")
        head_revision = script.get_current_head()
        logger.info(f"Head revision is: {head_revision}")

        # Get the current revision from the database
        logger.info("Getting current revision from database...")
        ctx = MigrationContext.configure(connection)
        current_rev = ctx.get_current_revision()
        logger.info(f"Current revision is: {current_rev}")

        if head_revision != current_rev:
            raise Exception(f"Database schema is out of date. Head revision is {head_revision}, but database is at {current_rev}. Please run migrations.")

        logger.info("Alembic revisions are up to date.")

        # Additionally, compare table names as a sanity check
        logger.info("Comparing table names...")
        inspector = reflection.Inspector.from_engine(connection)
        db_tables = inspector.get_table_names()
        logger.info(f"Tables in database: {db_tables}")

        model_table_names = set(Base.metadata.tables.keys())
        logger.info(f"Tables in models: {model_table_names}")
        db_table_names = set(db_tables)

        # The alembic_version table is not part of the models
        if 'alembic_version' in db_table_names:
            db_table_names.remove('alembic_version')

        if model_table_names != db_table_names:
            missing_in_db = model_table_names - db_table_names
            missing_in_models = db_table_names - model_table_names
            error_message = "Database schema mismatch."
            if missing_in_db:
                error_message += f" Tables missing in the database: {missing_in_db}."
            if missing_in_models:
                error_message += f" Tables missing in the models: {missing_in_models}."
            raise Exception(error_message)
        
        logger.info("Table names match.")
        logger.info("Schema validation with Alembic finished successfully.")

    except Exception as e:
        logger.error(f"Error during schema validation: {e}", exc_info=True)
        raise e
