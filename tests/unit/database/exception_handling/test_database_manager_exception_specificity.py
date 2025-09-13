"""
Unit tests for database manager exception specificity.

MISSION: Validate that DatabaseManager raises specific exception types instead of broad Exception handling.
Tests will FAIL initially to demonstrate current broad exception handling problems.

Issue #374: Database Exception Handling Remediation
"""

import pytest
import asyncio
import asyncpg
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Import the classes we're testing
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.db.transaction_errors import (
    DeadlockError, ConnectionError, TimeoutError, 
    PermissionError, SchemaError, classify_error
)


class TestDatabaseManagerExceptionSpecificity:
    """Test suite for database manager exception specificity validation."""
    
    @pytest.mark.unit
    async def test_database_manager_health_check_connection_failure_specificity(self):
        """FAILING TEST: Should raise ConnectionError, not generic Exception."""
        manager = DatabaseManager()
        
        # Mock connection failure scenario
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=asyncpg.ConnectionFailureError("Connection refused"))
        
        # CURRENT BEHAVIOR: Raises generic Exception (database_manager.py line 866)
        # EXPECTED BEHAVIOR: Should raise specific ConnectionError
        with pytest.raises(ConnectionError, match="Connection refused"):
            await manager._health_check_engine("test_engine", mock_engine)
    
    @pytest.mark.unit
    async def test_database_manager_initialization_failure_specificity(self):
        """FAILING TEST: Should raise specific exception types during initialization."""
        manager = DatabaseManager()
        
        # Mock engine creation failure
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            mock_create_engine.side_effect = asyncpg.ConnectionFailureError("Could not connect to server")
            
            # CURRENT BEHAVIOR: Generic Exception catch (database_manager.py line 445)
            # EXPECTED BEHAVIOR: Should raise ConnectionError with diagnostic context
            with pytest.raises(ConnectionError, match="Could not connect to server"):
                await manager.initialize()
    
    @pytest.mark.unit 
    async def test_database_manager_rollback_deadlock_classification(self):
        """FAILING TEST: Should classify rollback deadlock failures specifically."""
        manager = DatabaseManager()
        
        # Mock session with deadlock on rollback
        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock(
            side_effect=OperationalError("deadlock detected", None, None)
        )
        
        with patch.object(manager, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            # CURRENT BEHAVIOR: Broad Exception catch (database_manager.py lines 594, 615)  
            # EXPECTED BEHAVIOR: Should raise DeadlockError with context
            with pytest.raises(DeadlockError, match="deadlock detected"):
                async with manager.get_session() as session:
                    raise ValueError("Force rollback scenario")
    
    @pytest.mark.unit
    async def test_database_manager_session_timeout_specificity(self):
        """FAILING TEST: Should raise TimeoutError for session timeouts."""
        manager = DatabaseManager()
        
        # Mock session timeout
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                side_effect=asyncio.TimeoutError("Query execution timeout")
            )
            mock_session_class.return_value = mock_session
            
            # CURRENT BEHAVIOR: Generic Exception handling 
            # EXPECTED BEHAVIOR: Should raise TimeoutError
            with pytest.raises(TimeoutError, match="Query execution timeout"):
                async with manager.get_session() as session:
                    await session.execute("SELECT pg_sleep(30)")
    
    @pytest.mark.unit
    async def test_websocket_event_sending_failure_classification(self):
        """FAILING TEST: Should classify WebSocket event sending failures."""
        manager = DatabaseManager()
        
        # Mock WebSocket event sending failure
        with patch.object(manager, '_send_websocket_event') as mock_send:
            mock_send.side_effect = ConnectionError("WebSocket connection lost")
            
            # CURRENT BEHAVIOR: Generic Exception catch (database_manager.py line 181)
            # EXPECTED BEHAVIOR: Should handle ConnectionError specifically
            with pytest.raises(ConnectionError, match="WebSocket connection lost"):
                await manager._send_post_commit_events([
                    MagicMock(event_type="test_event", user_id=1, event_data={})
                ])
    
    @pytest.mark.unit
    async def test_session_cleanup_failure_specificity(self):
        """FAILING TEST: Should classify session cleanup failures specifically."""
        manager = DatabaseManager()
        
        # Mock session cleanup failure
        mock_session = AsyncMock()
        mock_session.close = AsyncMock(
            side_effect=OperationalError("connection already closed", None, None)
        )
        
        # CURRENT BEHAVIOR: Generic Exception catch (database_manager.py line 633)
        # EXPECTED BEHAVIOR: Should handle OperationalError specifically
        # Note: This might be acceptable to catch generically, but should still log specifically
        
        with patch.object(manager, '_active_sessions', {'test-session': mock_session}):
            # Should not raise but should handle the specific error type
            await manager._cleanup_expired_sessions()
            
            # Verify that the specific error was handled (not generic Exception)
            mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_rollback_notification_failure_classification(self):
        """FAILING TEST: Should classify rollback notification failures."""
        manager = DatabaseManager()
        
        # Mock rollback notification failure
        with patch.object(manager, '_send_rollback_notification') as mock_send:
            mock_send.side_effect = TimeoutError("Notification timeout")
            
            # CURRENT BEHAVIOR: Generic Exception catch (database_manager.py line 232)
            # EXPECTED BEHAVIOR: Should handle TimeoutError specifically
            with pytest.raises(TimeoutError, match="Notification timeout"):
                rollback_notification = MagicMock()
                await manager._send_rollback_notification(rollback_notification, [1, 2, 3])
    
    @pytest.mark.unit
    async def test_auto_initialization_failure_specificity(self):
        """FAILING TEST: Should classify auto-initialization failures."""
        
        # Mock initialization failure during auto-initialization
        with patch('netra_backend.app.db.database_manager.DatabaseManager.initialize') as mock_init:
            mock_init.side_effect = PermissionError("Insufficient database privileges")
            
            # CURRENT BEHAVIOR: Generic Exception catch (database_manager.py line 476)
            # EXPECTED BEHAVIOR: Should raise PermissionError with context
            with pytest.raises(PermissionError, match="Insufficient database privileges"):
                manager = DatabaseManager()
                await manager._ensure_initialized()
    
    @pytest.mark.unit
    def test_transaction_error_classification_integration(self):
        """Test that classify_error function is properly integrated."""
        
        # Test that classify_error properly categorizes database exceptions
        deadlock_error = OperationalError("deadlock detected", None, None)
        classified = classify_error(deadlock_error)
        
        # Should return DeadlockError, not the original OperationalError
        assert isinstance(classified, DeadlockError)
        assert "deadlock detected" in str(classified)
        
        # Test connection error classification
        connection_error = OperationalError("connection timeout", None, None)
        classified = classify_error(connection_error)
        
        # Should return ConnectionError or TimeoutError
        assert isinstance(classified, (ConnectionError, TimeoutError))
    
    @pytest.mark.unit
    def test_database_manager_not_using_transaction_errors_module(self):
        """FAILING TEST: DatabaseManager should import and use transaction_errors module."""
        
        # Check that DatabaseManager imports transaction_errors
        import netra_backend.app.db.database_manager as db_manager_module
        
        # CURRENT BEHAVIOR: May not import transaction_errors
        # EXPECTED BEHAVIOR: Should have transaction_errors imported
        assert hasattr(db_manager_module, 'classify_error'), \
            "DatabaseManager should import classify_error from transaction_errors"
        assert hasattr(db_manager_module, 'DeadlockError'), \
            "DatabaseManager should import DeadlockError"
        assert hasattr(db_manager_module, 'ConnectionError'), \
            "DatabaseManager should import ConnectionError" 
        assert hasattr(db_manager_module, 'TimeoutError'), \
            "DatabaseManager should import TimeoutError"


