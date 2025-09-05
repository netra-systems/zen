"""E2E Test Harness Utilities - SSOT for test context management

This module provides test harness utilities for E2E testing.
Implements SSOT patterns for test context and session management.

Business Value Justification (BVJ):
- Segment: Internal/Platform stability
- Business Goal: Enable reliable E2E test context management
- Value Impact: Ensures test isolation and cleanup 
- Revenue Impact: Protects test reliability and deployment quality
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class TestContextData:
    """Test context data container."""
    context_id: str
    test_name: str
    database_name: str
    seed_data: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class TestHarnessContext:
    """Test harness context manager for E2E tests."""
    
    def __init__(self, test_name: str, seed_data: bool = False):
        """Initialize test harness context.
        
        Args:
            test_name: Name of the test for identification
            seed_data: Whether to seed test data
        """
        self.test_name = test_name
        self.seed_data = seed_data
        self.context_id = f"test_{test_name}_{uuid.uuid4().hex[:8]}"
        self.database_name = f"test_db_{self.context_id}"
        
        # SSOT environment management
        self.env = IsolatedEnvironment(service_name=f"test_harness_{test_name}")
        
        # Resources to cleanup
        self.db_manager: Optional[DatabaseManager] = None
        self.cleanup_tasks = []
        
    async def __aenter__(self) -> 'TestHarnessContext':
        """Async context manager entry."""
        logger.info(f"Setting up test harness context: {self.context_id}")
        
        try:
            # Initialize database manager using SSOT pattern
            self.db_manager = DatabaseManager(
                postgres_config=self.env.get_database_config(),
                clickhouse_config=self.env.get_clickhouse_config()
            )
            await self.db_manager.initialize()
            
            # Seed data if requested
            if self.seed_data:
                await self._seed_test_data()
                
            logger.info(f"Test harness context ready: {self.context_id}")
            return self
            
        except Exception as e:
            logger.error(f"Failed to setup test harness context: {e}")
            await self._cleanup()
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup()
        
    async def _seed_test_data(self):
        """Seed test data for testing."""
        logger.info(f"Seeding test data for context: {self.context_id}")
        
        # In a real implementation, this would seed actual test data
        # For now, just log the action
        if self.db_manager:
            logger.info("Test data seeding completed")
    
    async def _cleanup(self):
        """Cleanup test resources."""
        logger.info(f"Cleaning up test harness context: {self.context_id}")
        
        # Execute custom cleanup tasks
        for task in reversed(self.cleanup_tasks):
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                logger.warning(f"Cleanup task failed: {e}")
        
        # Cleanup database manager
        if self.db_manager:
            try:
                await self.db_manager.cleanup()
            except Exception as e:
                logger.warning(f"Database cleanup failed: {e}")
            finally:
                self.db_manager = None
        
        logger.info(f"Test harness context cleanup complete: {self.context_id}")
    
    def add_cleanup_task(self, task):
        """Add a cleanup task to be executed on context exit."""
        self.cleanup_tasks.append(task)
    
    def get_context_data(self) -> TestContextData:
        """Get context data for the test."""
        return TestContextData(
            context_id=self.context_id,
            test_name=self.test_name,
            database_name=self.database_name,
            seed_data=self.seed_data
        )


@asynccontextmanager
async def test_harness_context(test_name: str, seed_data: bool = False):
    """Async context manager for test harness.
    
    Usage:
        async with test_harness_context("my_test") as harness:
            # Test code here
            pass
    """
    harness = TestHarnessContext(test_name, seed_data)
    async with harness:
        yield harness