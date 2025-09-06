"""Comprehensive test suite for UserExecutionContext service.

This test suite validates all aspects of the UserExecutionContext implementation
including isolation, validation, factory methods, and integration patterns.
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from contextlib import asynccontextmanager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    managed_user_context,
    register_shared_object,
    clear_shared_object_registry
)


class TestUserExecutionContextValidation:
    """Test validation logic for UserExecutionContext."""
    
    def test_valid_context_creation(self):
        """Test creating a valid UserExecutionContext."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890", 
            run_id="run_abcdef123456",
            request_id=str(uuid.uuid4())
        )
        
        assert context.user_id == "user_12345"
        assert context.thread_id == "thread_67890"
        assert context.run_id == "run_abcdef123456"
        assert context.operation_depth == 0
        assert context.parent_request_id is None
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.agent_context, dict)
        assert isinstance(context.audit_metadata, dict)
    
    def test_auto_generated_request_id(self):
        """Test that request_id is auto-generated when not provided."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        # Should be a valid UUID
        uuid.UUID(context.request_id)
        assert len(context.request_id) == 36  # Standard UUID length
    
    def test_required_field_validation(self):
        """Test validation of required fields."""
        # Test empty user_id
        with pytest.raises(InvalidContextError, match="Required field 'user_id'"):
            UserExecutionContext(
                user_id="",
                thread_id="thread_67890",
                run_id="run_abcdef123456"
            )
        
        # Test None thread_id
        with pytest.raises(InvalidContextError, match="Required field 'thread_id'"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id=None,
                run_id="run_abcdef123456"
            )
        
        # Test whitespace-only run_id
        with pytest.raises(InvalidContextError, match="Required field 'run_id'"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="   "
            )
        
        # Test invalid UUID for request_id
        with pytest.raises(InvalidContextError, match="request_id must be a valid UUID"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="run_abcdef123456",
                request_id="not-a-uuid"
            )
    
    def test_placeholder_value_validation(self):
        """Test validation against dangerous placeholder values."""
        dangerous_values = [
            "registry", "placeholder", "default", "temp", "none", "null",
            "undefined", "xxx", "example", "test", "demo"
        ]
        
        for dangerous_value in dangerous_values:
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserExecutionContext(
                    user_id=dangerous_value,
                    thread_id="thread_67890",
                    run_id="run_abcdef123456"
                )
    
    def test_placeholder_pattern_validation(self):
        """Test validation against dangerous placeholder patterns."""
        dangerous_patterns = [
            "placeholder_123", "registry_abc", "default_xyz", 
            "temp_456", "test_789"
        ]
        
        for pattern in dangerous_patterns:
            with pytest.raises(InvalidContextError, match="placeholder pattern"):
                UserExecutionContext(
                    user_id="user_12345",
                    thread_id=pattern,
                    run_id="run_abcdef123456"
                )
    
    def test_long_values_bypass_pattern_check(self):
        """Test that long values (>= 20 chars) bypass pattern validation."""
        # This should pass because it's >= 20 characters
        long_value_with_pattern = "placeholder_very_long_identifier_12345"
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id=long_value_with_pattern,
            run_id="run_abcdef123456"
        )
        assert context.thread_id == long_value_with_pattern
    
    def test_metadata_isolation(self):
        """Test that metadata dictionaries are properly isolated."""
        shared_dict = {"shared": "data"}
        
        context1 = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            agent_context=shared_dict
        )
        
        context2 = UserExecutionContext(
            user_id="user_54321",
            thread_id="thread_09876",
            run_id="run_fedcba654321",
            agent_context=shared_dict
        )
        
        # Modifications should not affect other contexts
        context1.agent_context["new_key"] = "value1"
        assert "new_key" not in context2.agent_context
    
    def test_reserved_key_validation(self):
        """Test validation against reserved keys in metadata."""
        with pytest.raises(InvalidContextError, match="reserved keys"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="run_abcdef123456",
                agent_context={"user_id": "conflicting_value"}
            )
        
        with pytest.raises(InvalidContextError, match="reserved keys"):
            UserExecutionContext(
                user_id="user_12345",
                thread_id="thread_67890",
                run_id="run_abcdef123456",
                audit_metadata={"db_session": "conflicting_value"}
            )


class TestUserExecutionContextFactoryMethods:
    """Test factory methods for creating UserExecutionContext."""
    
    def test_from_request_factory(self):
        """Test from_request factory method."""
        context = UserExecutionContext.from_request(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            websocket_client_id="ws_connection_123",
            agent_context={"agent_name": "TestAgent"},
            audit_metadata={"source": "test"}
        )
        
        assert context.user_id == "user_12345"
        assert context.thread_id == "thread_67890"
        assert context.run_id == "run_abcdef123456"
        assert context.websocket_client_id == "ws_connection_123"
        assert context.agent_context["agent_name"] == "TestAgent"
        assert context.audit_metadata["source"] == "test"
    
    def test_from_request_auto_generated_request_id(self):
        """Test that from_request auto-generates request_id when not provided."""
        context = UserExecutionContext.from_request(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        # Should be a valid UUID
        uuid.UUID(context.request_id)
    
    def test_from_fastapi_request_factory(self):
        """Test from_fastapi_request factory method."""
        # Mock FastAPI Request
        mock_request = mock_request_instance  # Initialize appropriate service
        mock_request.client = client_instance  # Initialize appropriate service
        mock_request.client.host = "192.168.1.100"
        mock_request.method = "POST"
        mock_request.url = "https://api.example.com/agents/execute"
        mock_request.headers = {
            "user-agent": "Mozilla/5.0 Test Browser",
            "content-type": "application/json",
            "x-request-id": "ext_req_12345",
            "x-correlation-id": "corr_67890"
        }
        
        context = UserExecutionContext.from_fastapi_request(
            request=mock_request,
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            websocket_client_id="ws_connection_123"
        )
        
        assert context.user_id == "user_12345"
        assert context.websocket_client_id == "ws_connection_123"
        assert context.audit_metadata["client_ip"] == "192.168.1.100"
        assert context.audit_metadata["user_agent"] == "Mozilla/5.0 Test Browser"
        assert context.audit_metadata["method"] == "POST"
        assert context.audit_metadata["x_request_id"] == "ext_req_12345"
        assert context.audit_metadata["x_correlation_id"] == "corr_67890"
    
    def test_from_fastapi_request_missing_client_info(self):
        """Test from_fastapi_request handles missing client information."""
        mock_request = mock_request_instance  # Initialize appropriate service
        mock_request.client = None
        mock_request.method = "GET"
        mock_request.url = "https://api.example.com/status"
        mock_request.headers = {}
        
        context = UserExecutionContext.from_fastapi_request(
            request=mock_request,
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        assert context.audit_metadata["client_ip"] == "unknown"
        assert context.audit_metadata["user_agent"] == "unknown"
        assert context.audit_metadata["content_type"] == "unknown"


class TestUserExecutionContextChildContexts:
    """Test child context creation and hierarchy tracking."""
    
    def test_create_child_context(self):
        """Test creating child contexts."""
        parent_context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            agent_context={"operation_name": "parent_operation"}
        )
        
        child_context = parent_context.create_child_context(
            operation_name="data_analysis",
            additional_agent_context={"model": "gpt-4"},
            additional_audit_metadata={"complexity": "high"}
        )
        
        # Verify inheritance
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        assert child_context.db_session == parent_context.db_session
        assert child_context.websocket_client_id == parent_context.websocket_client_id
        
        # Verify child-specific attributes
        assert child_context.request_id != parent_context.request_id
        assert child_context.operation_depth == parent_context.operation_depth + 1
        assert child_context.parent_request_id == parent_context.request_id
        
        # Verify enhanced metadata
        assert child_context.agent_context["operation_name"] == "data_analysis"
        assert child_context.agent_context["parent_operation"] == "parent_operation"
        assert child_context.agent_context["model"] == "gpt-4"
        assert child_context.audit_metadata["complexity"] == "high"
    
    def test_child_context_validation(self):
        """Test validation of child context creation."""
        parent_context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        # Test empty operation name
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context("")
        
        # Test None operation name
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context(None)
    
    def test_max_depth_protection(self):
        """Test protection against excessive nesting depth."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            operation_depth=10  # At maximum
        )
        
        with pytest.raises(InvalidContextError, match="Maximum operation depth"):
            context.create_child_context("too_deep")
    
    def test_nested_child_contexts(self):
        """Test creating multiple levels of child contexts."""
        root_context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        level1_context = root_context.create_child_context("level1")
        level2_context = level1_context.create_child_context("level2")
        level3_context = level2_context.create_child_context("level3")
        
        assert root_context.operation_depth == 0
        assert level1_context.operation_depth == 1
        assert level2_context.operation_depth == 2
        assert level3_context.operation_depth == 3
        
        assert level3_context.parent_request_id == level2_context.request_id
        assert level2_context.parent_request_id == level1_context.request_id
        assert level1_context.parent_request_id == root_context.request_id


