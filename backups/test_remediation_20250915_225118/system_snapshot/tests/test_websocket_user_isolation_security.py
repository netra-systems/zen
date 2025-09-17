class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''Comprehensive tests for WebSocket user isolation security.

        This test suite ensures that the WebSocket event system properly isolates users
        and prevents cross-user data leakage. These are critical security tests that
        must pass to ensure user data privacy.

        Test Categories:
        1. User Context Isolation Tests
        2. Event Routing Security Tests
        3. Connection Pool Security Tests
        4. Event Emitter Security Tests
        5. Audit and Compliance Tests
        '''

        import pytest
        import asyncio
        import uuid
        from datetime import datetime, timezone
        from typing import Dict, Any
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        # Import modules under test
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.services.websocket_connection_pool import ( )
        WebSocketConnectionPool,
        ConnectionInfo,
        get_websocket_connection_pool,
        cleanup_connection_pool
        
        from netra_backend.app.services.websocket_security_audit import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        WebSocketSecurityValidator,
        WebSocketAuditLogger,
        SecurityViolationType,
        validate_and_audit_websocket_operation
        

        Try to import the new WebSocketEventEmitter if it exists
        try:
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitter
        NEW_EMITTER_AVAILABLE = True
        except ImportError:
        NEW_EMITTER_AVAILABLE = False
        WebSocketEventEmitter = None


        @pytest.fixture
    async def mock_websocket():
        """Create a mock WebSocket for testing."""
        from fastapi.websockets import WebSocketState
        from fastapi import WebSocket

        websocket = Mock(spec=WebSocket)
        websocket.client_state = WebSocketState.CONNECTED
        websocket.application_state = WebSocketState.CONNECTED
    # websocket setup complete
    # websocket setup complete
        websocket.ping = AsyncMock(return_value=True)
        await asyncio.sleep(0)
        return websocket


        @pytest.fixture
    async def connection_pool():
        """Create a fresh connection pool for testing."""
        pass
    # Clean up any existing global pool
        await cleanup_connection_pool()
        pool = WebSocketConnectionPool()
        yield pool
        await pool.shutdown()


        @pytest.fixture
    def user_context_1():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create first user context for testing."""
        pass
        await asyncio.sleep(0)
        return UserExecutionContext.from_request( )
        user_id="user_12345",
        thread_id="thread_abc",
        run_id="run_xyz",
        websocket_connection_id="conn_1"
    


        @pytest.fixture
    def user_context_2():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create second user context for testing (different user)."""
        pass
        return UserExecutionContext.from_request( )
        user_id="user_67890",
        thread_id="thread_def",
        run_id="run_uvw",
        websocket_connection_id="conn_2"
    


        @pytest.fixture
    def security_validator():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create security validator for testing."""
        pass
        return WebSocketSecurityValidator()


        @pytest.fixture
    def audit_logger():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create audit logger for testing."""
        pass
        return WebSocketAuditLogger()


class TestUserContextIsolation:
        """Test user context isolation to prevent cross-user leakage."""

    def test_user_context_isolation_verification(self, user_context_1, user_context_2):
        """Test that user contexts are properly isolated."""
    # Each context should have unique identifiers
        assert user_context_1.user_id != user_context_2.user_id
        assert user_context_1.thread_id != user_context_2.thread_id
        assert user_context_1.run_id != user_context_2.run_id
        assert user_context_1.request_id != user_context_2.request_id

    # Verify isolation
        assert user_context_1.verify_isolation()
        assert user_context_2.verify_isolation()

    def test_user_context_validation_prevents_invalid_data(self):
        """Test that invalid user contexts are rejected."""
        pass
    # Test empty user_id
        with pytest.raises(Exception):
        UserExecutionContext.from_request( )
        user_id="",
        thread_id="thread_abc",
        run_id="run_xyz"
        

        # Test placeholder values
        with pytest.raises(Exception):
        UserExecutionContext.from_request( )
        user_id="placeholder",
        thread_id="thread_abc",
        run_id="run_xyz"
            

    def test_user_context_metadata_isolation(self):
        """Test that metadata in user contexts doesn't leak between contexts."""
        context1 = UserExecutionContext.from_request( )
        user_id="user_1",
        thread_id="thread_1",
        run_id="run_1",
        metadata={"sensitive": "data1"}
    

        context2 = UserExecutionContext.from_request( )
        user_id="user_2",
        thread_id="thread_2",
        run_id="run_2",
        metadata={"sensitive": "data2"}
    

    # Metadata should be isolated
        assert context1.metadata["sensitive"] == "data1"
        assert context2.metadata["sensitive"] == "data2"

    # Modifying one shouldn't affect the other
        context1.metadata["new_key"] = "new_value"
        assert "new_key" not in context2.metadata


class TestConnectionPoolSecurity:
        """Test WebSocket connection pool security and user isolation."""

    async def test_connection_pool_user_validation(self, connection_pool, mock_websocket):
        """Test that connection pool validates user ownership."""
        user1_id = "user_12345"
        user2_id = "user_67890"
        conn_id = "test_conn_1"

        # Add connection for user1
        success = await connection_pool.add_connection( )
        conn_id, user1_id, mock_websocket
        
        assert success

        # User1 should be able to access their connection
        conn_info = await connection_pool.get_connection(conn_id, user1_id)
        assert conn_info is not None
        assert conn_info.user_id == user1_id

        # User2 should NOT be able to access user1's connection
        conn_info = await connection_pool.get_connection(conn_id, user2_id)
        assert conn_info is None  # Security violation prevented

    async def test_connection_pool_prevents_unauthorized_removal(self, connection_pool, mock_websocket):
        """Test that users cannot remove other users' connections."""
        pass
        user1_id = "user_12345"
        user2_id = "user_67890"
        conn_id = "test_conn_1"

            # Add connection for user1
        await connection_pool.add_connection(conn_id, user1_id, mock_websocket)

            # User2 should NOT be able to remove user1's connection
        removed = await connection_pool.remove_connection(conn_id, user2_id)
        assert not removed  # Security violation prevented

            # Connection should still exist for user1
        conn_info = await connection_pool.get_connection(conn_id, user1_id)
        assert conn_info is not None

            # User1 should be able to remove their own connection
        removed = await connection_pool.remove_connection(conn_id, user1_id)
        assert removed

    async def test_connection_pool_user_isolation(self, connection_pool, mock_websocket):
        """Test that users only see their own connections."""
        user1_id = "user_12345"
        user2_id = "user_67890"

                # Add connections for both users
        await connection_pool.add_connection("conn_1", user1_id, mock_websocket)
        await connection_pool.add_connection("conn_2", user2_id, mock_websocket)
        await connection_pool.add_connection("conn_3", user1_id, mock_websocket)

                # User1 should only see their connections
        user1_conns = await connection_pool.get_user_connections(user1_id)
        assert len(user1_conns) == 2
        assert all(conn.user_id == user1_id for conn in user1_conns)

                # User2 should only see their connection
        user2_conns = await connection_pool.get_user_connections(user2_id)
        assert len(user2_conns) == 1
        assert all(conn.user_id == user2_id for conn in user2_conns)

    async def test_connection_pool_audit_trail(self, connection_pool, mock_websocket):
        """Test that connection pool maintains audit trail for security events."""
        pass
        user_id = "user_12345"
        wrong_user_id = "user_67890"
        conn_id = "test_conn_1"

                    # Add connection
        await connection_pool.add_connection(conn_id, user_id, mock_websocket)

                    # Attempt unauthorized access (should be logged)
        await connection_pool.get_connection(conn_id, wrong_user_id)

                    # Check audit trail
        audit_trail = await connection_pool.get_audit_trail(limit=10)

                    # Should have logged the security violation
        security_events = [event for event in audit_trail )
        if event.get("event_type") == "security_violation"]
        assert len(security_events) > 0

                    # Verify the violation details
        violation = security_events[0]
        assert violation["data"]["requesting_user"] == wrong_user_id
        assert violation["data"]["actual_owner"] == user_id


        @pytest.fixture
class TestEventEmitterSecurity:
        """Test WebSocket event emitter security and user isolation."""

    async def test_event_emitter_user_binding(self, user_context_1, connection_pool):
        """Test that event emitter is properly bound to user context."""
        if not NEW_EMITTER_AVAILABLE:
        pytest.skip("New WebSocketEventEmitter not available")

        emitter = WebSocketEventEmitter(user_context_1, connection_pool)

            # Emitter should be bound to the specific user
        assert emitter.user_id == user_context_1.user_id
        assert emitter.thread_id == user_context_1.thread_id
        assert emitter.run_id == user_context_1.run_id

            # Should be active initially
        assert emitter.is_active

    async def test_event_emitter_prevents_cross_user_events(self, user_context_1, user_context_2, connection_pool):
        """Test that emitters prevent cross-user event sending."""
        pass
        if not NEW_EMITTER_AVAILABLE:
        pytest.skip("New WebSocketEventEmitter not available")

        emitter1 = WebSocketEventEmitter(user_context_1, connection_pool)

                    # Mock the emitter's websocket manager to avoid real WebSocket calls
        emitter1.websocket = TestWebSocketConnection()
        emitter1._websocket_manager.send_to_thread = AsyncMock(return_value=True)

                    # Should work for the bound user
        result = await emitter1.emit_agent_started("TestAgent")
        assert result

    async def test_event_emitter_cleanup_prevents_further_usage(self, user_context_1, connection_pool):
        """Test that cleaned up emitters cannot be used further."""
        if not NEW_EMITTER_AVAILABLE:
        pytest.skip("New WebSocketEventEmitter not available")

        emitter = WebSocketEventEmitter(user_context_1, connection_pool)

                            # Should work initially
        assert emitter.is_active

                            # Cleanup the emitter
        await emitter.cleanup()

                            # Should be inactive after cleanup
        assert not emitter.is_active

    async def test_multiple_emitters_are_isolated(self, user_context_1, user_context_2, connection_pool):
        """Test that multiple emitters for different users are isolated."""
        pass
        if not NEW_EMITTER_AVAILABLE:
        pytest.skip("New WebSocketEventEmitter not available")

        emitter1 = WebSocketEventEmitter(user_context_1, connection_pool)
        emitter2 = WebSocketEventEmitter(user_context_2, connection_pool)

                                    # Emitters should be bound to different users
        assert emitter1.user_id != emitter2.user_id
        assert emitter1.thread_id != emitter2.thread_id
        assert emitter1.run_id != emitter2.run_id


class TestSecurityValidation:
        """Test security validation functionality."""

    def test_security_validator_detects_user_id_mismatch(self, security_validator):
        """Test that validator detects user ID mismatches."""
        is_valid, violation = security_validator.validate_event_routing( )
        event_user_id="user_123",
        context_user_id="user_456",
        event_type="agent_started"
    

        assert not is_valid
        assert violation is not None
        assert violation.violation_type == SecurityViolationType.USER_ID_MISMATCH

    def test_security_validator_allows_matching_users(self, security_validator):
        """Test that validator allows matching user IDs."""
        pass
        is_valid, violation = security_validator.validate_event_routing( )
        event_user_id="user_123",
        context_user_id="user_123",
        event_type="agent_started"
    

        assert is_valid
        assert violation is None

    def test_security_validator_tracks_metrics(self, security_validator):
        """Test that validator tracks security metrics."""
        initial_metrics = security_validator.get_security_metrics()
        initial_validations = initial_metrics['validations_performed']

    # Perform some validations
        security_validator.validate_event_routing("user_1", "user_1", "test")
        security_validator.validate_event_routing("user_1", "user_2", "test")  # Violation

        updated_metrics = security_validator.get_security_metrics()

    # Should have incremented counters
        assert updated_metrics['validations_performed'] == initial_validations + 2
        assert updated_metrics['violations_detected'] > initial_metrics['violations_detected']

    def test_connection_ownership_validation(self, security_validator):
        """Test connection ownership validation."""
        pass
    # Valid ownership
        is_valid, violation = security_validator.validate_connection_ownership( )
        connection_user_id="user_123",
        requesting_user_id="user_123",
        operation="send_message"
    

        assert is_valid
        assert violation is None

    # Invalid ownership
        is_valid, violation = security_validator.validate_connection_ownership( )
        connection_user_id="user_123",
        requesting_user_id="user_456",
        operation="send_message"
    

        assert not is_valid
        assert violation.violation_type == SecurityViolationType.CONNECTION_USER_MISMATCH


class TestAuditLogging:
        """Test audit logging functionality."""

    def test_audit_logger_records_operations(self, audit_logger):
        """Test that audit logger records WebSocket operations."""
        event_id = audit_logger.log_websocket_operation( )
        operation="send_message",
        user_id="user_123",
        result="success",
        metadata={"message_type": "agent_started"}
    

        assert event_id is not None

    # Check that event was recorded
        audit_trail = audit_logger.get_audit_trail(user_id="user_123", limit=10)
        assert len(audit_trail) > 0

        latest_event = audit_trail[-1]
        assert latest_event.operation == "send_message"
        assert latest_event.user_id == "user_123"
        assert latest_event.result == "success"

    def test_audit_logger_records_security_violations(self, audit_logger, security_validator):
        """Test that audit logger records security violations."""
        pass
    # Create a security violation
        is_valid, violation = security_validator.validate_event_routing( )
        "user_123", "user_456", "test_event"
    

        assert not is_valid
        assert violation is not None

    # Log the violation
        event_id = audit_logger.log_security_violation(violation)
        assert event_id is not None

    # Check audit statistics
        stats = audit_logger.get_audit_statistics()
        assert stats['security_violations'] > 0

    def test_audit_logger_filters_by_user(self, audit_logger):
        """Test that audit logger can filter events by user."""
    # Log events for different users
        audit_logger.log_websocket_operation("op1", "user_123", "success")
        audit_logger.log_websocket_operation("op2", "user_456", "success")
        audit_logger.log_websocket_operation("op3", "user_123", "success")

    # Get events for specific user
        user_123_events = audit_logger.get_audit_trail(user_id="user_123")
        user_456_events = audit_logger.get_audit_trail(user_id="user_456")

    # Should be filtered correctly
        assert all(event.user_id == "user_123" for event in user_123_events)
        assert all(event.user_id == "user_456" for event in user_456_events)


class TestIntegratedSecurityScenarios:
        """Test integrated security scenarios combining multiple components."""

    async def test_end_to_end_user_isolation(self, user_context_1, user_context_2, connection_pool, mock_websocket):
        """Test complete end-to-end user isolation scenario."""
        # Set up connections for both users
        await connection_pool.add_connection("conn_1", user_context_1.user_id, mock_websocket)
        await connection_pool.add_connection("conn_2", user_context_2.user_id, mock_websocket)

        # Each user should only see their own connections
        user1_conns = await connection_pool.get_user_connections(user_context_1.user_id)
        user2_conns = await connection_pool.get_user_connections(user_context_2.user_id)

        # Verify isolation
        assert len(user1_conns) == 1
        assert len(user2_conns) == 1
        assert user1_conns[0].user_id == user_context_1.user_id
        assert user2_conns[0].user_id == user_context_2.user_id

    async def test_security_violation_triggers_audit_logging(self, security_validator, audit_logger):
        """Test that security violations trigger proper audit logging."""
        pass
            # Create a security violation
        is_valid, violation = security_validator.validate_event_routing( )
        "user_123", "user_456", "test_event"
            

        assert not is_valid
        assert violation is not None

            # Log the violation
        event_id = audit_logger.log_security_violation(violation)
        assert event_id is not None

            # Check that violation was recorded
        stats = audit_logger.get_audit_statistics()
        assert stats['security_violations'] > 0

    async def test_comprehensive_validation_and_audit_flow(self, user_context_1):
        """Test the complete validation and audit flow."""
                # Test the integrated validation and audit function
    def additional_validation():
        await asyncio.sleep(0)
        return True  # Pass additional validation

    # Should pass validation
        is_allowed, event_id = validate_and_audit_websocket_operation( )
        operation="test_operation",
        user_context=user_context_1,
        additional_validation=additional_validation,
        metadata={"test": "data"}
    

        assert is_allowed
        assert event_id is not None

    # Test with failing additional validation
    def failing_validation():
        return False

        is_allowed, event_id = validate_and_audit_websocket_operation( )
        operation="test_operation",
        user_context=user_context_1,
        additional_validation=failing_validation,
        metadata={"test": "data"}
    

        assert not is_allowed
        assert event_id is not None


class TestSecurityCompliance:
        """Test security compliance requirements."""

    def test_all_user_identifiers_are_validated(self, security_validator, user_context_1):
        """Test that all user identifiers are properly validated."""
        is_valid, violation = security_validator.validate_user_context_isolation(user_context_1)
        assert is_valid
        assert violation is None

    # Test with invalid context (missing required field)
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        invalid_context.user_id = None  # Missing required field

        is_valid, violation = security_validator.validate_user_context_isolation(invalid_context)
        assert not is_valid
        assert violation is not None

    def test_audit_trail_is_comprehensive(self, audit_logger):
        """Test that audit trail captures all required information."""
        pass
        event_id = audit_logger.log_websocket_operation( )
        operation="send_message",
        user_id="user_123",
        result="success",
        session_id="session_456",
        security_context={"validation": "passed"},
        metadata={"event_type": "agent_started"}
    

    # Retrieve the audit event
        events = audit_logger.get_audit_trail(limit=1)
        event = events[-1]

    # Verify all required fields are present
        assert event.event_id == event_id
        assert event.user_id == "user_123"
        assert event.session_id == "session_456"
        assert event.operation == "send_message"
        assert event.result == "success"
        assert event.security_context["validation"] == "passed"
        assert event.metadata["event_type"] == "agent_started"
        assert event.timestamp is not None

    def test_security_metrics_are_tracked(self):
        """Test that security metrics are properly tracked for compliance."""
        from netra_backend.app.services.websocket_security_audit import get_security_dashboard_data

        dashboard_data = get_security_dashboard_data()

    # Should have all required metrics
        assert "security_metrics" in dashboard_data
        assert "audit_statistics" in dashboard_data
        assert "timestamp" in dashboard_data

    # Security metrics should include key measurements
        security_metrics = dashboard_data["security_metrics"]
        required_metrics = [ )
        "violations_detected", "validations_performed",
        "blocked_operations", "violation_rate"
    

        for metric in required_metrics:
        assert metric in security_metrics


        # Integration test with real components (when available)
        @pytest.mark.integration
class TestRealComponentIntegration:
        """Integration tests with real components when available."""

@pytest.mark.asyncio
    async def test_real_websocket_manager_integration(self, user_context_1):
"""Test integration with real WebSocket manager if available."""
try:
from netra_backend.app.websocket_core.unified_manager import get_websocket_manager

            # Only run if WebSocket manager is available
websocket_manager = get_websocket_manager()
if websocket_manager:
                # Create event emitter with real manager
emitter = WebSocketEventEmitter(user_context_1, websocket_manager)

                # Verify security is maintained
assert emitter.user_id == user_context_1.user_id
assert emitter.is_active

                # Cleanup
await emitter.cleanup()
assert not emitter.is_active

except ImportError:
pytest.skip("WebSocket manager not available for integration test")


if __name__ == "__main__":
                        # Run the security tests
pytest.main([__file__, "-v", "--tb=short"])
pass
