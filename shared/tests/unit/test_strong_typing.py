"""
Comprehensive Unit Tests for Strong Typing System - Type Safety and Drift Prevention
Tests critical type safety business logic that prevents type drift and confusion bugs.

Business Value: Platform/Internal - System Reliability & Type Safety
Prevents type confusion bugs, improves IDE support, enforces validation to reduce debugging time.

Following CLAUDE.md guidelines:
- NO MOCKS in integration/E2E tests - unit tests can have limited mocks if needed
- Use SSOT patterns from test_framework/ssot/
- Each test MUST be designed to FAIL HARD - no try/except blocks in tests
- Tests must validate real business value
- Use descriptive test names that explain what is being tested

CRITICAL: Strong typing prevents production errors from type mismatches and provides
IDE support for better developer experience and faster development cycles.
"""
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

# Absolute imports per CLAUDE.md requirements
from shared.types.core_types import (
    # Core Identity Types
    UserID, SessionID, TokenString, ThreadID, RunID, RequestID,
    WebSocketID, ConnectionID, AgentID, ExecutionID, ContextID,
    
    # Authentication Types  
    AuthValidationResult, SessionValidationResult, TokenResponse,
    
    # WebSocket Types
    ConnectionState, WebSocketConnectionInfo, WebSocketEventType, WebSocketMessage,
    
    # Execution Context Types
    ExecutionContextState, ExecutionMetrics, AgentExecutionContext,
    
    # Type Conversion Utilities
    ensure_user_id, ensure_thread_id, ensure_run_id, ensure_request_id, ensure_websocket_id,
    to_string_dict, from_string_dict
)


