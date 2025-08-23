"""
Database test helper functions.
Consolidates database-related helpers from across services.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import patch


def create_test_thread_data(
    thread_id: str = "test_thread_123",
    user_id: str = "test_user_001"
) -> Dict[str, Any]:
    """Create test thread data"""
    return {
        "id": thread_id,
        "user_id": user_id,
        "metadata_": {
            "user_id": user_id,
            "created_at": "2025-01-01T00:00:00Z"
        },
        "created_at": 1640995200,  # timestamp
        "object": "thread",
        "title": "Test Thread",
        "status": "active"
    }


def create_test_run_data(
    run_id: str = "test_run_123",
    thread_id: str = "test_thread_123"
) -> Dict[str, Any]:
    """Create test run data"""
    return {
        "id": run_id,
        "thread_id": thread_id,
        "status": "completed",
        "assistant_id": "test_assistant",
        "model": "gpt-4",
        "metadata_": {"user_id": "test_user_001"},
        "created_at": 1640995200,
        "completed_at": 1640995260,
        "object": "thread.run"
    }


def create_test_message_data(
    message_id: str = "test_message_123",
    thread_id: str = "test_thread_123"
) -> Dict[str, Any]:
    """Create test message data"""
    return {
        "id": message_id,
        "thread_id": thread_id,
        "role": "user",
        "content": "Test message content",
        "created_at": 1640995200,
        "object": "thread.message"
    }


def create_test_user_db_data(
    user_id: str = "test_user_123",
    email: str = "test@example.com"
) -> Dict[str, Any]:
    """Create test user database data"""
    return {
        "id": user_id,
        "email": email,
        "hashed_password": "test_hashed_password",
        "is_active": True,
        "is_superuser": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "last_login_at": None
    }


def setup_database_mocking():
    """Setup database mocking for tests"""
    from test_framework.mocks.database_mocks import (
        MockDatabaseSession,
        MockAsyncDatabaseFactory
    )
    
    mock_factory = MockAsyncDatabaseFactory()
    
    patches = [
        patch('netra_backend.app.services.database.unit_of_work.async_session_factory', mock_factory),
        patch('netra_backend.app.db.postgres_core.async_session_factory', mock_factory)
    ]
    
    return patches


def setup_test_data_fixtures():
    """Setup common test data fixtures"""
    fixtures = {
        "test_thread": create_test_thread_data(),
        "test_run": create_test_run_data(),
        "test_message": create_test_message_data(),
        "test_user": create_test_user_db_data()
    }
    return fixtures


class DatabaseTestHelpers:
    """Database test helper class with common operations"""
    
    @staticmethod
    def create_mock_query_result(data: List[Dict[str, Any]]):
        """Create mock query result"""
        from unittest.mock import MagicMock
        result = MagicMock()
        result.fetchall = lambda: data
        result.fetchone = lambda: data[0] if data else None
        result.rowcount = len(data)
        return result
    
    @staticmethod
    def setup_postgres_mocking():
        """Setup PostgreSQL specific mocking"""
        from test_framework.mocks.database_mocks import MockPostgreSQLConnection
        
        mock_connection = MockPostgreSQLConnection()
        return patch('asyncpg.connect', return_value=mock_connection)
    
    @staticmethod  
    def setup_clickhouse_mocking():
        """Setup ClickHouse specific mocking"""
        from test_framework.mocks.database_mocks import MockClickHouseConnection
        
        mock_connection = MockClickHouseConnection()
        return patch('netra_backend.app.db.clickhouse.get_client', return_value=mock_connection)
    
    @staticmethod
    def validate_database_operations(operations: List[Dict[str, Any]], expected_operations: List[str]):
        """Validate that expected database operations occurred"""
        operation_types = [op.get("type") for op in operations]
        for expected in expected_operations:
            assert expected in operation_types, f"Expected operation '{expected}' not found in {operation_types}"
    
    @staticmethod
    def create_test_migration_data() -> Dict[str, Any]:
        """Create test data for database migration testing"""
        return {
            "version": "001_initial_migration",
            "applied_at": "2025-01-01T00:00:00Z",
            "checksum": "abc123def456",
            "execution_time_ms": 150
        }
    
    @staticmethod
    def create_bulk_test_data(count: int = 100) -> List[Dict[str, Any]]:
        """Create bulk test data for performance testing"""
        return [
            {
                "id": f"test_record_{i}",
                "name": f"Test Record {i}",
                "value": i * 10,
                "created_at": "2025-01-01T00:00:00Z"
            }
            for i in range(count)
        ]


def assert_database_query_called(mock_session, query_substring: str):
    """Assert that a database query containing substring was called"""
    operations = mock_session.get_operations()
    query_operations = [op for op in operations if op.get("type") == "execute"]
    
    for operation in query_operations:
        if query_substring.lower() in operation.get("query", "").lower():
            return True
    
    raise AssertionError(f"Query containing '{query_substring}' was not executed")


def assert_database_insert_called(mock_session, expected_count: int = None):
    """Assert that database insert operations were called"""
    operations = mock_session.get_operations()
    insert_operations = [op for op in operations if op.get("type") == "add"]
    
    if expected_count is not None:
        assert len(insert_operations) == expected_count, \
            f"Expected {expected_count} inserts, but got {len(insert_operations)}"
    else:
        assert len(insert_operations) > 0, "No insert operations were performed"


def assert_transaction_committed(mock_session):
    """Assert that database transaction was committed"""
    operations = mock_session.get_operations()
    commit_operations = [op for op in operations if op.get("type") == "commit"]
    assert len(commit_operations) > 0, "Transaction was not committed"


def assert_transaction_rolled_back(mock_session):
    """Assert that database transaction was rolled back"""
    operations = mock_session.get_operations()
    rollback_operations = [op for op in operations if op.get("type") == "rollback"]
    assert len(rollback_operations) > 0, "Transaction was not rolled back"


# Utility functions for specific database testing patterns

def create_test_pagination_data(
    page: int = 1,
    page_size: int = 10,
    total_count: int = 100
) -> Dict[str, Any]:
    """Create test pagination data"""
    return {
        "page": page,
        "page_size": page_size, 
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size,
        "has_next": page * page_size < total_count,
        "has_previous": page > 1
    }


def create_test_filter_data() -> Dict[str, Any]:
    """Create test filter data for database queries"""
    return {
        "filters": {
            "status": "active",
            "created_after": "2025-01-01T00:00:00Z",
            "user_id": "test_user_123"
        },
        "sort_by": "created_at",
        "sort_order": "desc"
    }


def mock_database_connection_pool():
    """Mock database connection pool for testing"""
    from unittest.mock import AsyncMock
    
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    pool.release = AsyncMock()
    pool.close = AsyncMock()
    pool.get_size = lambda: 5
    pool.get_idle_size = lambda: 3
    
    return pool


async def setup_test_database_schema():
    """Setup test database schema (mock implementation)"""
    # Mock implementation - would normally create actual tables
    return {
        "tables_created": ["users", "threads", "runs", "messages"],
        "indexes_created": ["idx_users_email", "idx_threads_user_id"],
        "status": "success"
    }


def cleanup_test_database():
    """Cleanup test database (mock implementation)"""
    # Mock implementation - would normally drop test tables
    return {"status": "cleaned"}