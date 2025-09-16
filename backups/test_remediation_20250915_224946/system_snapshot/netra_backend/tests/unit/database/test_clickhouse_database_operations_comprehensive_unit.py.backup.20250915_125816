"""
Comprehensive Unit Tests for ClickHouse Database Operations

Business Value Justification (BVJ):
- Segment: All (Platform/Internal, Enterprise data analytics)
- Business Goal: Ensure reliable data storage and retrieval for analytics
- Value Impact: Data integrity protects customer analytics and business intelligence
- Strategic Impact: Core database operations enable platform scalability and analytics features

This test suite validates:
1. Connection management and validation
2. Query execution and parameter handling 
3. Data insertion and batch operations
4. Error handling and timeout management
5. Environment-specific configuration
6. Database health monitoring
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict, List, Optional

# Test the actual ClickHouse database class
from netra_backend.app.db.clickhouse_base import ClickHouseDatabase
from test_framework.fixtures.database_fixtures import test_db_session
from shared.isolated_environment import get_env


class TestClickHouseDatabaseOperationsUnit:
    """Unit tests for ClickHouse database operations."""
    
    @pytest.mark.unit
    def test_connection_parameter_validation_success(self):
        """Test valid connection parameters are accepted."""
        # Valid parameters should not raise exceptions
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password",
            secure=False
        )
        
        assert db.host == "localhost"
        assert db.port == 8123
        assert db.database == "test_db"
        assert db.user == "default"
        assert db.password == "password"
        assert db.secure is False
    
    @pytest.mark.unit
    def test_connection_parameter_validation_control_characters(self):
        """Test validation rejects control characters in parameters."""
        # Test control characters in different parameters
        invalid_params = [
            {"host": "local\nhost", "error_part": "host contains newline"},
            {"database": "test\rdb", "error_part": "database contains carriage return"},
            {"user": "user\tname", "error_part": "user contains tab"},
            {"password": "pass\x00word", "error_part": "password contains control character"},
        ]
        
        for params in invalid_params:
            base_params = {
                "host": "localhost",
                "port": 8123,
                "database": "test_db", 
                "user": "default",
                "password": "password",
                "secure": False
            }
            base_params.update({k: v for k, v in params.items() if k != "error_part"})
            
            with pytest.raises(ValueError) as exc_info:
                ClickHouseDatabase(**base_params)
            
            assert params["error_part"] in str(exc_info.value)
    
    @pytest.mark.unit
    def test_connection_parameter_validation_port_range(self):
        """Test port validation for valid range."""
        invalid_ports = [0, -1, 65536, 99999, "8123", None]
        
        for invalid_port in invalid_ports:
            with pytest.raises(ValueError) as exc_info:
                ClickHouseDatabase(
                    host="localhost",
                    port=invalid_port,
                    database="test_db",
                    user="default",
                    password="password"
                )
            
            assert "port must be integer between 1-65535" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_connection_parameter_validation_empty_host(self):
        """Test validation rejects empty or whitespace host."""
        invalid_hosts = ["", "   ", "\t", "\n"]
        
        for invalid_host in invalid_hosts:
            with pytest.raises(ValueError) as exc_info:
                ClickHouseDatabase(
                    host=invalid_host,
                    port=8123,
                    database="test_db",
                    user="default", 
                    password="password"
                )
            
            assert "host cannot be empty" in str(exc_info.value)
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_environment_aware_timeout_configuration_staging(self, mock_get_client):
        """Test environment-aware timeout configuration for staging."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_get_client.return_value = mock_client
        
        with patch.object(get_env(), 'get', side_effect=lambda key, default=None: 
                         "staging" if key == "ENVIRONMENT" else default):
            
            db = ClickHouseDatabase(
                host="localhost",
                port=8123,
                database="test_db",
                user="default",
                password="password"
            )
            
            # Verify staging-specific timeouts were used
            mock_get_client.assert_called_once_with(
                host="localhost",
                port=8123,
                database="test_db",
                username="default",
                password="password",
                secure=False,
                connect_timeout=15,  # Staging timeout
                send_receive_timeout=30  # Staging timeout
            )
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_environment_aware_timeout_configuration_production(self, mock_get_client):
        """Test environment-aware timeout configuration for production."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_get_client.return_value = mock_client
        
        with patch.object(get_env(), 'get', side_effect=lambda key, default=None:
                         "production" if key == "ENVIRONMENT" else default):
            
            db = ClickHouseDatabase(
                host="localhost",
                port=8123,
                database="test_db",
                user="default",
                password="password"
            )
            
            # Verify production-specific timeouts were used
            mock_get_client.assert_called_once_with(
                host="localhost",
                port=8123,
                database="test_db", 
                username="default",
                password="password",
                secure=False,
                connect_timeout=20,  # Production timeout
                send_receive_timeout=45  # Production timeout
            )
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_environment_aware_timeout_configuration_development(self, mock_get_client):
        """Test environment-aware timeout configuration for development."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_get_client.return_value = mock_client
        
        with patch.object(get_env(), 'get', side_effect=lambda key, default=None:
                         "development" if key == "ENVIRONMENT" else default):
            
            db = ClickHouseDatabase(
                host="localhost",
                port=8123,
                database="test_db",
                user="default",
                password="password"
            )
            
            # Verify development-specific timeouts were used
            mock_get_client.assert_called_once_with(
                host="localhost",
                port=8123,
                database="test_db",
                username="default",
                password="password", 
                secure=False,
                connect_timeout=3,   # Development timeout
                send_receive_timeout=5  # Development timeout
            )
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_connection_failure_with_context(self, mock_get_client):
        """Test connection failure provides environment context."""
        mock_get_client.side_effect = Exception("Connection refused")
        
        with patch.object(get_env(), 'get', side_effect=lambda key, default=None:
                         "staging" if key == "ENVIRONMENT" else default):
            
            with pytest.raises(ConnectionError) as exc_info:
                ClickHouseDatabase(
                    host="localhost",
                    port=8123,
                    database="test_db",
                    user="default",
                    password="password"
                )
            
            error_msg = str(exc_info.value)
            assert "Could not connect to ClickHouse in staging environment" in error_msg
            assert "ClickHouse infrastructure may not be available" in error_msg
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_optional_connection_in_staging_when_not_required(self, mock_get_client):
        """Test connection is optional in staging when CLICKHOUSE_REQUIRED=false."""
        with patch.object(get_env(), 'get', side_effect=lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "CLICKHOUSE_REQUIRED": "false"
        }.get(key, default)):
            
            db = ClickHouseDatabase(
                host="localhost", 
                port=8123,
                database="test_db",
                user="default",
                password="password"
            )
            
            # Should not attempt connection when not required
            mock_get_client.assert_not_called()
            assert db.client is None
    
    @pytest.mark.unit
    async def test_execute_query_without_connection(self):
        """Test execute_query raises error when not connected."""
        with patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError):
                db = ClickHouseDatabase(
                    host="localhost",
                    port=8123,
                    database="test_db", 
                    user="default",
                    password="password"
                )
        
        # Manually set client to None to simulate no connection
        db.client = None
        
        with pytest.raises(ConnectionError) as exc_info:
            await db.execute_query("SELECT 1")
        
        assert "Not connected to ClickHouse" in str(exc_info.value)
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_execute_query_with_parameters(self, mock_get_client):
        """Test execute_query with parameters and settings."""
        # Setup mock
        mock_client = Mock()
        mock_result = Mock()
        mock_result.named_results.return_value = [{"result": 1}]
        mock_client.query.return_value = mock_result
        mock_client.ping = Mock()
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123, 
            database="test_db",
            user="default",
            password="password"
        )
        
        # Test query execution
        query = "SELECT * FROM users WHERE id = {id:UInt32}"
        parameters = {"id": 123}
        settings = {"max_threads": 2}
        
        result = await db.execute_query(query, parameters, settings)
        
        # Verify the call was made correctly
        mock_client.query.assert_called_once_with(query, parameters=parameters, settings=settings)
        assert result == [{"result": 1}]
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_insert_data_operation(self, mock_get_client):
        """Test data insertion operation."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_client.insert = Mock()
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        # Test data insertion
        table = "test_table"
        data = [["value1", "value2"], ["value3", "value4"]]
        column_names = ["col1", "col2"]
        
        await db.insert_data(table, data, column_names)
        
        # Verify insertion was called correctly
        mock_client.insert.assert_called_once_with(table, data, column_names=column_names)
    
    @pytest.mark.unit
    async def test_insert_data_without_connection(self):
        """Test insert_data raises error when not connected."""
        with patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError):
                db = ClickHouseDatabase(
                    host="localhost",
                    port=8123,
                    database="test_db",
                    user="default", 
                    password="password"
                )
        
        db.client = None
        
        with pytest.raises(ConnectionError) as exc_info:
            await db.insert_data("table", [["data"]], ["column"])
        
        assert "Not connected to ClickHouse" in str(exc_info.value)
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_command_execution(self, mock_get_client):
        """Test command execution with parameters and settings."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_client.command = Mock(return_value="OK")
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db", 
            user="default",
            password="password"
        )
        
        # Test command execution
        cmd = "CREATE TABLE test (id UInt32) ENGINE = Memory"
        parameters = {"table_name": "test"}
        settings = {"allow_experimental": 1}
        
        result = await db.command(cmd, parameters, settings)
        
        # Verify command was executed correctly
        mock_client.command.assert_called_once_with(cmd, parameters=parameters, settings=settings)
        assert result == "OK"
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_test_connection_with_timeout(self, mock_get_client):
        """Test connection testing with environment-aware timeout."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_result = Mock()
        mock_result.named_results.return_value = [{"result": 1}]
        mock_client.query.return_value = mock_result
        mock_get_client.return_value = mock_client
        
        with patch.object(get_env(), 'get', side_effect=lambda key, default=None:
                         "staging" if key == "ENVIRONMENT" else default):
            
            db = ClickHouseDatabase(
                host="localhost",
                port=8123,
                database="test_db",
                user="default",
                password="password"
            )
            
            # Test connection
            result = await db.test_connection()
            
            # Should succeed in staging with longer timeout
            assert result is True
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_test_connection_timeout_error(self, mock_get_client):
        """Test connection test handles timeout gracefully."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_client.query.side_effect = asyncio.TimeoutError("Connection timeout")
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        # Mock asyncio.wait_for to raise TimeoutError
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            result = await db.test_connection()
            
            assert result is False
    
    @pytest.mark.unit 
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_ping_operation(self, mock_get_client):
        """Test ping operation."""
        mock_client = Mock()
        mock_client.ping = Mock(return_value=True)
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        # Test successful ping
        result = db.ping()
        assert result is True
        mock_client.ping.assert_called_once()
    
    @pytest.mark.unit
    def test_ping_without_connection(self):
        """Test ping raises error when not connected."""
        with patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError):
                db = ClickHouseDatabase(
                    host="localhost",
                    port=8123,
                    database="test_db",
                    user="default",
                    password="password"
                )
        
        db.client = None
        
        with pytest.raises(ConnectionError) as exc_info:
            db.ping()
        
        assert "Not connected to ClickHouse" in str(exc_info.value)
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    def test_ping_exception_handling(self, mock_get_client):
        """Test ping handles exceptions gracefully."""
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Network error")
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        # Should return False on exception, not raise
        result = db.ping()
        assert result is False
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_log_entry_insertion(self, mock_get_client):
        """Test log entry insertion with proper data preparation."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_client.insert = Mock()
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        # Create mock log entry
        log_entry = Mock()
        log_entry.trace_id = "trace123"
        log_entry.span_id = "span456"
        log_entry.event = "test_event"
        log_entry.data = {"key": "value"}
        log_entry.source = "test_source"
        log_entry.user_id = "user789"
        
        table_name = "logs"
        
        await db.insert_log(log_entry, table_name)
        
        # Verify the insert was called with correct data
        expected_data = [["trace123", "span456", "test_event", '{"key": "value"}', "test_source", "user789"]]
        expected_columns = ['trace_id', 'span_id', 'event', 'data', 'source', 'user_id']
        
        mock_client.insert.assert_called_once_with(table_name, expected_data, column_names=expected_columns)
    
    @pytest.mark.unit
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_disconnect_operation(self, mock_get_client):
        """Test disconnect operation."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_client.close = Mock()
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        await db.disconnect()
        
        # Verify disconnect was called and client is cleared
        mock_client.close.assert_called_once()
        assert db.client is None
    
    @pytest.mark.unit
    async def test_disconnect_without_connection(self):
        """Test disconnect when no connection exists."""
        with patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError):
                db = ClickHouseDatabase(
                    host="localhost",
                    port=8123,
                    database="test_db",
                    user="default",
                    password="password"
                )
        
        db.client = None
        
        # Should not raise error when disconnecting without connection
        await db.disconnect()
        assert db.client is None
    
    @pytest.mark.unit 
    @patch('netra_backend.app.db.clickhouse_base.clickhouse_connect.get_client')
    async def test_execute_alias_for_execute_query(self, mock_get_client):
        """Test execute method is alias for execute_query."""
        mock_client = Mock()
        mock_client.ping = Mock()
        mock_result = Mock()
        mock_result.named_results.return_value = [{"test": "data"}]
        mock_client.query.return_value = mock_result
        mock_get_client.return_value = mock_client
        
        db = ClickHouseDatabase(
            host="localhost",
            port=8123,
            database="test_db",
            user="default",
            password="password"
        )
        
        # Test that execute and execute_query produce same results
        query = "SELECT 1"
        params = {"param": "value"}
        settings = {"setting": "value"}
        
        result1 = await db.execute(query, params, settings)
        result2 = await db.execute_query(query, params, settings)
        
        assert result1 == result2
        assert result1 == [{"test": "data"}]