class TestUserExecutionContextImmutability:
    """Test immutability and isolation features."""
    
    def test_context_immutability(self):
        """Test that UserExecutionContext is immutable after creation."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        # These should raise AttributeError due to frozen=True
        with pytest.raises(AttributeError):
            context.user_id = "modified_user"
        
        with pytest.raises(AttributeError):
            context.operation_depth = 5
    
    def test_with_db_session(self):
        """Test creating context with database session."""
        mock_session = AsyncNone  # TODO: Use real service instance
        
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        context_with_session = context.with_db_session(mock_session)
        
        # Original context unchanged
        assert context.db_session is None
        
        # New context has session
        assert context_with_session.db_session is mock_session
        assert context_with_session.user_id == context.user_id
        assert context_with_session.request_id == context.request_id
    
    def test_with_db_session_validation(self):
        """Test validation of with_db_session method."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        with pytest.raises(InvalidContextError, match="db_session cannot be None"):
            context.with_db_session(None)
    
    def test_with_websocket_connection(self):
        """Test creating context with WebSocket connection."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        context_with_ws = context.with_websocket_connection("ws_connection_456")
        
        # Original context unchanged
        assert context.websocket_client_id is None
        
        # New context has WebSocket connection
        assert context_with_ws.websocket_client_id == "ws_connection_456"
        assert context_with_ws.user_id == context.user_id
    
    def test_with_websocket_connection_validation(self):
        """Test validation of with_websocket_connection method."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        with pytest.raises(InvalidContextError, match="connection_id must be a non-empty string"):
            context.with_websocket_connection("")
        
        with pytest.raises(InvalidContextError, match="connection_id must be a non-empty string"):
            context.with_websocket_connection(None)


