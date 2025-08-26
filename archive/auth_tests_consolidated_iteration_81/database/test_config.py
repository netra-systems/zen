"""
SSOT-Compliant Test Database Configuration
All database operations MUST use auth_service.auth_core.database.connection.auth_db

This file provides SSOT-compliant helpers for test database operations.
NO duplicate engine creation or session management.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: SSOT compliance and reduced maintenance burden  
- Value Impact: Eliminates duplicate database connection logic
- Strategic Impact: Single source of truth for all auth database operations
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.models import Base

logger = logging.getLogger(__name__)


class SSotTestDatabaseHelper:
    """SSOT-compliant test database helper using canonical auth_db"""
    
    @staticmethod
    async def ensure_initialized():
        """Ensure auth_db is initialized for tests"""
        if not auth_db._initialized:
            await auth_db.initialize()
    
    @staticmethod
    @asynccontextmanager
    async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
        """Get test session using canonical auth_db - SSOT compliant"""
        await SSotTestDatabaseHelper.ensure_initialized()
        async with auth_db.get_session() as session:
            yield session
    
    @staticmethod
    async def reset_tables_if_needed():
        """Reset tables using canonical auth_db if needed for test isolation"""
        await SSotTestDatabaseHelper.ensure_initialized()
        
        # For SQLite :memory: databases, tables are automatically isolated
        # For persistent test databases, we would need cleanup logic here
        engine_url = str(auth_db.engine.url)
        if ":memory:" in engine_url:
            logger.debug("Using :memory: database - automatic isolation")
        else:
            logger.warning("Using persistent database - consider cleanup logic if needed")
    
    @staticmethod
    async def verify_connection():
        """Verify database connection using canonical auth_db"""
        await SSotTestDatabaseHelper.ensure_initialized()
        return await auth_db.test_connection()


# SSOT-compliant helper functions
async def get_ssot_test_session() -> AsyncGenerator[AsyncSession, None]:
    """Get test session using SSOT auth_db - preferred method"""
    async with SSotTestDatabaseHelper.get_test_session() as session:
        yield session


async def setup_ssot_test_database():
    """Setup test database using SSOT auth_db - preferred method"""
    await SSotTestDatabaseHelper.ensure_initialized()
    return auth_db


# Legacy compatibility - DEPRECATED, will be removed
def get_test_db_config(use_postgres: bool = False):
    """DEPRECATED: Use auth_db directly instead"""
    logger.warning("DEPRECATED: get_test_db_config violates SSOT - use auth_db directly")
    raise DeprecationWarning("Use auth_service.auth_core.database.connection.auth_db directly")


async def setup_test_database(config=None):
    """DEPRECATED: Use auth_db.initialize() directly instead"""
    logger.warning("DEPRECATED: setup_test_database violates SSOT - use auth_db.initialize() directly")
    raise DeprecationWarning("Use auth_service.auth_core.database.connection.auth_db.initialize() directly")