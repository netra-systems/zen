"""
WebSocket Event Routing Type Safety Unit Tests - DESIGNED TO FAIL

This comprehensive test suite is designed to FAIL initially to expose critical type safety 
violations in WebSocket event routing components. The tests validate that string-based IDs
are being incorrectly used instead of strongly typed identifiers.

CRITICAL VIOLATIONS TO EXPOSE:
1. `unified_manager.py:484` - `thread_id: str` should be `ThreadID`
2. `unified_manager.py:1895` - `connection_id: str, thread_id: str` issues
3. `protocols.py:144` - Protocol interface type violations
4. `utils.py:680` - `str(message["thread_id"])` casting issues

Business Value Justification:
- Segment: Platform/Internal - Type Safety & Multi-User Isolation
- Business Goal: System Reliability & Security
- Value Impact: Prevents cross-user data contamination in WebSocket routing
- Strategic Impact: Eliminates production bugs from type confusion and ID mixing

IMPORTANT: These tests are designed to FAIL until type safety fixes are implemented.
Success would indicate the violations have been resolved.
"""

import asyncio
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.types import (
    UserID, ThreadID, RunID, RequestID, WebSocketID, ConnectionID,
    ensure_user_id, ensure_thread_id, ensure_request_id,
    StronglyTypedWebSocketEvent, WebSocketEventType
)
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import the components with violations
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.websocket_core.utils import extract_user_info_from_message


