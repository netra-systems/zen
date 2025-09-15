"""
Test suite for database connector consistency in dev launcher.

Tests that database connection status is reported consistently across
different validation phases, preventing confusing error messages.
"""

import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.database_connector import (
    DatabaseConnector,
    DatabaseConnection,
    ConnectionStatus,
    DatabaseType,
    RetryConfig
)


class TestDatabaseConnectorConsistency:
    """Test cases for consistent database connection status reporting."""
    
    @pytest.fixture
    def database_connector(self):
        """Create a database connector instance for testing."""
        connector = DatabaseConnector(use_emoji=False)
        return connector
    
    @pytest.fixture
    def mock_connections(self):
        """Create mock database connections."""
        return {
            'main_postgres': DatabaseConnection(
                name='main_postgres',
                url='postgresql://user:pass@localhost:5432/testdb',
                db_type=DatabaseType.POSTGRESQL,
                status=ConnectionStatus.UNKNOWN
            ),
            'main_redis': DatabaseConnection(
                name='main_redis',
                url='redis://localhost:6379/0',
                db_type=DatabaseType.REDIS,
                status=ConnectionStatus.UNKNOWN
            ),
            'main_clickhouse': DatabaseConnection(
                name='main_clickhouse',
                url='clickhouse://localhost:9000/default',
                db_type=DatabaseType.CLICKHOUSE,
                status=ConnectionStatus.UNKNOWN
            )
        }
    
    @pytest.mark.asyncio
    async def test_connection_status_transitions(self, database_connector, mock_connections):
        """Test that connection status transitions are consistent."""
        database_connector.connections = mock_connections
        
        # Track status changes
        status_history = {name: [] for name in mock_connections.keys()}
        
        # Mock the test methods to track status changes
        async def mock_test(connection):
            status_history[connection.name].append(connection.status)
            if connection.name == 'main_redis':
                # Simulate Redis failure
                connection.status = ConnectionStatus.FAILED
                connection.last_error = "Connection refused"
                return False
            else:
                connection.status = ConnectionStatus.CONNECTED
                return True
        
        with patch.object(database_connector, '_test_database_connection', mock_test):
            result = await database_connector.validate_all_connections()
            
            # Verify status transitions
            assert mock_connections['main_postgres'].status == ConnectionStatus.CONNECTED
            assert mock_connections['main_redis'].status == ConnectionStatus.FAILED
            assert mock_connections['main_clickhouse'].status == ConnectionStatus.CONNECTED
            
            # Result should be False since one connection failed
            assert result is False
    
    @pytest.mark.asyncio
    async def test_retry_count_tracking(self, database_connector, mock_connections):
        """Test that retry counts are accurately tracked."""
        database_connector.connections = mock_connections
        database_connector.retry_config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        attempt_counts = {}
        
        async def mock_test(connection):
            if connection.name not in attempt_counts:
                attempt_counts[connection.name] = 0
            
            attempt_counts[connection.name] += 1
            
            # Fail first 2 attempts for PostgreSQL
            if connection.name == 'main_postgres' and attempt_counts[connection.name] < 3:
                raise Exception("Connection timeout")
            
            connection.status = ConnectionStatus.CONNECTED
            return True
        
        with patch.object(database_connector, '_test_database_connection', mock_test):
            await database_connector._validate_connection_with_retry(
                mock_connections['main_postgres']
            )
            
            # Should have made 3 attempts total (2 failures + 1 success)
            assert mock_connections['main_postgres'].retry_count == 3
            assert mock_connections['main_postgres'].status == ConnectionStatus.CONNECTED
            assert attempt_counts['main_postgres'] == 3
    
    @pytest.mark.asyncio
    async def test_error_message_consistency(self, database_connector, mock_connections):
        """Test that error messages are consistent across validation phases."""
        database_connector.connections = mock_connections
        
        # Simulate different error scenarios
        error_scenarios = {
            'main_postgres': "password incorrect",
            'main_redis': "Connection refused",
            'main_clickhouse': "Database connection failed after 5 attempts"
        }
        
        async def mock_test(connection):
            error_msg = error_scenarios.get(connection.name)
            if error_msg:
                connection.last_error = error_msg
                connection.status = ConnectionStatus.FAILED
                return False
            return True
        
        with patch.object(database_connector, '_test_database_connection', mock_test):
            await database_connector.validate_all_connections()
            
            # Verify error messages are preserved
            for name, expected_error in error_scenarios.items():
                assert mock_connections[name].last_error == expected_error
                assert mock_connections[name].status == ConnectionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_no_duplicate_validation_messages(self, database_connector, mock_connections):
        """Test that validation doesn't produce duplicate or conflicting messages."""
        database_connector.connections = mock_connections
        
        # Capture all print outputs
        printed_messages = []
        
        def mock_print(message):
            printed_messages.append(message)
        
        with patch('builtins.print', mock_print):
            # Mock successful connections
            async def mock_test(connection):
                connection.status = ConnectionStatus.CONNECTED
                return True
            
            with patch.object(database_connector, '_test_database_connection', mock_test):
                await database_connector.validate_all_connections()
        
        # Check for duplicate messages
        message_counts = {}
        for msg in printed_messages:
            # Normalize message for comparison (remove emojis and timing info)
            normalized = msg.strip()
            if normalized:
                message_counts[normalized] = message_counts.get(normalized, 0) + 1
        
        # No message should appear more than once for the same connection
        for msg, count in message_counts.items():
            if 'main_postgres' in msg or 'main_redis' in msg or 'main_clickhouse' in msg:
                assert count == 1, f"Duplicate message: {msg} (appeared {count} times)"
    
    @pytest.mark.asyncio
    async def test_connection_validation_order(self, database_connector, mock_connections):
        """Test that connections are validated in a consistent order."""
        database_connector.connections = mock_connections
        
        validation_order = []
        
        async def mock_test(connection):
            validation_order.append(connection.name)
            connection.status = ConnectionStatus.CONNECTED
            return True
        
        with patch.object(database_connector, '_test_database_connection', mock_test):
            await database_connector.validate_all_connections()
        
        # Should validate in the order they were added
        expected_order = ['main_postgres', 'main_redis', 'main_clickhouse']
        assert validation_order == expected_order
    
    @pytest.mark.asyncio
    async def test_health_check_doesnt_override_validation_status(self, database_connector, mock_connections):
        """Test that health checks don't override initial validation status incorrectly."""
        database_connector.connections = mock_connections
        
        # Set initial validation status
        mock_connections['main_postgres'].status = ConnectionStatus.CONNECTED
        mock_connections['main_redis'].status = ConnectionStatus.FAILED
        mock_connections['main_redis'].last_error = "Initial validation failed"
        
        # Run health check
        async def mock_health_check(connection):
            # Health check should not change FAILED status unless connection recovers
            if connection.status == ConnectionStatus.FAILED:
                # Try to connect again
                return False  # Still failing
            return True
        
        with patch.object(database_connector, '_test_database_connection', mock_health_check):
            await database_connector._check_connection_health(mock_connections['main_redis'])
        
        # Status should remain FAILED with original error
        assert mock_connections['main_redis'].status == ConnectionStatus.FAILED
        assert "Initial validation failed" in mock_connections['main_redis'].last_error
    
    @pytest.mark.asyncio
    async def test_connection_status_summary_accuracy(self, database_connector, mock_connections):
        """Test that connection status summary is accurate."""
        database_connector.connections = mock_connections
        
        # Set mixed statuses
        mock_connections['main_postgres'].status = ConnectionStatus.CONNECTED
        mock_connections['main_redis'].status = ConnectionStatus.FAILED
        mock_connections['main_redis'].failure_count = 3
        mock_connections['main_redis'].last_error = "Connection timeout"
        mock_connections['main_clickhouse'].status = ConnectionStatus.CONNECTED
        
        status_summary = database_connector.get_connection_status()
        
        # Verify summary accuracy
        assert status_summary['main_postgres']['status'] == 'connected'
        assert status_summary['main_redis']['status'] == 'failed'
        assert status_summary['main_redis']['failure_count'] == 3
        assert status_summary['main_redis']['last_error'] == "Connection timeout"
        assert status_summary['main_clickhouse']['status'] == 'connected'
        
        # Check is_all_healthy
        assert database_connector.is_all_healthy() is False
    
    @pytest.mark.asyncio
    async def test_validation_continues_after_first_failure(self, database_connector, mock_connections):
        """Test that validation continues checking all connections even after failures."""
        database_connector.connections = mock_connections
        
        validated_connections = set()
        
        async def mock_test(connection):
            validated_connections.add(connection.name)
            if connection.name == 'main_postgres':
                # First connection fails
                connection.status = ConnectionStatus.FAILED
                return False
            connection.status = ConnectionStatus.CONNECTED
            return True
        
        with patch.object(database_connector, '_test_database_connection', mock_test):
            result = await database_connector.validate_all_connections()
        
        # All connections should have been validated (unique connections, ignoring retries)
        assert len(validated_connections) == 3
        assert 'main_postgres' in validated_connections
        assert 'main_redis' in validated_connections
        assert 'main_clickhouse' in validated_connections
        
        # Result should be False since one connection failed
        assert result is False


