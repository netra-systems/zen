"""
Validation tests for db_fixtures module.
Tests compliance with 8-line function limit and functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from app.tests.test_utilities.db_fixtures import (
    SessionBuilder, create_mock_session, DatabaseErrorSimulator,
    ClickHouseQueryMocker, create_repository_mock, create_mock_user,
    with_async_transaction, assert_session_operations
)


def test_session_builder_fluent_interface():
    """Test SessionBuilder fluent interface pattern."""
    session = (SessionBuilder()
               .with_transactions()
               .with_repository_mocks()
               .build())
    
    assert session is not None
    assert hasattr(session, 'begin')
    assert hasattr(session, 'commit')


def test_create_mock_session_basic():
    """Test basic mock session creation."""
    session = create_mock_session()
    
    assert session is not None
    assert hasattr(session, 'add')
    assert hasattr(session, 'commit')
    assert hasattr(session, 'rollback')


def test_database_error_simulator():
    """Test database error simulation."""
    session = create_mock_session()
    simulator = DatabaseErrorSimulator(session)
    
    simulator.integrity_error('commit')
    
    with pytest.raises(Exception):
        session.commit.side_effect()


def test_clickhouse_query_mocker():
    """Test ClickHouse query mocking."""
    mocker = ClickHouseQueryMocker()
    
    mocker.mock_query("SELECT", [{"id": 1, "value": "test"}])
    
    result = asyncio.run(mocker.execute("SELECT * FROM test"))
    assert result == [{"id": 1, "value": "test"}]


def test_repository_mock_creation():
    """Test repository mock with CRUD operations."""
    repo = create_repository_mock()
    
    assert hasattr(repo, 'create')
    assert hasattr(repo, 'get_by_id')
    assert hasattr(repo, 'update')
    assert hasattr(repo, 'delete')


def test_model_factory_user():
    """Test user model factory."""
    user = create_mock_user(email="test@test.com")
    
    assert user.email == "test@test.com"
    assert hasattr(user, 'id')
    assert hasattr(user, 'full_name')


async def test_async_transaction_helper():
    """Test async transaction helper function."""
    session = create_mock_session()
    
    async def test_operation(session):
        return "operation_result"
    
    result = await with_async_transaction(session, test_operation)
    assert result == "operation_result"


def test_session_operations_assertion():
    """Test session operations assertion helper."""
    session = create_mock_session()
    session.commit.call_count = 2
    session.rollback.call_count = 1
    
    assert_session_operations(session, {"commit": 2, "rollback": 1})


def test_function_line_limits():
    """Test that all functions in db_fixtures are ≤8 lines."""
    import inspect
    from app.tests.test_utilities import db_fixtures
    
    for name, obj in inspect.getmembers(db_fixtures):
        if inspect.isfunction(obj):
            source_lines = inspect.getsource(obj).strip().split('\n')
            # Remove docstring and empty lines for core logic count
            code_lines = [line for line in source_lines 
                         if line.strip() and not line.strip().startswith('"""')]
            
            # Allow for function signature + 7 implementation lines
            assert len(code_lines) <= 8, f"Function {name} has {len(code_lines)} lines, max is 8"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])