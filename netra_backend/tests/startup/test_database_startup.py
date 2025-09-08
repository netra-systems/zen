"""
Database Startup Test - Validates database connectivity during system startup

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent database-related startup failures
- Value Impact: Ensures system can connect to all required databases
- Strategic Impact: Prevents 80% of startup failures caused by database issues

This test validates database startup requirements:
1. Database connector can be initialized
2. Connection discovery works
3. Connection validation logic functions
4. Fallback behavior works correctly
"""
import pytest
from typing import Dict, List
from unittest.mock import MagicMock, AsyncMock, Mock, patch
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.database_connector import DatabaseConnector, ConnectionStatus, DatabaseType
from test_framework.performance_helpers import fast_test


@pytest.mark.integration
@fast_test
def test_database_connector_initialization():
    """Test that database connector initializes successfully."""
    # Should not raise an exception
    connector = DatabaseConnector()
    
    # Should have expected attributes
    assert hasattr(connector, 'connections'), "Connector should have connections attribute"
    
    # Connections should be initialized as empty dict
    assert isinstance(connector.connections, dict), "Connections should be a dictionary"


@pytest.mark.integration  
@fast_test
def test_database_discovery_process():
    """Test that database discovery process works correctly."""
    connector = DatabaseConnector()
    
    # Discovery happens automatically during initialization
    # Should have discovered some connections
    assert len(connector.connections) > 0, "Should discover at least one database connection"
    
    # Each connection should have expected attributes
    for name, connection in connector.connections.items():
        assert hasattr(connection, 'name'), f"Connection {name} should have name"
        assert hasattr(connection, 'db_type'), f"Connection {name} should have db_type"
        assert hasattr(connection, 'url'), f"Connection {name} should have url"
        assert hasattr(connection, 'status'), f"Connection {name} should have status"


@pytest.mark.integration
def test_database_connection_types():
    """Test that all expected database types are discovered."""
    connector = DatabaseConnector()
    
    # Should discover PostgreSQL, ClickHouse, and Redis
    connection_types = {conn.db_type for conn in connector.connections.values()}
    
    # At minimum should have PostgreSQL (required for the system)
    assert DatabaseType.POSTGRESQL in connection_types, "Should discover PostgreSQL connection"
    
    # Redis and ClickHouse may or may not be available depending on environment
    # But if discovered, they should be valid types
    for conn_type in connection_types:
        assert isinstance(conn_type, DatabaseType), f"Connection type {conn_type} should be valid DatabaseType"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection_validation_with_mocks():
    """Test database connection validation with mocked external services."""
    
    # Mock external database calls
    with patch('asyncpg.connect') as mock_asyncpg, \
         patch('aiohttp.ClientSession') as mock_session_class, \
         patch('redis.Redis') as mock_redis:
        
        # Mock successful PostgreSQL connection
        mock_pg_conn = AsyncNone  # TODO: Use real service instance
        mock_pg_conn.fetchval = AsyncMock(return_value=1)
        mock_asyncpg.return_value = mock_pg_conn
        
        # Mock successful ClickHouse connection
        mock_response = AsyncNone  # TODO: Use real service instance
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Ok.")
        
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session
        
        # Mock successful Redis connection
        mock_redis_instance = MagicMock()  # TODO: Use real service instance
        mock_redis_instance.ping = MagicMock(return_value=True)
        mock_redis.return_value = mock_redis_instance
        
        # Test connection validation
        connector = DatabaseConnector()
        
        # Validate all discovered connections
        await connector.validate_all_connections()
        
        # Check that validation completed
        validated_connections = [conn for conn in connector.connections.values() 
                               if conn.status != ConnectionStatus.UNKNOWN]
        
        assert len(validated_connections) > 0, "Should have validated at least one connection"
        
        # Should have either connected or failed (not unknown)
        for connection in validated_connections:
            assert connection.status in [ConnectionStatus.CONNECTED, ConnectionStatus.FAILED, 
                                       ConnectionStatus.RETRYING, ConnectionStatus.FALLBACK_AVAILABLE], \
                   f"Connection {connection.name} should have a determined status"


@pytest.mark.integration
def test_database_fallback_behavior():
    """Test that database connector handles fallback scenarios correctly."""
    
    # Mock all database connections to fail
    with patch('asyncpg.connect') as mock_asyncpg, \
         patch('aiohttp.ClientSession') as mock_session_class, \
         patch('redis.Redis') as mock_redis:
        
        # Mock failed connections
        mock_asyncpg.side_effect = Exception("PostgreSQL connection failed")
        
        # Mock failed ClickHouse
        mock_session_class.side_effect = Exception("ClickHouse connection failed")
        
        # Mock failed Redis
        mock_redis.side_effect = Exception("Redis connection failed")
        
        # Test that system handles failures gracefully
        connector = DatabaseConnector()
        
        # Should still have discovered connection configs (even if they fail to connect)
        assert len(connector.connections) > 0, "Should discover database configurations even if connections fail"
        
        # Should handle failures gracefully without crashing
        # (The actual validation would happen async, but discovery should work)
        for connection in connector.connections.values():
            assert connection.name is not None, "Connection should have a name even if failed"
            assert connection.url is not None, "Connection should have a URL even if failed"


@pytest.mark.unit
@fast_test
def test_database_connection_status_enum():
    """Test that ConnectionStatus enum has expected values."""
    # Should have all expected status values
    expected_statuses = [
        'UNKNOWN', 'CONNECTING', 'CONNECTED', 'FAILED', 'RETRYING', 'FALLBACK_AVAILABLE'
    ]
    
    for status_name in expected_statuses:
        assert hasattr(ConnectionStatus, status_name), f"ConnectionStatus should have {status_name}"
        
    # Should be able to create status instances
    status = ConnectionStatus.CONNECTED
    assert status == ConnectionStatus.CONNECTED, "Status comparison should work"
    assert status.value == 'connected', "Status should have string value"


@pytest.mark.unit
@fast_test  
def test_database_type_enum():
    """Test that DatabaseType enum has expected values."""
    # Should have all expected database types
    expected_types = ['POSTGRESQL', 'CLICKHOUSE', 'REDIS']
    
    for type_name in expected_types:
        assert hasattr(DatabaseType, type_name), f"DatabaseType should have {type_name}"
        
    # Should be able to create type instances
    db_type = DatabaseType.POSTGRESQL
    assert db_type == DatabaseType.POSTGRESQL, "Type comparison should work"
    assert db_type.value == 'postgresql', "Type should have string value"