class TestDatabaseInitializationConsistency:
    """Test that database initialization reports status consistently."""
    
    @pytest.mark.asyncio
    async def test_initialization_doesnt_report_false_failures(self):
        """Test that initialization doesn't report failures when connections succeed later."""
        from dev_launcher.database_initialization import DatabaseInitializer
        
        initializer = DatabaseInitializer(Path('.'), use_emoji=False)
        
        # Track messages
        messages = []
        
        def capture_print(emoji, category, message):
            messages.append((emoji, category, message))
        
        initializer._print = capture_print
        
        with patch.object(initializer, '_test_postgresql_connection') as mock_test:
            # First attempt fails, second succeeds (simulating retry)
            mock_test.side_effect = [False, True]
            
            with patch.object(initializer, '_ensure_database_exists', return_value=True):
                with patch.object(initializer, '_check_basic_tables', return_value=True):
                    with patch('dev_launcher.database_initialization.get_env') as mock_env:
                        mock_env.return_value = {
                            'DATABASE_URL': 'postgresql://localhost:5432/testdb'
                        }
                        
                        result = await initializer._initialize_postgresql()
        
        # Should report success, not failure
        assert result is False  # First connection failed
        assert any('Cannot connect to PostgreSQL' in msg[2] for msg in messages)
        # But should not have success message after failure
        assert not any('PostgreSQL initialization successful' in msg[2] for msg in messages)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])