class TestUserExecutionContextIsolation:
    """Test isolation verification and shared object detection."""
    
    def setup_method(self):
        """Clear shared object registry before each test."""
        clear_shared_object_registry()
    
    def test_verify_isolation_success(self):
        """Test successful isolation verification."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        assert context.verify_isolation() is True
    
    def test_verify_isolation_with_db_session(self):
        """Test isolation verification with database session."""
        mock_session = AsyncNone  # TODO: Use real service instance
        
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            db_session=mock_session
        )
        
        assert context.verify_isolation() is True
    
    def test_isolation_violation_detection(self):
        """Test detection of isolation violations."""
        shared_dict = {"shared": "data"}
        register_shared_object(shared_dict)
        
        # This should not raise an error because we copy the dict in __post_init__
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            agent_context=shared_dict
        )
        
        # Verification should still pass because dict was copied
        assert context.verify_isolation() is True
    
    def test_duplicate_id_warning(self, caplog):
        """Test warning for duplicate ID values."""
        import logging
        caplog.set_level(logging.WARNING, logger="netra_backend.app.services.user_execution_context")
        
        duplicate_id = "same_id_123"
        context = UserExecutionContext(
            user_id=duplicate_id,
            thread_id=duplicate_id,  # Duplicate value
            run_id="run_abcdef123456"
        )
        
        context.verify_isolation()
        
        # Should log a warning about duplicate IDs
        assert "duplicate ID values" in caplog.text


class TestUserExecutionContextUtilityMethods:
    """Test utility methods and serialization."""
    
    def test_to_dict(self):
        """Test dictionary serialization."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            websocket_client_id="ws_connection_123",
            agent_context={"agent_name": "TestAgent"},
            audit_metadata={"source": "test"},
            operation_depth=2,
            parent_request_id="parent_req_123"
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["user_id"] == "user_12345"
        assert context_dict["thread_id"] == "thread_67890"
        assert context_dict["run_id"] == "run_abcdef123456"
        assert context_dict["websocket_client_id"] == "ws_connection_123"
        assert context_dict["agent_context"]["agent_name"] == "TestAgent"
        assert context_dict["audit_metadata"]["source"] == "test"
        assert context_dict["operation_depth"] == 2
        assert context_dict["parent_request_id"] == "parent_req_123"
        assert context_dict["has_db_session"] is False
        assert isinstance(context_dict["created_at"], str)  # ISO format
    
    def test_to_dict_with_db_session(self):
        """Test dictionary serialization with database session."""
        mock_session = AsyncNone  # TODO: Use real service instance
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            db_session=mock_session
        )
        
        context_dict = context.to_dict()
        assert context_dict["has_db_session"] is True
        assert "db_session" not in context_dict  # Should not include actual session
    
    def test_get_correlation_id(self):
        """Test correlation ID generation."""
        context = UserExecutionContext(
            user_id="user_12345678",
            thread_id="thread_87654321",
            run_id="run_abcdef123456",
            request_id="12345678-1234-1234-1234-123456789012"
        )
        
        correlation_id = context.get_correlation_id()
        
        # Should be first 8 characters of each ID joined by colons
        expected = "user_123:thread_8:run_abcd:12345678"
        assert correlation_id == expected
    
    def test_get_audit_trail(self):
        """Test comprehensive audit trail generation."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            websocket_client_id="ws_connection_123",
            operation_depth=1,
            parent_request_id="parent_req_123",
            audit_metadata={"source": "test", "complexity": "high"}
        )
        
        audit_trail = context.get_audit_trail()
        
        assert audit_trail["user_id"] == "user_12345"
        assert audit_trail["operation_depth"] == 1
        assert audit_trail["parent_request_id"] == "parent_req_123"
        assert audit_trail["has_websocket"] is True
        assert audit_trail["audit_metadata"]["source"] == "test"
        assert "correlation_id" in audit_trail
        assert "context_age_seconds" in audit_trail
        assert isinstance(audit_trail["context_age_seconds"], float)
    
    def test_to_execution_context(self):
        """Test conversion to legacy ExecutionContext."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            websocket_client_id="ws_connection_123",
            agent_context={"agent_name": "TestAgent"},
            operation_depth=1
        )
        
        execution_context = context.to_execution_context()
        
        assert execution_context.run_id == "run_abcdef123456"
        assert execution_context.user_id == "user_12345"
        assert execution_context.thread_id == "thread_67890"
        assert execution_context.agent_name == "TestAgent"
        assert execution_context.metadata["user_execution_context_id"] == context.request_id
        assert execution_context.metadata["operation_depth"] == 1
        assert execution_context.metadata["websocket_client_id"] == "ws_connection_123"


