"""
ClickHouse Test Fixtures - Mock implementations for testing

Provides MockClickHouseDatabase and related mock classes for testing
when ClickHouse is not available or when explicit testing is required.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable reliable testing without external dependencies
- Value Impact: 100% test coverage and reliability in CI/CD environments
- Strategic Impact: Prevents test failures due to external service issues
"""

import time
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger as logger


class MockClickHouseDatabase:
    """Mock ClickHouse client for testing and local development.
    
    Returns empty results without connecting to real database.
    ONLY used when explicitly configured for testing.
    """
    
    def __init__(self):
        """Initialize mock client with tracking."""
        self._is_mock = True
        self.query_count = 0
        self.last_query_time = time.time()
    
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query - returns empty results in mock mode."""
        self.query_count += 1
        self.last_query_time = time.time()
        logger.debug(f"[MOCK ClickHouse] Query: {query[:100]}...")
        return []
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute parameterized query - returns empty results in mock mode."""
        self.query_count += 1
        self.last_query_time = time.time()
        logger.debug(f"[MOCK ClickHouse] Parameterized: {query[:100]}...")
        return []
    
    async def fetch(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetch data - returns empty results in mock mode."""
        self.query_count += 1
        self.last_query_time = time.time()
        logger.debug(f"[MOCK ClickHouse] Fetch: {query[:100]}...")
        return []
    
    async def disconnect(self):
        """Disconnect - no-op for mock client."""
        logger.debug("[MOCK ClickHouse] Disconnect called")
    
    async def test_connection(self) -> bool:
        """Test connection - always succeeds for mock client."""
        logger.debug("[MOCK ClickHouse] Connection test (mock)")
        return True
    
    def ping(self) -> bool:
        """Ping - always succeeds for mock client."""
        logger.debug("[MOCK ClickHouse] Ping (mock)")
        return True
    
    async def check_health(self) -> Dict[str, Any]:
        """Check health - always healthy for mock client."""
        logger.debug("[MOCK ClickHouse] Health check (mock)")
        return {
            "status": "healthy",
            "mode": "mock",
            "queries_executed": self.query_count,
            "last_query": self.last_query_time
        }
    
    async def command(self, cmd: str, parameters: Optional[Dict[str, Any]] = None, 
                     settings: Optional[Dict[str, Any]] = None) -> Any:
        """Execute command - no-op for mock client."""
        logger.debug(f"[MOCK ClickHouse] Command: {cmd[:100]}...")
        return None
    
    async def insert_data(self, table: str, data: List[List[Any]], column_names: Optional[List[str]] = None) -> None:
        """Mock insert_data method - logs operation (matches clickhouse_base.py signature)."""
        self.query_count += 1
        self.last_query_time = time.time()
        logger.debug(f"[MOCK ClickHouse] Insert data to {table}: {len(data)} rows, columns: {column_names}")
    
    async def batch_insert(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Mock batch insert - logs operation."""
        logger.debug(f"[MOCK ClickHouse] Batch insert to {table_name}: {len(data)} rows")
    
    async def cleanup(self) -> None:
        """Mock cleanup (alias for disconnect)."""
        await self.disconnect()
    
    def get_mock_stats(self) -> Dict[str, Any]:
        """Get mock client statistics."""
        return {
            "query_count": self.query_count,
            "last_query_time": self.last_query_time,
            "mode": "mock",
            "is_mock": True
        }


# Backward compatibility aliases removed - use MockClickHouseDatabase directly