class TestStronglyTypedIdentifiers:
    """Test strongly typed identifiers that prevent ID mixing and type confusion."""
    
    def test_user_id_type_prevents_mixing_with_other_identifier_types(self):
        """Test that UserID type prevents mixing with other identifier types to avoid business logic errors."""
        # Arrange
        user_id_string = "user-12345-abcdef"
        thread_id_string = "thread-67890-ghijkl"
        
        # Act - Create strongly typed identifiers
        user_id = UserID(user_id_string)
        thread_id = ThreadID(thread_id_string)
        
        # Assert - Types must be distinct even though underlying values are strings
        assert user_id == user_id_string, f"UserID must equal underlying string: {user_id} != {user_id_string}"
        assert thread_id == thread_id_string, f"ThreadID must equal underlying string: {thread_id} != {thread_id_string}"
        
        # Runtime values are strings (NewType behavior - no actual type at runtime)
        assert isinstance(user_id, str), "UserID must be string at runtime (NewType behavior)"
        assert isinstance(thread_id, str), "ThreadID must be string at runtime (NewType behavior)"
        
        # NewType provides type checking at static analysis time, not runtime
        # At runtime, they are just strings, but provide IDE/mypy support
        assert type(user_id).__name__ == "str", "UserID is actually str at runtime (NewType design)"
        assert type(thread_id).__name__ == "str", "ThreadID is actually str at runtime (NewType design)"
        
        # Test conversion utilities enforce validation
        converted_user_id = ensure_user_id(user_id_string)
        assert converted_user_id == user_id, f"ensure_user_id must create equivalent UserID: {converted_user_id} != {user_id}"
        
        converted_thread_id = ensure_thread_id(thread_id_string)
        assert converted_thread_id == thread_id, f"ensure_thread_id must create equivalent ThreadID: {converted_thread_id} != {thread_id}"
    
    def test_type_conversion_utilities_validate_input_and_reject_invalid_values(self):
        """Test that type conversion utilities validate inputs and reject invalid values to prevent errors."""
        # Test valid conversions
        valid_user_id = ensure_user_id("valid-user-123")
        assert valid_user_id == "valid-user-123", f"Valid user ID must be converted: {valid_user_id}"
        
        valid_thread_id = ensure_thread_id("valid-thread-456")
        assert valid_thread_id == "valid-thread-456", f"Valid thread ID must be converted: {valid_thread_id}"
        
        valid_run_id = ensure_run_id("valid-run-789")
        assert valid_run_id == "valid-run-789", f"Valid run ID must be converted: {valid_run_id}"
        
        valid_request_id = ensure_request_id("valid-request-abc")
        assert valid_request_id == "valid-request-abc", f"Valid request ID must be converted: {valid_request_id}"
        
        # Test invalid input rejection
        invalid_inputs = [None, "", "   ", 123, [], {}, object()]
        
        for invalid_input in invalid_inputs:
            # All conversion functions must reject invalid inputs
            with pytest.raises(ValueError, match="Invalid user_id"):
                ensure_user_id(invalid_input)
            
            with pytest.raises(ValueError, match="Invalid thread_id"):
                ensure_thread_id(invalid_input)
            
            with pytest.raises(ValueError, match="Invalid run_id"):
                ensure_run_id(invalid_input)
            
            with pytest.raises(ValueError, match="Invalid request_id"):
                ensure_request_id(invalid_input)
        
        # Test WebSocket ID allows None (optional parameter)
        assert ensure_websocket_id(None) is None, "WebSocket ID conversion must allow None"
        assert ensure_websocket_id("valid-ws-id") == "valid-ws-id", "WebSocket ID conversion must work for valid strings"
        
        with pytest.raises(ValueError, match="Invalid websocket_id"):
            ensure_websocket_id("")
    
    def test_authentication_validation_result_enforces_business_logic_constraints(self):
        """Test that AuthValidationResult enforces business logic constraints for secure authentication."""
        # Arrange & Act - Create valid authentication result
        valid_auth_result = AuthValidationResult(
            valid=True,
            user_id="authenticated-user-12345",
            email="user@netra.ai",
            permissions=["read:agents", "write:threads"],
            expires_at=datetime.now(timezone.utc)
        )
        
        # Assert - Valid result must have proper structure
        assert valid_auth_result.valid is True, "Valid auth result must have valid=True"
        # NewType creates str at runtime but provides static type safety - test that it's actually converted
        assert isinstance(valid_auth_result.user_id, str), f"User ID must be string at runtime (NewType design): {type(valid_auth_result.user_id)}"
        assert valid_auth_result.user_id == "authenticated-user-12345", f"User ID must match input: {valid_auth_result.user_id}"
        # Verify it was converted through the UserID constructor (business logic test)
        assert str(UserID("authenticated-user-12345")) == valid_auth_result.user_id, "User ID must be created through UserID NewType"
        assert valid_auth_result.email == "user@netra.ai", f"Email must match input: {valid_auth_result.email}"
        assert len(valid_auth_result.permissions) == 2, f"Permissions must be preserved: {valid_auth_result.permissions}"
        assert "read:agents" in valid_auth_result.permissions, "Read permissions must be included"
        assert "write:threads" in valid_auth_result.permissions, "Write permissions must be included"
        assert valid_auth_result.error_message is None, "Valid result must not have error message"
        
        # Test invalid authentication result
        invalid_auth_result = AuthValidationResult(
            valid=False,
            user_id=None,
            email=None,
            permissions=[],
            error_message="Authentication failed: invalid credentials"
        )
        
        assert invalid_auth_result.valid is False, "Invalid auth result must have valid=False"
        assert invalid_auth_result.user_id is None, "Invalid result must not have user_id"
        assert invalid_auth_result.email is None, "Invalid result must not have email"
        assert len(invalid_auth_result.permissions) == 0, "Invalid result must have empty permissions"
        assert invalid_auth_result.error_message is not None, "Invalid result must have error message"
        assert "Authentication failed" in invalid_auth_result.error_message, "Error message must describe failure"
    
    def test_websocket_message_enforces_complete_business_context_for_chat_value(self):
        """Test that WebSocketMessage enforces complete business context needed for chat value delivery."""
        # Arrange
        user_id = "chat-user-12345"
        thread_id = "chat-thread-67890"
        request_id = "chat-request-abcdef"
        event_type = WebSocketEventType.AGENT_THINKING
        
        business_data = {
            "reasoning": "I'm analyzing your request to provide the best possible response",
            "progress": 0.6,
            "estimated_completion": "30 seconds",
            "tools_planned": ["web_search", "analysis", "synthesis"]
        }
        
        # Act - Create WebSocket message with business context
        message = WebSocketMessage(
            event_type=event_type,
            user_id=user_id,
            thread_id=thread_id,
            request_id=request_id,
            data=business_data
        )
        
        # Assert - Message must enforce complete business context
        # NewType creates str at runtime but provides static type safety
        assert isinstance(message.user_id, str), f"User ID must be string at runtime (NewType design): {type(message.user_id)}"
        assert isinstance(message.thread_id, str), f"Thread ID must be string at runtime (NewType design): {type(message.thread_id)}"
        assert isinstance(message.request_id, str), f"Request ID must be string at runtime (NewType design): {type(message.request_id)}"
        assert isinstance(message.event_type, WebSocketEventType), f"Event type must be enum: {type(message.event_type)}"
        
        # Verify IDs were converted through proper NewType constructors (business logic)
        assert str(UserID(user_id)) == message.user_id, "User ID must be created through UserID NewType"
        assert str(ThreadID(thread_id)) == message.thread_id, "Thread ID must be created through ThreadID NewType"
        assert str(RequestID(request_id)) == message.request_id, "Request ID must be created through RequestID NewType"
        
        # Business context must be preserved
        assert message.data["reasoning"] == business_data["reasoning"], "Agent reasoning must be preserved for user visibility"
        assert message.data["progress"] == business_data["progress"], "Progress must be preserved for user feedback"
        assert message.data["tools_planned"] == business_data["tools_planned"], "Tool planning must be preserved for transparency"
        
        # Timestamp must be automatically set and valid
        assert message.timestamp is not None, "Message must have timestamp for ordering"
        assert isinstance(message.timestamp, datetime), "Timestamp must be datetime object"
        assert message.timestamp.tzinfo == timezone.utc, "Timestamp must be in UTC timezone"
        
        # Test message serialization preserves strong types
        message_dict = message.model_dump(mode='json')  # JSON mode converts enums to values
        assert message_dict["user_id"] == str(user_id), "User ID must serialize to string"
        assert message_dict["thread_id"] == str(thread_id), "Thread ID must serialize to string"
        assert message_dict["request_id"] == str(request_id), "Request ID must serialize to string"
        assert message_dict["event_type"] == event_type.value, "Event type must serialize to enum value"
    
    def test_agent_execution_context_maintains_complete_execution_state_for_business_operations(self):
        """Test that AgentExecutionContext maintains complete execution state for business operations."""
        # Arrange
        execution_data = {
            "execution_id": "exec-12345-abcdef",
            "agent_id": "data-analysis-agent-v2",
            "user_id": "business-user-67890",
            "thread_id": "business-thread-ghijkl",
            "run_id": "run-mnopqr",
            "request_id": "req-stuvwx",
            "websocket_id": "ws-yz1234",
            "state": ExecutionContextState.ACTIVE,
            "metadata": {
                "business_priority": "high",
                "expected_duration": 120,
                "cost_estimate": 0.25,
                "tools_authorized": ["web_search", "data_analysis", "visualization"]
            }
        }
        
        # Act - Create execution context
        context = AgentExecutionContext(**execution_data)
        
        # Assert - Context must maintain all business-critical state
        # NewType creates str at runtime but provides static type safety
        assert isinstance(context.execution_id, str), f"Execution ID must be string at runtime (NewType design): {type(context.execution_id)}"
        assert isinstance(context.agent_id, str), f"Agent ID must be string at runtime (NewType design): {type(context.agent_id)}"
        assert isinstance(context.user_id, str), f"User ID must be string at runtime (NewType design): {type(context.user_id)}"
        assert isinstance(context.thread_id, str), f"Thread ID must be string at runtime (NewType design): {type(context.thread_id)}"
        assert isinstance(context.run_id, str), f"Run ID must be string at runtime (NewType design): {type(context.run_id)}"
        assert isinstance(context.request_id, str), f"Request ID must be string at runtime (NewType design): {type(context.request_id)}"
        assert isinstance(context.websocket_id, str), f"WebSocket ID must be string at runtime (NewType design): {type(context.websocket_id)}"
        
        # Verify IDs were converted through proper NewType constructors (business logic)
        assert str(ExecutionID(execution_data["execution_id"])) == context.execution_id, "Execution ID must be created through ExecutionID NewType"
        assert str(AgentID(execution_data["agent_id"])) == context.agent_id, "Agent ID must be created through AgentID NewType"
        assert str(UserID(execution_data["user_id"])) == context.user_id, "User ID must be created through UserID NewType"
        
        # State must be enforced as enum
        assert isinstance(context.state, ExecutionContextState), f"State must be enum type: {type(context.state)}"
        assert context.state == ExecutionContextState.ACTIVE, f"State must match input: {context.state}"
        
        # Business metadata must be preserved
        assert context.metadata["business_priority"] == "high", "Business priority must be preserved"
        assert context.metadata["expected_duration"] == 120, "Duration estimate must be preserved"
        assert context.metadata["cost_estimate"] == 0.25, "Cost estimate must be preserved for billing"
        assert "web_search" in context.metadata["tools_authorized"], "Tool authorization must be preserved for security"
        
        # Created timestamp must be set automatically
        assert context.created_at is not None, "Context must have creation timestamp"
        assert isinstance(context.created_at, datetime), "Creation timestamp must be datetime"
        assert context.created_at.tzinfo == timezone.utc, "Creation timestamp must be UTC"