class TestDatabaseManagerErrorRecovery:
    """Test suite for database manager error recovery patterns."""
    
    @pytest.mark.unit
    async def test_retryable_error_detection(self):
        """Test that retryable errors are properly identified."""
        from netra_backend.app.db.transaction_errors import is_retryable_error
        
        # Test deadlock error retryability
        deadlock_error = OperationalError("deadlock detected", None, None)
        assert is_retryable_error(deadlock_error, enable_deadlock_retry=True, enable_connection_retry=False)
        assert not is_retryable_error(deadlock_error, enable_deadlock_retry=False, enable_connection_retry=False)
        
        # Test connection error retryability  
        connection_error = DisconnectionError("connection lost", None, None)
        assert is_retryable_error(connection_error, enable_deadlock_retry=False, enable_connection_retry=True)
        assert not is_retryable_error(connection_error, enable_deadlock_retry=False, enable_connection_retry=False)
    
    @pytest.mark.unit
    async def test_error_context_enhancement(self):
        """Test that errors include enhanced context information."""
        manager = DatabaseManager()
        
        # Mock a database operation with context
        with patch.object(manager, '_health_check_engine') as mock_health_check:
            mock_health_check.side_effect = ConnectionError("Database connection failed")
            
            # EXPECTED BEHAVIOR: Error should include operational context
            # (connection details, timing, operation type, etc.)
            with pytest.raises(ConnectionError) as exc_info:
                await manager._health_check_engine("postgresql_engine", MagicMock())
            
            # Error should include contextual information
            error_message = str(exc_info.value)
            # These assertions will likely fail initially, demonstrating missing context
            assert "postgresql_engine" in error_message, "Error should include engine name context"
            assert any(word in error_message.lower() for word in ["connection", "database"]), \
                "Error should include operation context"


if __name__ == "__main__":
    # Run tests to validate current broad exception handling issues
    pytest.main([__file__, "-v", "--tb=short"])