"""
Database helpers for test framework.

Provides database session and utility functions for tests.
"""

from test_framework.fixtures import get_test_db_session


def get_clickhouse_test_client():
    """
    Get ClickHouse test client.
    
    Returns mock ClickHouse client for testing migration scenarios.
    """
    from unittest.mock import AsyncMock
    
    class ClickHouseTestClient:
        def __init__(self):
            self.connection = AsyncMock()
            self.connection.execute = AsyncMock(return_value=[])
            self.connection.insert = AsyncMock(return_value=True)
            self.connection.close = AsyncMock()
            
        async def __aenter__(self):
            return self.connection
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.connection.close()
    
    return ClickHouseTestClient()


__all__ = [
    "get_test_db_session",
    "get_clickhouse_test_client",
]