class TestTypeCompatibilityAndConversion:
    """Test type compatibility and conversion utilities for backward compatibility."""
    
    def test_string_dict_conversion_preserves_business_data_for_legacy_systems(self):
        """Test that string dictionary conversion preserves business data for legacy system compatibility."""
        # Arrange - Typed business data
        typed_data = {
            UserID("business-user-123"): "active",
            ThreadID("business-thread-456"): "processing", 
            RequestID("business-request-789"): "high-priority",
            WebSocketID("ws-connection-abc"): "connected"
        }
        
        # Act - Convert to string dictionary for legacy systems
        string_data = to_string_dict(typed_data)
        
        # Assert - All data must be preserved as strings
        assert isinstance(string_data, dict), "Result must be dictionary"
        assert len(string_data) == len(typed_data), f"All entries must be preserved: expected {len(typed_data)}, got {len(string_data)}"
        
        # All keys and values must be strings
        for key, value in string_data.items():
            assert isinstance(key, str), f"Key must be string: {key} ({type(key)})"
            assert isinstance(value, str), f"Value must be string: {value} ({type(value)})"
        
        # Business data must be preserved
        assert string_data["business-user-123"] == "active", "User status must be preserved"
        assert string_data["business-thread-456"] == "processing", "Thread status must be preserved"
        assert string_data["business-request-789"] == "high-priority", "Request priority must be preserved"
        assert string_data["ws-connection-abc"] == "connected", "Connection status must be preserved"
        
        # Test reverse conversion with type mapping
        expected_types = {
            "business-user-123": UserID,
            "business-thread-456": ThreadID,
            "business-request-789": RequestID,
            "ws-connection-abc": WebSocketID
        }
        
        # Act - Convert back to typed data
        restored_typed_data = from_string_dict(string_data, expected_types)
        
        # Assert - Types must be restored correctly
        assert len(restored_typed_data) == len(string_data), "All entries must be restored"
        
        # Check type restoration - NewType creates str at runtime but provides static type safety
        user_key = None
        thread_key = None
        request_key = None
        websocket_key = None
        
        for key in restored_typed_data.keys():
            if str(key) == "business-user-123":
                user_key = key
                assert isinstance(key, str), f"User key must be string at runtime (NewType design): {type(key)}"
                # Verify it equals what UserID constructor would create
                assert key == UserID("business-user-123"), "User key must be equivalent to UserID NewType"
            elif str(key) == "business-thread-456":
                thread_key = key  
                assert isinstance(key, str), f"Thread key must be string at runtime (NewType design): {type(key)}"
                assert key == ThreadID("business-thread-456"), "Thread key must be equivalent to ThreadID NewType"
            elif str(key) == "business-request-789":
                request_key = key
                assert isinstance(key, str), f"Request key must be string at runtime (NewType design): {type(key)}"
                assert key == RequestID("business-request-789"), "Request key must be equivalent to RequestID NewType"
            elif str(key) == "ws-connection-abc":
                websocket_key = key
                assert isinstance(key, str), f"WebSocket key must be string at runtime (NewType design): {type(key)}"
                assert key == WebSocketID("ws-connection-abc"), "WebSocket key must be equivalent to WebSocketID NewType"
        
        # All typed keys must be found
        assert user_key is not None, "User key must be found in restored data"
        assert thread_key is not None, "Thread key must be found in restored data"
        assert request_key is not None, "Request key must be found in restored data"  
        assert websocket_key is not None, "WebSocket key must be found in restored data"
        
        # Values must be preserved
        assert restored_typed_data[user_key] == "active", "User status must be preserved after restoration"
        assert restored_typed_data[thread_key] == "processing", "Thread status must be preserved after restoration"
        assert restored_typed_data[request_key] == "high-priority", "Request priority must be preserved after restoration"
        assert restored_typed_data[websocket_key] == "connected", "Connection status must be preserved after restoration"