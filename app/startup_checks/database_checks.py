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
    
    async def check_database_connection(self) -> StartupCheckResult:
        """Check PostgreSQL database connection and schema"""
        try:
            async with self.app.state.db_session_factory() as db:
                await self._test_basic_connectivity(db)
                await self._check_critical_tables(db)
                
                return StartupCheckResult(
                    name="database_connection",
                    success=True,
                    message="PostgreSQL connected and schema valid",
                    critical=not self.is_staging
                )
        except Exception as e:
            return StartupCheckResult(
                name="database_connection",
                success=False,
                message=f"Database check failed: {e}",
                critical=not self.is_staging
            )
    
    async def check_or_create_assistant(self) -> StartupCheckResult:
        """Check if Netra assistant exists, create if not"""
        try:
            async with self.app.state.db_session_factory() as db:
                assistant = await self._find_assistant(db)
                
                if not assistant:
                    await self._create_assistant(db)
                    return StartupCheckResult(
                        name="netra_assistant",
                        success=True,
                        message="Netra assistant created successfully",
                        critical=False
                    )
                else:
                    return StartupCheckResult(
                        name="netra_assistant",
                        success=True,
                        message="Netra assistant already exists",
                        critical=False
                    )
        except Exception as e:
            return StartupCheckResult(
                name="netra_assistant",
                success=False,
                message=f"Failed to check/create assistant: {e}",
                critical=False
            )
    
    async def _test_basic_connectivity(self, db: AsyncSession) -> None:
        """Test basic database connectivity"""
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
    
    async def _check_critical_tables(self, db: AsyncSession) -> None:
        """Check if critical tables exist"""
        critical_tables = ['assistants', 'threads', 'messages', 'userbase']
        
        for table in critical_tables:
            result = await db.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table)"),
                {"table": table}
            )
            exists = result.scalar_one()
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
        assistant = Assistant(
            id="netra-assistant",
            object="assistant",
            created_at=int(time.time()),
            name="Netra AI Optimization Assistant",
            description="The world's best AI workload optimization assistant",
            model="gpt-4",
            instructions="You are Netra AI Workload Optimization Assistant. You help users optimize their AI workloads for cost, performance, and quality.",
            tools=self._get_assistant_tools(),
            file_ids=[],
            metadata_=self._get_assistant_metadata()
        )
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
        return {
            "version": "1.0",
            "capabilities": [
                "workload_analysis",
                "cost_optimization",
                "performance_optimization",
                "quality_optimization",
                "model_selection",
                "supply_catalog_management"
            ]
        }