class TestUserExecutionContextValidation:
    """Test the validate_user_context function."""
    
    def test_valid_context_validation(self):
        """Test validation of valid UserExecutionContext."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        validated_context = validate_user_context(context)
        assert validated_context is context
    
    def test_invalid_type_validation(self):
        """Test validation fails for non-UserExecutionContext objects."""
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context("not_a_context")
        
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context({"user_id": "user_123"})


class TestManagedUserContext:
    """Test the managed_user_context async context manager."""
    
    @pytest.mark.asyncio
    async def test_managed_context_basic(self):
        """Test basic managed context functionality."""
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        async with managed_user_context(context) as managed_ctx:
            assert managed_ctx is context
    
    @pytest.mark.asyncio
    async def test_managed_context_with_db_session_cleanup(self):
        """Test managed context with database session cleanup."""
        mock_session = AsyncNone  # TODO: Use real service instance
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            db_session=mock_session
        )
        
        async with managed_user_context(context, cleanup_db_session=True) as managed_ctx:
            assert managed_ctx.db_session is mock_session
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_managed_context_without_cleanup(self):
        """Test managed context without database session cleanup."""
        mock_session = AsyncNone  # TODO: Use real service instance
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            db_session=mock_session
        )
        
        async with managed_user_context(context, cleanup_db_session=False) as managed_ctx:
            assert managed_ctx.db_session is mock_session
        
        # Verify session was not closed
        mock_session.close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_managed_context_exception_handling(self):
        """Test managed context handles exceptions properly."""
        mock_session = AsyncNone  # TODO: Use real service instance
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            db_session=mock_session
        )
        
        with pytest.raises(ValueError, match="test exception"):
            async with managed_user_context(context) as managed_ctx:
                raise ValueError("test exception")
        
        # Session should still be closed even after exception
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_managed_context_session_close_error(self, caplog):
        """Test managed context handles session close errors."""
        import logging
        caplog.set_level(logging.WARNING, logger="netra_backend.app.services.user_execution_context")
        
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_session.close.side_effect = Exception("Close failed")
        
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            db_session=mock_session
        )
        
        async with managed_user_context(context):
            pass
        
        # Should log warning about close error
        assert "Error closing database session" in caplog.text


class TestUserExecutionContextEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_long_ids(self):
        """Test context with very long ID values."""
        long_user_id = "u" * 1000
        context = UserExecutionContext(
            user_id=long_user_id,
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        assert context.user_id == long_user_id
        assert len(context.get_correlation_id()) > 8  # Should still truncate for correlation
    
    def test_unicode_ids(self):
        """Test context with Unicode characters in IDs."""
        unicode_user_id = "user_测试_🚀"
        context = UserExecutionContext(
            user_id=unicode_user_id,
            thread_id="thread_67890",
            run_id="run_abcdef123456"
        )
        
        assert context.user_id == unicode_user_id
    
    def test_context_age_calculation(self):
        """Test context age calculation in audit trail."""
        # Create context with specific timestamp
        past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            created_at=past_time
        )
        
        audit_trail = context.get_audit_trail()
        age = audit_trail["context_age_seconds"]
        
        # Should be approximately 10 seconds (allowing for test execution time)
        assert 9 < age < 15
    
    def test_metadata_deep_copy(self):
        """Test that nested dictionaries in metadata are properly copied."""
        nested_context = {
            "level1": {
                "level2": {
                    "value": "original"
                }
            }
        }
        
        context = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            agent_context=nested_context
        )
        
        # Modify nested structure
        context.agent_context["level1"]["level2"]["value"] = "modified"
        
        # Create child context
        child = context.create_child_context("test_operation")
        
        # Child should have snapshot, not reference
        assert child.agent_context["level1"]["level2"]["value"] == "modified"
        
        # Further modifications to child should not affect parent
        child.agent_context["level1"]["level2"]["value"] = "child_modified"
        assert context.agent_context["level1"]["level2"]["value"] == "modified"


class TestUserExecutionContextIntegration:
    """Test integration scenarios and compatibility."""
    
    def test_multiple_contexts_isolation(self):
        """Test that multiple contexts are properly isolated."""
        context1 = UserExecutionContext(
            user_id="user_111",
            thread_id="thread_111",
            run_id="run_111",
            agent_context={"agent_data": "context1"}
        )
        
        context2 = UserExecutionContext(
            user_id="user_222",
            thread_id="thread_222",
            run_id="run_222",
            agent_context={"agent_data": "context2"}
        )
        
        # Verify complete isolation
        assert context1.user_id != context2.user_id
        assert context1.request_id != context2.request_id
        assert context1.agent_context["agent_data"] != context2.agent_context["agent_data"]
        
        # Verify both are valid
        assert validate_user_context(context1) is context1
        assert validate_user_context(context2) is context2
    
    def test_context_equality_and_hashing(self):
        """Test context comparison and hashing behavior."""
        request_id1 = str(uuid.uuid4())
        request_id2 = str(uuid.uuid4())
        
        context1 = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            request_id=request_id1
        )
        
        # Same IDs, different object
        context2 = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            request_id=request_id1
        )
        
        # Different request ID
        context3 = UserExecutionContext(
            user_id="user_12345",
            thread_id="thread_67890",
            run_id="run_abcdef123456",
            request_id=request_id2
        )
        
        # Test equality (based on all fields due to dataclass)
        assert context1 != context2  # Different created_at timestamps
        assert context1 != context3  # Different request IDs
        
        # Test hashing works (no exceptions)
        context_set = {context1, context2, context3}
        assert len(context_set) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_context_usage(self):
        """Test that contexts work properly in concurrent scenarios."""
        async def create_and_use_context(user_id: str) -> str:
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=f"run_{user_id}"
            )
            
            # Simulate some async work
            await asyncio.sleep(0.01)
            
            return context.get_correlation_id()
        
        # Create multiple concurrent contexts
        tasks = [
            create_and_use_context(f"user_{i}")
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All results should be unique (different correlation IDs)
        assert len(set(results)) == 10
        
        # Each should contain the correct user ID
        for i, correlation_id in enumerate(results):
            expected_prefix = f"user_{i}:"
            assert correlation_id.startswith(expected_prefix)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])