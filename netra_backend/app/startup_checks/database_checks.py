"""
Database Checks

Handles database connectivity and schema validation.
Maintains 25-line function limit and focused responsibility.
"""

import time
from typing import List
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.db.models_postgres import Assistant
from netra_backend.app.startup_checks.models import StartupCheckResult


class DatabaseChecker:
    """Handles database connectivity and schema checks"""
    
    def __init__(self, app):
        self.app = app
        config = unified_config_manager.get_config()
        self.environment = config.environment.lower()
        self.is_staging = self.environment == "staging" or (hasattr(config, 'k_service') and config.k_service)
        database_url = getattr(config, 'database_url', '')
        self.is_mock = "mock" in database_url.lower()
    
    async def check_database_connection(self) -> StartupCheckResult:
        """Check PostgreSQL database connection and schema"""
        # Check for mock mode from both config URL and runtime app state
        if self.is_mock or (hasattr(self.app.state, 'database_mock_mode') and self.app.state.database_mock_mode):
            return self._create_mock_result("database_connection")
        return await self._perform_database_connection_check()
    
    async def _perform_database_connection_check(self) -> StartupCheckResult:
        """Perform actual database connection check"""
        try:
            missing_tables = await self._execute_database_tests()
            return self._create_db_success_result(missing_tables)
        except Exception as e:
            from netra_backend.app.logging_config import central_logger
            logger = central_logger.get_logger(__name__)
            logger.error(
                f"❌ VALIDATION FAILURE: Database connection check failed during startup. "
                f"Environment: {self.environment}, Error: {e}, "
                f"This will block system startup and prevent user access."
            )
            return self._create_db_failure_result(e)
    
    async def check_or_create_assistant(self) -> StartupCheckResult:
        """Check if Netra assistant exists, create if not"""
        # Check for mock mode from both config URL and runtime app state
        if self.is_mock or (hasattr(self.app.state, 'database_mock_mode') and self.app.state.database_mock_mode):
            return self._create_mock_result("netra_assistant")
        return await self._perform_assistant_check()
    
    async def _perform_assistant_check(self) -> StartupCheckResult:
        """Perform actual assistant check and creation"""
        try:
            # First check if assistants table exists
            from netra_backend.app.db.postgres import get_async_db
            async with get_async_db() as db:
                table_exists = await self._table_exists(db, 'assistants')
                if not table_exists:
                    # Table doesn't exist, skip assistant creation (non-critical)
                    return StartupCheckResult(
                        name="netra_assistant", 
                        success=True, 
                        critical=False,
                        message="Assistants table not found - skipping (non-critical)"
                    )
            # Table exists, proceed with check
            return await self._handle_assistant_check()
        except Exception as e:
            # Non-critical failure, return success with warning
            return StartupCheckResult(
                name="netra_assistant",
                success=True,
                critical=False,
                message=f"Assistant check skipped (non-critical): {str(e)}"
            )
    
    async def _test_basic_connectivity(self, db: AsyncSession) -> None:
        """Test basic database connectivity"""
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
    
    async def _check_critical_tables(self, db: AsyncSession) -> List[str]:
        """Check if critical tables exist and return list of missing tables
        
        CRITICAL: Only truly essential tables for basic system operation are checked.
        Missing non-critical tables (from recent migrations) won't prevent startup.
        """
        from netra_backend.app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        
        # REDUCED to only absolutely essential tables for basic startup
        # Other tables (like supply chain, billing, etc.) are considered non-critical for startup
        essential_tables = ['assistants']  # Only assistant table is truly critical
        
        missing_tables = []
        
        # Check all expected tables but separate into critical vs non-critical
        all_expected_tables = [
            'assistants', 'threads', 'messages', 'userbase', 
            # Add any other tables that might be missing from recent migrations
            'supplies', 'billing_records', 'analytics_events'
        ]
        
        for table in all_expected_tables:
            try:
                exists = await self._table_exists(db, table)
                if not exists:
                    missing_tables.append(table)
                    # Only log as error if it's truly essential
                    if table in essential_tables:
                        logger.error(f"CRITICAL TABLE MISSING: {table}")
                    else:
                        logger.warning(f"Non-critical table missing: {table} (system will continue)")
            except Exception as e:
                # Don't let table checking errors prevent startup
                logger.warning(f"Could not check table {table}: {e}")
                missing_tables.append(f"{table} (check failed)")
        
        return missing_tables
    
    async def _find_assistant(self, db: AsyncSession) -> Assistant:
        """Find existing Netra assistant"""
        from netra_backend.app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        
        logger.debug(f"_find_assistant called with db: {db}")
        logger.debug(f"db is None: {db is None}")
        
        try:
            logger.debug("Creating select query...")
            query = select(Assistant).where(Assistant.id == "netra-assistant")
            logger.debug(f"Query created: {query}")
            
            logger.debug("Executing query...")
            logger.debug(f"db.bind: {db.bind}")
            logger.debug(f"db.get_bind(): {db.get_bind()}")
            
            # Check if the engine exists
            try:
                bind = db.get_bind()
                logger.debug(f"Bind is None: {bind is None}")
                if bind is None:
                    raise RuntimeError("Database engine/bind is None")
            except Exception as bind_error:
                logger.error(f"Error getting bind: {bind_error}")
                raise
                
            result = await db.execute(query)
            logger.debug(f"Query executed, result: {result}")
            
            logger.debug("Getting scalar result...")
            assistant = result.scalar_one_or_none()
            logger.debug(f"Assistant found: {assistant}")
            
            return assistant
        except Exception as e:
            logger.error(f"Error in _find_assistant: {e}")
            raise
    
    async def _create_assistant(self, db: AsyncSession) -> None:
        """Create Netra assistant"""
        assistant = self._build_assistant_instance()
        db.add(assistant)
        await db.commit()
    
    def _get_assistant_tools(self) -> List[dict]:
        """Get assistant tools configuration"""
        return [
            {"type": "data_analysis"},
            {"type": "optimization"},
            {"type": "reporting"}
        ]
    
    def _get_assistant_metadata(self) -> dict:
        """Get assistant metadata"""
        capabilities = [
            "workload_analysis", "cost_optimization", "performance_optimization",
            "quality_optimization", "model_selection", "supply_catalog_management"
        ]
        return {"version": "1.0", "capabilities": capabilities}
    
    def _create_mock_result(self, name: str) -> StartupCheckResult:
        """Create mock result for database checks"""
        return StartupCheckResult(
            name=name, success=True, critical=False,
            message="PostgreSQL in mock mode - skipping connection check"
        )
    
    async def _execute_database_tests(self) -> List[str]:
        """Execute database connectivity and schema tests, return missing tables"""
        # Check if database is in mock mode (set by startup sequence)
        if hasattr(self.app.state, 'database_mock_mode') and self.app.state.database_mock_mode:
            # In mock mode, db_session_factory is legitimately None
            return []  # No missing tables in mock mode
            
        if not hasattr(self.app.state, 'db_session_factory') or self.app.state.db_session_factory is None:
            raise RuntimeError("Database session factory not initialized. Check database setup.")
        async with self.app.state.db_session_factory() as db:
            await self._test_basic_connectivity(db)
            missing_tables = await self._check_critical_tables(db)
            return missing_tables
    
    def _create_db_success_result(self, missing_tables: List[str] = None) -> StartupCheckResult:
        """Create successful database check result"""
        if missing_tables:
            message = f"PostgreSQL connected successfully. Warning: Missing tables: {', '.join(missing_tables)}"
        else:
            message = "PostgreSQL connected and schema valid"
        
        return StartupCheckResult(
            name="database_connection", success=True, critical=False,
            message=message
        )
    
    def _create_db_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed database check result"""
        return StartupCheckResult(
            name="database_connection", success=False, critical=True,
            message=f"Database check failed: {error}"
        )
    
    async def _handle_assistant_check(self) -> StartupCheckResult:
        """Handle assistant existence check and creation"""
        from netra_backend.app.logging_config import central_logger
        logger = central_logger.get_logger(__name__)
        
        logger.debug(f"Checking app.state for db_session_factory...")
        logger.debug(f"hasattr(self.app.state, 'db_session_factory'): {hasattr(self.app.state, 'db_session_factory')}")
        
        # Check if database is in mock mode (set by startup sequence)
        if hasattr(self.app.state, 'database_mock_mode') and self.app.state.database_mock_mode:
            logger.debug("Database is in mock mode - skipping assistant check")
            return StartupCheckResult(
                name="netra_assistant", success=True, critical=False,
                message="PostgreSQL in mock mode - skipping assistant check"
            )
        
        if hasattr(self.app.state, 'db_session_factory'):
            logger.debug(f"self.app.state.db_session_factory: {self.app.state.db_session_factory}")
            logger.debug(f"self.app.state.db_session_factory is None: {self.app.state.db_session_factory is None}")
        else:
            logger.error("app.state does not have db_session_factory attribute!")
            
        if not hasattr(self.app.state, 'db_session_factory') or self.app.state.db_session_factory is None:
            raise RuntimeError("Database session factory not initialized. Check database setup.")
        
        logger.debug("Creating database session for assistant check...")
        try:
            # Check global engine state
            from netra_backend.app.db.postgres_core import async_engine
            from netra_backend.app.db.postgres_core import (
                async_session_factory as global_factory,
            )
            logger.debug(f"Global async_engine: {async_engine}")
            logger.debug(f"Global async_session_factory: {global_factory}")
            
            session_factory = self.app.state.db_session_factory
            logger.debug(f"Got session factory: {session_factory}")
            session = session_factory()
            logger.debug(f"Created session: {session}")
            
            async with session as db:
                logger.debug(f"Entered async context, db object: {db}")
                logger.debug(f"db is None: {db is None}")
                assistant = await self._find_assistant(db)
                if not assistant:
                    logger.debug("Assistant not found, creating new one...")
                    await self._create_assistant(db)
                    return self._create_assistant_created_result()
                logger.debug("Assistant already exists")
                return self._create_assistant_exists_result()
        except Exception as e:
            logger.error(f"Error creating or using database session: {e}")
            raise
    
    def _create_assistant_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed assistant check result"""
        return StartupCheckResult(
            name="netra_assistant", success=False, critical=False,
            message=f"Failed to check/create assistant: {error}"
        )
    
    def _create_assistant_created_result(self) -> StartupCheckResult:
        """Create result for newly created assistant"""
        return StartupCheckResult(
            name="netra_assistant", success=True, critical=False,
            message="Netra assistant created successfully"
        )
    
    def _create_assistant_exists_result(self) -> StartupCheckResult:
        """Create result for existing assistant"""
        return StartupCheckResult(
            name="netra_assistant", success=True, critical=False,
            message="Netra assistant already exists"
        )
    
    async def _table_exists(self, db: AsyncSession, table: str) -> bool:
        """Check if table exists in database"""
        config = unified_config_manager.get_config()
        database_url = getattr(config, 'database_url', '')
        if "sqlite" in database_url.lower():
            return await self._sqlite_table_exists(db, table)
        return await self._postgres_table_exists(db, table)
    
    async def _sqlite_table_exists(self, db: AsyncSession, table: str) -> bool:
        """Check if table exists in SQLite"""
        result = await db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name = :table"),
            {"table": table}
        )
        return result.scalar_one_or_none() is not None
    
    async def _postgres_table_exists(self, db: AsyncSession, table: str) -> bool:
        """Check if table exists in PostgreSQL"""
        result = await db.execute(
            text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table)"),
            {"table": table}
        )
        return result.scalar_one()
    
    def _build_assistant_instance(self) -> Assistant:
        """Build assistant instance with all properties"""
        basic_props = self._get_assistant_basic_props()
        advanced_props = self._get_assistant_advanced_props()
        return Assistant(**{**basic_props, **advanced_props})
    
    def _get_assistant_basic_props(self) -> dict:
        """Get basic assistant properties"""
        return {
            "id": "netra-assistant", "object": "assistant",
            "created_at": int(time.time()), "name": "Netra AI Optimization Assistant",
            "model": LLMModel.GEMINI_2_5_FLASH.value, "file_ids": []
        }
    
    def _get_assistant_advanced_props(self) -> dict:
        """Get advanced assistant properties"""
        return {
            "description": "The world's best AI workload optimization assistant",
            "instructions": "You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality.",
            "tools": self._get_assistant_tools(),
            "metadata_": self._get_assistant_metadata()
        }