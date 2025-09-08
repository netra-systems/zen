"""
Alembic state recovery module for migration health checks.

Provides utilities to ensure Alembic migration state is healthy and recoverable.
This module implements minimal functionality to support migration_tracker.py.
"""

import logging
from typing import Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.db.migration_utils import get_sync_database_url


logger = logging.getLogger(__name__)


async def ensure_migration_state_healthy(database_url: str) -> Tuple[bool, str]:
    """
    Ensure Alembic migration state is healthy and recoverable.
    
    This function performs basic connectivity and Alembic version table checks
    to ensure the database is in a state that allows migration operations.
    
    Args:
        database_url: The database URL to check
        
    Returns:
        Tuple of (healthy: bool, recovery_info: str)
        - healthy: True if migration state is healthy, False otherwise
        - recovery_info: Details about the health check or recovery actions needed
    """
    try:
        # Convert async URL to sync for direct SQL operations
        sync_url = get_sync_database_url(database_url)
        
        # Test basic database connectivity
        engine = create_engine(sync_url)
        
        with engine.connect() as connection:
            # Test basic connectivity
            connection.execute(text("SELECT 1"))
            
            # Check if alembic_version table exists (indicates migrations have been initialized)
            try:
                result = connection.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_name = 'alembic_version'"
                ))
                table_exists = result.scalar() > 0
                
                if table_exists:
                    # Check if we can read from alembic_version table
                    connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                    recovery_info = "Alembic migration state is healthy"
                else:
                    # Table doesn't exist but database is accessible - this is normal for fresh installs
                    recovery_info = "Alembic version table not found - migrations may not be initialized"
                
                logger.debug(f"Migration state health check passed: {recovery_info}")
                return True, recovery_info
                
            except SQLAlchemyError as table_error:
                # Table exists but can't be read - this indicates a problem
                error_msg = f"Alembic version table exists but not readable: {table_error}"
                logger.warning(error_msg)
                return False, error_msg
        
        engine.dispose()
        
    except SQLAlchemyError as db_error:
        error_msg = f"Database connectivity check failed: {db_error}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as error:
        error_msg = f"Unexpected error during migration state health check: {error}"
        logger.error(error_msg)
        return False, error_msg