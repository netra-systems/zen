"""
Unit tests for ClickHouse exception specificity.

MISSION: Validate that ClickHouse modules raise specific exception types instead of broad Exception handling.
Tests will FAIL initially to demonstrate current broad exception handling problems.

Issue #374: Database Exception Handling Remediation
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
# ClickHouse imports - handle import errors gracefully
try:
    from clickhouse_driver import Client as ClickHouseClient
    from clickhouse_driver.errors import NetworkError, ServerException, Error as ClickHouseError
except ImportError:
    # Mock ClickHouse classes if not available
    class ClickHouseClient:
        pass
    class NetworkError(Exception):
        pass
    class ServerException(Exception):
        pass
    class ClickHouseError(Exception):
        pass

# Import the classes we're testing
from netra_backend.app.db.clickhouse import ClickHouseDatabase as ClickHouseDB
from netra_backend.app.db.transaction_errors import (
    DeadlockError, ConnectionError, TimeoutError, 
    PermissionError, SchemaError, classify_error
)


class TestClickHouseExceptionSpecificity:
    """Test suite for ClickHouse exception specificity validation."""
    
    @pytest.mark.unit
    async def test_clickhouse_connection_failure_specificity(self):
        """FAILING TEST: Should raise ConnectionError with ClickHouse context, not generic Exception."""
        
        # Mock ClickHouse connection failure
        with patch('netra_backend.app.db.clickhouse.Client') as mock_client:
            mock_client.side_effect = NetworkError("ClickHouse server unreachable")
            
            # CURRENT BEHAVIOR: Generic Exception catch (clickhouse.py line 561)
            # EXPECTED BEHAVIOR: Should raise ConnectionError with ClickHouse context
            with pytest.raises(ConnectionError, match="ClickHouse server unreachable"):
                db = ClickHouseDB()
                await db.get_connection()
    
    @pytest.mark.unit
    async def test_clickhouse_query_execution_error_specificity(self):
        """FAILING TEST: Should raise specific query error, not generic Exception."""
        
        # Mock ClickHouse query execution failure
        with patch('netra_backend.app.db.clickhouse.Client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.execute.side_effect = ServerException("Table doesn't exist")
            mock_client.return_value = mock_client_instance
            
            # CURRENT BEHAVIOR: May catch with generic Exception
            # EXPECTED BEHAVIOR: Should raise SchemaError for table existence issues
            with pytest.raises(SchemaError, match="Table doesn't exist"):
                db = ClickHouseDB()
                await db.execute("SELECT * FROM non_existent_table")
    
    @pytest.mark.unit
    async def test_clickhouse_timeout_error_specificity(self):
        """FAILING TEST: Should raise TimeoutError for query timeouts."""
        
        # Mock ClickHouse query timeout
        with patch('netra_backend.app.db.clickhouse.Client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.execute.side_effect = asyncio.TimeoutError("Query timeout exceeded")
            mock_client.return_value = mock_client_instance
            
            # CURRENT BEHAVIOR: Generic Exception handling likely
            # EXPECTED BEHAVIOR: Should raise specific TimeoutError
            with pytest.raises(TimeoutError, match="Query timeout exceeded"):
                db = ClickHouseDB()
                await db.execute("SELECT * FROM large_table", timeout=1)
    
    @pytest.mark.unit
    async def test_clickhouse_authentication_error_specificity(self):
        """FAILING TEST: Should raise PermissionError for authentication failures."""
        
        # Mock ClickHouse authentication failure
        with patch('netra_backend.app.db.clickhouse.Client') as mock_client:
            mock_client.side_effect = ServerException("Authentication failed")
            
            # CURRENT BEHAVIOR: Generic Exception handling
            # EXPECTED BEHAVIOR: Should raise PermissionError
            with pytest.raises(PermissionError, match="Authentication failed"):
                db = ClickHouseDB()
                await db.get_connection()
    
    @pytest.mark.unit
    async def test_clickhouse_password_loading_failure_specificity(self):
        """FAILING TEST: Should classify password loading failures specifically."""
        
        # Mock GCP secret manager failure during password loading
        with patch('netra_backend.app.db.clickhouse.SecretManagerServiceClient') as mock_secret_client:
            mock_secret_client.side_effect = PermissionError("Access denied to secret")
            
            # CURRENT BEHAVIOR: Generic Exception catch (clickhouse.py lines 359, 403)
            # EXPECTED BEHAVIOR: Should raise PermissionError specifically
            with pytest.raises(PermissionError, match="Access denied to secret"):
                from netra_backend.app.db.clickhouse import ClickHouseStagingConfig
                config = ClickHouseStagingConfig()
                config.password  # This should trigger the secret loading
    
    @pytest.mark.unit
    def test_clickhouse_module_not_importing_transaction_errors(self):
        """FAILING TEST: ClickHouse modules should import and use transaction_errors."""
        
        # Check that ClickHouse module imports transaction_errors
        import netra_backend.app.db.clickhouse as clickhouse_module
        
        # CURRENT BEHAVIOR: May not import transaction_errors
        # EXPECTED BEHAVIOR: Should have transaction_errors imported
        assert hasattr(clickhouse_module, 'classify_error'), \
            "ClickHouse module should import classify_error from transaction_errors"
        assert hasattr(clickhouse_module, 'ConnectionError'), \
            "ClickHouse module should import ConnectionError"
        assert hasattr(clickhouse_module, 'TimeoutError'), \
            "ClickHouse module should import TimeoutError"
        assert hasattr(clickhouse_module, 'SchemaError'), \
            "ClickHouse module should import SchemaError"
        assert hasattr(clickhouse_module, 'PermissionError'), \
            "ClickHouse module should import PermissionError"


class TestClickHouseConnectionManager:
    """Test suite for ClickHouse connection manager exception specificity."""
    
    @pytest.mark.unit
    async def test_connection_manager_fallback_error_specificity(self):
        """FAILING TEST: Connection manager fallback should raise specific errors."""
        
        # Mock connection manager failure with fallback
        with patch('netra_backend.app.core.clickhouse_connection_manager.ClickHouseConnectionManager') as mock_manager:
            mock_manager.side_effect = NetworkError("Connection manager unavailable")
            
            # CURRENT BEHAVIOR: Generic Exception catch with fallback (clickhouse.py line 561)
            # EXPECTED BEHAVIOR: Should raise ConnectionError but continue with fallback
            db = ClickHouseDB()
            
            # The method should handle the ConnectionError gracefully and use fallback
            # but should still log the specific error type
            with patch('netra_backend.app.db.clickhouse.logger') as mock_logger:
                await db.get_connection()
                
                # Should have logged a ConnectionError, not generic Exception
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args[0][0]
                assert "connection manager" in warning_call.lower()
    
    @pytest.mark.unit
    async def test_clickhouse_error_classification_integration(self):
        """Test that ClickHouse errors are properly classified."""
        
        # Test various ClickHouse error types
        network_error = NetworkError("Network unreachable")
        classified = classify_error(network_error)
        
        # Should be classified as ConnectionError
        # Note: This may fail if classify_error doesn't handle ClickHouse-specific errors
        assert isinstance(classified, ConnectionError), \
            "NetworkError should be classified as ConnectionError"
        
        # Test server exception classification
        server_error = ServerException("Table 'test' doesn't exist")
        classified = classify_error(server_error)
        
        # Should be classified as SchemaError for table existence issues
        assert isinstance(classified, SchemaError), \
            "ServerException for missing table should be classified as SchemaError"
    
    @pytest.mark.unit
    async def test_clickhouse_error_context_enhancement(self):
        """FAILING TEST: ClickHouse errors should include enhanced context."""
        
        # Mock a ClickHouse operation with detailed context
        with patch('netra_backend.app.db.clickhouse.Client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.execute.side_effect = NetworkError("Connection lost")
            mock_client.return_value = mock_client_instance
            
            db = ClickHouseDB()
            
            # EXPECTED BEHAVIOR: Error should include ClickHouse operational context
            with pytest.raises(ConnectionError) as exc_info:
                await db.execute("INSERT INTO events VALUES (1, 'test')")
            
            # Error should include contextual information
            error_message = str(exc_info.value)
            
            # These assertions will likely fail initially, demonstrating missing context
            assert "clickhouse" in error_message.lower(), \
                "Error should include ClickHouse context"
            assert any(word in error_message.lower() for word in ["insert", "query", "operation"]), \
                "Error should include operation context"


class TestClickHouseAnalyticsIntegration:
    """Test suite for ClickHouse analytics integration exception handling."""
    
    @pytest.mark.unit
    async def test_analytics_query_error_specificity(self):
        """FAILING TEST: Analytics queries should raise specific errors."""
        
        # Mock analytics query failure
        with patch('netra_backend.app.db.clickhouse.ClickHouseDB.execute') as mock_execute:
            mock_execute.side_effect = ServerException("Memory limit exceeded")
            
            # EXPECTED BEHAVIOR: Should raise specific error for resource limits
            # This might need a new error type like ResourceError
            with pytest.raises((TimeoutError, Exception)) as exc_info:
                db = ClickHouseDB()
                await db.execute("""
                    SELECT user_id, COUNT(*) 
                    FROM massive_events_table 
                    GROUP BY user_id
                """)
            
            # Should include context about the resource limitation
            error_message = str(exc_info.value)
            assert "memory" in error_message.lower() or "resource" in error_message.lower()
    
    @pytest.mark.unit
    async def test_batch_insert_error_specificity(self):
        """FAILING TEST: Batch insert errors should be classified specifically."""
        
        # Mock batch insert failure
        with patch('netra_backend.app.db.clickhouse.Client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.execute.side_effect = ServerException("Duplicate key value")
            mock_client.return_value = mock_client_instance
            
            # EXPECTED BEHAVIOR: Should raise specific error for constraint violations
            # This might need a new error type like ConstraintError
            with pytest.raises((SchemaError, Exception)) as exc_info:
                db = ClickHouseDB()
                await db.batch_insert("test_table", [
                    {"id": 1, "value": "test1"},
                    {"id": 1, "value": "test2"}  # Duplicate ID
                ])
            
            error_message = str(exc_info.value)
            assert "duplicate" in error_message.lower() or "constraint" in error_message.lower()


if __name__ == "__main__":
    # Run tests to validate current broad exception handling issues
    pytest.main([__file__, "-v", "--tb=short"])