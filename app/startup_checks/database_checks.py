"""
Database Checks

Handles database connectivity and schema validation.
Maintains 8-line function limit and focused responsibility.
"""

import os
import time
from typing import List
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import Assistant
from .models import StartupCheckResult


class DatabaseChecker:
    """Handles database connectivity and schema checks"""
    
    def __init__(self, app):
        self.app = app
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.is_staging = self.environment == "staging" or os.getenv("K_SERVICE")
        self.is_mock = "mock" in os.getenv("DATABASE_URL", "").lower()
    
    async def check_database_connection(self) -> StartupCheckResult:
        """Check PostgreSQL database connection and schema"""
        if self.is_mock:
            return self._create_mock_result("database_connection")
        return await self._perform_database_connection_check()
    
    async def _perform_database_connection_check(self) -> StartupCheckResult:
        """Perform actual database connection check"""
        try:
            await self._execute_database_tests()
            return self._create_db_success_result()
        except Exception as e:
            return self._create_db_failure_result(e)
    
    async def check_or_create_assistant(self) -> StartupCheckResult:
        """Check if Netra assistant exists, create if not"""
        if self.is_mock:
            return self._create_mock_result("netra_assistant")
        return await self._perform_assistant_check()
    
    async def _perform_assistant_check(self) -> StartupCheckResult:
        """Perform actual assistant check and creation"""
        try:
            return await self._handle_assistant_check()
        except Exception as e:
            return self._create_assistant_failure_result(e)
    
    async def _test_basic_connectivity(self, db: AsyncSession) -> None:
        """Test basic database connectivity"""
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
    
    async def _check_critical_tables(self, db: AsyncSession) -> None:
        """Check if critical tables exist"""
        critical_tables = ['assistants', 'threads', 'messages', 'userbase']
        
        for table in critical_tables:
            exists = await self._table_exists(db, table)
            if not exists:
                raise ValueError(f"Critical table '{table}' does not exist")
    
    async def _find_assistant(self, db: AsyncSession) -> Assistant:
        """Find existing Netra assistant"""
        result = await db.execute(
            select(Assistant).where(Assistant.id == "netra-assistant")
        )
        return result.scalar_one_or_none()
    
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
    
    async def _execute_database_tests(self) -> None:
        """Execute database connectivity and schema tests"""
        async with self.app.state.db_session_factory() as db:
            await self._test_basic_connectivity(db)
            await self._check_critical_tables(db)
    
    def _create_db_success_result(self) -> StartupCheckResult:
        """Create successful database check result"""
        return StartupCheckResult(
            name="database_connection", success=True, critical=not self.is_staging,
            message="PostgreSQL connected and schema valid"
        )
    
    def _create_db_failure_result(self, error: Exception) -> StartupCheckResult:
        """Create failed database check result"""
        return StartupCheckResult(
            name="database_connection", success=False, critical=not self.is_staging,
            message=f"Database check failed: {error}"
        )
    
    async def _handle_assistant_check(self) -> StartupCheckResult:
        """Handle assistant existence check and creation"""
        async with self.app.state.db_session_factory() as db:
            assistant = await self._find_assistant(db)
            if not assistant:
                await self._create_assistant(db)
                return self._create_assistant_created_result()
            return self._create_assistant_exists_result()
    
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
        if "sqlite" in os.getenv("DATABASE_URL", "").lower():
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
            "model": "gpt-4", "file_ids": []
        }
    
    def _get_assistant_advanced_props(self) -> dict:
        """Get advanced assistant properties"""
        return {
            "description": "The world's best AI workload optimization assistant",
            "instructions": "You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality.",
            "tools": self._get_assistant_tools(),
            "metadata_": self._get_assistant_metadata()
        }