class TestWebSocketEventRoutingTypeSafetyViolations(SSotBaseTestCase):
    """
    Unit tests to expose WebSocket type safety violations.
    
    CRITICAL: These tests are designed to FAIL until violations are fixed.
    Each test exposes a specific type safety issue that enables data leakage.
    """
    
    def setup_method(self):
        """Set up test fixtures with strongly typed identifiers."""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        
        # Create strongly typed test identifiers
        self.user_id_1 = ensure_user_id("test-user-1-uuid")
        self.user_id_2 = ensure_user_id("test-user-2-uuid") 
        self.thread_id_1 = ensure_thread_id("thread-1-uuid")
        self.thread_id_2 = ensure_thread_id("thread-2-uuid")
        self.request_id_1 = ensure_request_id("request-1-uuid")
        self.request_id_2 = ensure_request_id("request-2-uuid")
        
        # Create test WebSocket manager
        self.websocket_manager = UnifiedWebSocketManager()
        
        # Mock WebSocket connections
        self.websocket_1 = MagicMock()
        self.websocket_2 = MagicMock()
        
    # =============================================================================
    # CRITICAL VIOLATION 1: unified_manager.py:484 - send_to_thread type confusion
    # =============================================================================
    
    def test_send_to_thread_accepts_string_instead_of_thread_id_type(self):
        """
        CRITICAL FAILURE TEST: Expose that send_to_thread accepts raw string
        instead of ThreadID type, enabling type confusion and potential routing errors.
        
        VIOLATION: unified_manager.py:484 - `thread_id: str` should be `ThreadID`
        RISK: String-based thread_id can be mixed with user_id, causing message misrouting
        """
        # This test should FAIL because the method incorrectly accepts str instead of ThreadID
        manager = UnifiedWebSocketManager()
        
        # Create a message intended for thread_id_1
        test_message = {
            "type": "agent_completed",
            "data": {"result": "sensitive_data_for_user_1"}
        }
        
        # CRITICAL: This should fail type checking but currently doesn't
        # The method should reject raw strings and require ThreadID type
        raw_string_thread_id = "thread-1-uuid"  # This is a str, not ThreadID
        
        with pytest.raises(TypeError, match="Expected ThreadID, got str"):
            # This should fail because we're passing str instead of ThreadID
            asyncio.run(manager.send_to_thread(raw_string_thread_id, test_message))
            
        # If we reach here, the type safety violation exists
        pytest.fail("VIOLATION DETECTED: send_to_thread accepts raw string instead of ThreadID type")
        
    def test_send_to_thread_id_confusion_vulnerability(self):
        """
        CRITICAL FAILURE TEST: Demonstrate how string-based IDs enable ID confusion.
        
        RISK: user_id could be accidentally passed as thread_id, causing cross-user contamination
        """
        manager = UnifiedWebSocketManager()
        
        # Create message with sensitive data
        sensitive_message = {
            "type": "agent_completed", 
            "data": {"private_key": "user_1_secret_data"}
        }
        
        # DANGEROUS: user_id and thread_id are both strings, can be confused
        user_id_as_string = str(self.user_id_1)  # "test-user-1-uuid"
        thread_id_as_string = str(self.thread_id_1)  # "thread-1-uuid"
        
        # This demonstrates the vulnerability - we could accidentally swap them
        # and the type system wouldn't catch it
        try:
            # WRONG: Passing user_id where thread_id expected
            asyncio.run(manager.send_to_thread(user_id_as_string, sensitive_message))
            
            # If this doesn't fail, we have a type safety violation
            pytest.fail("VIOLATION: Method accepts user_id as thread_id - type confusion possible")
            
        except Exception as e:
            # We expect this to fail due to type safety, but currently it might not
            if "type" not in str(e).lower():
                pytest.fail(f"Expected type error, got: {e}")
                
    # =============================================================================
    # CRITICAL VIOLATION 2: unified_manager.py:1895 - update_connection_thread types
    # =============================================================================
    
    def test_update_connection_thread_string_parameters_violation(self):
        """
        CRITICAL FAILURE TEST: Expose string parameter types in update_connection_thread.
        
        VIOLATION: unified_manager.py:1895 - `connection_id: str, thread_id: str`
        SHOULD BE: `connection_id: ConnectionID, thread_id: ThreadID`
        """
        manager = UnifiedWebSocketManager()
        
        # These should be strongly typed, not strings
        raw_connection_id = "conn-123"  # str instead of ConnectionID
        raw_thread_id = "thread-456"   # str instead of ThreadID
        
        # This should fail type validation but currently doesn't
        with pytest.raises(TypeError, match="Expected ConnectionID.*ThreadID"):
            result = manager.update_connection_thread(raw_connection_id, raw_thread_id)
            
        # If we reach here without error, violation exists
        pytest.fail("VIOLATION: update_connection_thread accepts raw strings instead of typed IDs")
        
    def test_update_connection_thread_parameter_swap_vulnerability(self):
        """
        CRITICAL FAILURE TEST: Demonstrate parameter swap vulnerability.
        
        RISK: connection_id and thread_id could be swapped due to both being strings
        """
        manager = UnifiedWebSocketManager()
        
        connection_str = "connection-abc-123"
        thread_str = "thread-xyz-789"
        
        # Both parameters are strings, so they can be accidentally swapped
        # This should be caught by type system but isn't
        
        try:
            # WRONG ORDER: thread_id, connection_id instead of connection_id, thread_id
            result = manager.update_connection_thread(thread_str, connection_str)
            
            # If this succeeds, we have a parameter confusion vulnerability
            if result is not False:  # Method might return success even with wrong params
                pytest.fail("VIOLATION: Parameter order confusion not detected - both are strings")
                
        except Exception as e:
            # Should fail due to type safety, but might not
            if "parameter" not in str(e).lower() and "type" not in str(e).lower():
                pytest.fail(f"Expected parameter/type error, got: {e}")
                
    # =============================================================================
    # CRITICAL VIOLATION 3: protocols.py:144 - Protocol interface violations
    # =============================================================================
    
    def test_websocket_protocol_interface_string_types_violation(self):
        """
        CRITICAL FAILURE TEST: Expose protocol interface using string types.
        
        VIOLATION: protocols.py:144 - Protocol defines str instead of typed IDs
        IMPACT: All implementations inherit the weak typing, enabling violations system-wide
        """
        from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
        import inspect
        
        # Get the method signature from the protocol
        update_method = getattr(WebSocketManagerProtocol, 'update_connection_thread')
        signature = inspect.signature(update_method)
        
        # Check parameter types
        connection_id_param = signature.parameters.get('connection_id')
        thread_id_param = signature.parameters.get('thread_id')
        
        # CRITICAL: These should be typed as ConnectionID and ThreadID, not str
        if connection_id_param and connection_id_param.annotation == str:
            pytest.fail("VIOLATION: Protocol defines connection_id as str instead of ConnectionID")
            
        if thread_id_param and thread_id_param.annotation == str:
            pytest.fail("VIOLATION: Protocol defines thread_id as str instead of ThreadID")
            
        # If we reach here, the protocol might have been fixed or we couldn't detect it
        # Let's try a different approach - test actual usage
        
        class TestProtocolImpl(WebSocketManagerProtocol):
            """Test implementation of the protocol"""
            async def add_connection(self, user_id: str, websocket: Any, request_id: str) -> str:
                return "test"
            
            async def remove_connection(self, connection_id: str) -> bool:
                return True
            
            def update_connection_thread(self, connection_id: str, thread_id: str) -> bool:
                # This should require typed parameters but doesn't
                return True
                
            async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
                return True
                
        # Test that implementation accepts raw strings (violation)
        impl = TestProtocolImpl()
        result = impl.update_connection_thread("raw_conn_id", "raw_thread_id")
        
        if result:  # If this succeeds, we have a type safety violation
            pytest.fail("VIOLATION: Protocol implementation accepts raw strings instead of typed IDs")
            
    # =============================================================================
    # CRITICAL VIOLATION 4: utils.py:680 - String casting in message extraction
    # =============================================================================
    
    def test_extract_user_info_string_casting_violation(self):
        """
        CRITICAL FAILURE TEST: Expose str() casting of thread_id in utils.
        
        VIOLATION: utils.py:680 - `str(message["thread_id"])` loses type safety
        RISK: Typed ThreadID gets converted to string, enabling type confusion downstream
        """
        # Create message with properly typed thread_id
        typed_thread_id = ensure_thread_id("test-thread-123")
        
        message_with_typed_id = {
            "thread_id": typed_thread_id,
            "user_id": self.user_id_1,
            "type": "test_message"
        }
        
        # Extract user info - this should preserve types but doesn't
        user_info = extract_user_info_from_message(message_with_typed_id)
        
        if user_info and "thread_id" in user_info:
            extracted_thread_id = user_info["thread_id"]
            
            # CRITICAL: This should preserve the ThreadID type but gets converted to str
            # Since NewType creates runtime str, we check if the original typed value was lost
            if extracted_thread_id != typed_thread_id:
                pytest.fail(f"VIOLATION: thread_id type lost in extraction - original ThreadID was converted to plain str")
                
        else:
            pytest.fail("Could not extract thread_id to test type safety")
            
    def test_extract_user_info_type_coercion_data_loss(self):
        """
        CRITICAL FAILURE TEST: Demonstrate type information loss in message processing.
        
        RISK: Type coercion enables downstream components to mix ID types
        """
        # Create strongly typed message
        message = {
            "user_id": self.user_id_1,
            "thread_id": self.thread_id_1, 
            "request_id": self.request_id_1
        }
        
        # Process through utils function
        user_info = extract_user_info_from_message(message)
        
        if user_info:
            # Check if types are preserved
            user_id_preserved = isinstance(user_info.get("user_id"), UserID)
            thread_id_preserved = isinstance(user_info.get("thread_id"), ThreadID)
            
            type_violations = []
            if not user_id_preserved:
                type_violations.append(f"user_id: expected UserID, got {type(user_info.get('user_id'))}")
            if not thread_id_preserved:
                type_violations.append(f"thread_id: expected ThreadID, got {type(user_info.get('thread_id'))}")
                
            if type_violations:
                pytest.fail(f"VIOLATIONS: Type information lost - {'; '.join(type_violations)}")
                
    # =============================================================================
    # MULTI-USER DATA LEAKAGE SCENARIO TESTS
    # =============================================================================
    
    def test_thread_id_user_id_confusion_scenario(self):
        """
        CRITICAL FAILURE TEST: Simulate real-world ID confusion leading to data leakage.
        
        SCENARIO: Developer accidentally uses user_id where thread_id expected
        RESULT: Messages intended for one thread go to another user
        """
        manager = UnifiedWebSocketManager()
        
        # Scenario: User 1 starts conversation in Thread A
        # User 2 starts conversation in Thread B  
        # Due to string-based IDs, messages can be misrouted
        
        user_1_message = {
            "type": "agent_completed",
            "data": {"private_result": "user_1_confidential_data"}
        }
        
        # DANGEROUS: In string-based system, these could be confused
        user_1_id_str = str(self.user_id_1)
        thread_1_id_str = str(self.thread_id_1)
        
        # Simulate bug: developer uses user_id where thread_id expected
        try:
            # This should fail but might not due to weak typing
            result = asyncio.run(manager.send_to_thread(user_1_id_str, user_1_message))
            
            # If this succeeds, we have a serious vulnerability
            if result:
                pytest.fail("CRITICAL VULNERABILITY: user_id accepted as thread_id - data leakage possible")
                
        except Exception as e:
            # Should fail due to type safety
            if "type" not in str(e).lower():
                # Failed for other reason, not type safety
                pass
                
    def test_connection_id_thread_id_swap_vulnerability(self):
        """
        CRITICAL FAILURE TEST: Test connection/thread ID parameter swap vulnerability.
        
        SCENARIO: Both IDs are strings, so they can be accidentally swapped in function calls
        RESULT: Wrong connection gets associated with wrong thread
        """
        manager = UnifiedWebSocketManager()
        
        # Both are strings, easy to confuse
        conn_id = "connection-user1-abc123"
        thread_id = "thread-conversation1-xyz789"
        
        # Test normal order
        result1 = manager.update_connection_thread(conn_id, thread_id)
        
        # Test swapped order - should fail but might not
        result2 = manager.update_connection_thread(thread_id, conn_id)  # WRONG ORDER
        
        # If both succeed, we have a vulnerability
        if result1 is not False and result2 is not False:
            pytest.fail("VULNERABILITY: Parameter order swap not detected - enables connection misrouting")
            
    # =============================================================================
    # MESSAGE ROUTING INTEGRITY TESTS
    # =============================================================================
    
    def test_message_routing_type_boundary_enforcement(self):
        """
        CRITICAL FAILURE TEST: Verify type boundaries are enforced in message routing.
        
        Tests that messages with mixed ID types are rejected rather than processed
        """
        # Create message with mixed ID types (should be rejected)
        mixed_message = {
            "user_id": str(self.user_id_1),      # Raw string
            "thread_id": self.thread_id_1,       # Typed ID
            "request_id": str(self.request_id_1), # Raw string
            "data": "test_data"
        }
        
        # Message processing should enforce type consistency
        try:
            user_info = extract_user_info_from_message(mixed_message)
            
            # If extraction succeeds without type validation, we have a violation
            if user_info:
                pytest.fail("VIOLATION: Mixed ID types accepted - type boundary not enforced")
                
        except Exception as e:
            # Should fail due to type inconsistency
            if "type" in str(e).lower() or "consistency" in str(e).lower():
                # Good - type boundary enforced
                pass
            else:
                pytest.fail(f"Unexpected error (not type-related): {e}")
                
    # =============================================================================
    # ASYNC CONTEXT SAFETY TESTS  
    # =============================================================================
    
    async def test_async_message_routing_context_isolation(self):
        """
        CRITICAL FAILURE TEST: Verify async message routing maintains context isolation.
        
        RISK: Async operations might leak context between different user sessions
        """
        manager = UnifiedWebSocketManager()
        
        # Create concurrent messages for different users
        user1_message = {
            "type": "agent_started",
            "data": {"user_context": "user_1_private_context"}
        }
        
        user2_message = {
            "type": "agent_started", 
            "data": {"user_context": "user_2_private_context"}
        }
        
        # Send messages concurrently - should maintain isolation
        tasks = [
            manager.send_to_thread(str(self.thread_id_1), user1_message),
            manager.send_to_thread(str(self.thread_id_2), user2_message)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Both should either succeed with proper isolation or fail due to type safety
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                if "type" not in str(result).lower():
                    pytest.fail(f"Message {i} failed unexpectedly: {result}")
                    
    # =============================================================================
    # REGRESSION TESTS FOR COMMON VIOLATIONS
    # =============================================================================
    
    def test_common_string_concatenation_vulnerability(self):
        """
        CRITICAL FAILURE TEST: Test vulnerability from string concatenation of IDs.
        
        RISK: String-based IDs can be concatenated, creating invalid composite IDs
        """
        # This should not be possible with strongly typed IDs
        user_id_str = str(self.user_id_1)
        thread_id_str = str(self.thread_id_1)
        
        # Dangerous operation that's possible with strings
        composite_id = user_id_str + ":" + thread_id_str
        
        # Try to use composite ID where single ID expected
        try:
            # This should fail type validation
            manager = UnifiedWebSocketManager()
            result = manager.update_connection_thread(composite_id, thread_id_str)
            
            if result is not False:
                pytest.fail("VULNERABILITY: Composite string ID accepted - type safety bypassed")
                
        except Exception as e:
            if "type" not in str(e).lower():
                # Failed for other reason
                pass
                
    def test_empty_string_id_vulnerability(self):
        """
        CRITICAL FAILURE TEST: Test handling of empty string IDs.
        
        RISK: Empty strings might be accepted as valid IDs, causing routing failures
        """
        manager = UnifiedWebSocketManager()
        
        # Empty strings should be rejected
        empty_connection_id = ""
        empty_thread_id = ""
        
        with pytest.raises((ValueError, TypeError), match="empty|invalid"):
            manager.update_connection_thread(empty_connection_id, empty_thread_id)
            
        # If we reach here, empty IDs were accepted (violation)
        pytest.fail("VIOLATION: Empty string IDs accepted - validation insufficient")
        
    # =============================================================================
    # PERFORMANCE IMPACT TESTS
    # =============================================================================
    
    def test_type_checking_performance_overhead(self):
        """
        Test that type checking doesn't introduce excessive performance overhead.
        
        This ensures type safety fixes are performant enough for production use.
        """
        import time
        
        manager = UnifiedWebSocketManager()
        iterations = 1000
        
        # Time string-based operations (current implementation)
        start_time = time.time()
        for i in range(iterations):
            manager.update_connection_thread(f"conn_{i}", f"thread_{i}")
        string_time = time.time() - start_time
        
        # Record performance baseline
        self.test_metrics.record_custom("string_id_operations_time", string_time)
        self.test_metrics.record_custom("string_id_operations_per_second", iterations / string_time)
        
        # Type-safe operations should not be significantly slower
        # This test documents current performance for comparison after fixes
        
        
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])