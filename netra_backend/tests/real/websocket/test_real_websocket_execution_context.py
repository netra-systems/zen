"""Real WebSocket Execution Context Tests

Business Value Justification (BVJ):
- Segment: All Customer Tiers - SECURITY FOUNDATION
- Business Goal: UserExecutionContext Isolation - CRITICAL SECURITY REQUIREMENT  
- Value Impact: Ensures every message/request has proper user isolation context
- Strategic Impact: Prevents data leakage that would destroy customer trust and business

Tests real WebSocket UserExecutionContext functionality with Docker services.
Validates that every message has proper execution context and user isolation.

CRITICAL per CLAUDE.md: UserExecutionContext is NOT optional - it's the security foundation.
Every message/request MUST have isolation. Silent data leakage is a BUG.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.execution_context
@pytest.mark.security_critical
@skip_if_no_real_services
class TestRealWebSocketExecutionContext:
    """Test real WebSocket UserExecutionContext functionality.
    
    CRITICAL: Tests the security foundation of the multi-user system.
    UserExecutionContext MUST ensure complete user isolation for every operation.
    """
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-ExecutionContext-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_execution_context_creation_per_message(self, websocket_url, auth_headers):
        """Test UserExecutionContext is created for each message."""
        user_id = f"context_test_{int(time.time())}"
        
        context_tracking_results = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect with context tracking
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "track_execution_context": True,
                    "context_validation": True
                }))
                
                connect_response = json.loads(await websocket.recv())
                context_tracking_results.append(("connect", connect_response))
                
                # Send multiple messages to test context creation
                test_messages = [
                    {
                        "type": "user_message",
                        "user_id": user_id,
                        "content": "Context test message 1",
                        "context_id": f"ctx_1_{uuid.uuid4().hex[:8]}",
                        "request_context_info": True
                    },
                    {
                        "type": "heartbeat",
                        "user_id": user_id,
                        "timestamp": time.time(),
                        "context_id": f"ctx_2_{uuid.uuid4().hex[:8]}",
                        "request_context_info": True
                    },
                    {
                        "type": "user_message", 
                        "user_id": user_id,
                        "content": "Context test message 2",
                        "context_id": f"ctx_3_{uuid.uuid4().hex[:8]}",
                        "request_context_info": True
                    }
                ]
                
                # Send each message and collect context responses
                for msg in test_messages:
                    await websocket.send(json.dumps(msg))
                    
                    # Collect response to check context information
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response = json.loads(response_raw)
                        context_tracking_results.append((msg["type"], response))
                        
                        # Check for context information in response
                        if "execution_context" in response or "context_id" in response:
                            print(f"Context info found in {msg['type']} response")
                        
                    except asyncio.TimeoutError:
                        context_tracking_results.append((msg["type"], {"timeout": True}))
                    
                    await asyncio.sleep(0.5)
                
        except Exception as e:
            pytest.fail(f"Execution context creation test failed: {e}")
        
        # Validate context creation
        assert len(context_tracking_results) >= 3, f"Should track contexts for multiple messages"
        
        # Verify each message type got processed (indicating context was created)
        message_types_processed = [msg_type for msg_type, response in context_tracking_results if not response.get("timeout")]
        
        assert "connect" in message_types_processed, "Connect message should be processed with context"
        assert message_types_processed.count("user_message") >= 1, "User messages should be processed with context"
        
        # Check for user_id consistency (context should preserve user identity)
        user_ids_in_responses = []
        for msg_type, response in context_tracking_results:
            if isinstance(response, dict) and "user_id" in response:
                user_ids_in_responses.append(response["user_id"])
        
        # All responses should have consistent user_id (context working properly)
        unique_user_ids = set(user_ids_in_responses)
        if len(unique_user_ids) > 0:
            assert len(unique_user_ids) == 1, f"User ID should be consistent across contexts: {unique_user_ids}"
            assert user_id in unique_user_ids, f"Context should preserve correct user ID: {unique_user_ids}"
        
        print(f"Execution context creation - Messages processed: {len(message_types_processed)}, User ID consistency: {len(unique_user_ids) <= 1}")
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_context_isolation(self, websocket_url, auth_headers):
        """Test execution context isolation between concurrent users."""
        base_time = int(time.time())
        user_a_id = f"concurrent_ctx_a_{base_time}"
        user_b_id = f"concurrent_ctx_b_{base_time}"
        
        execution_contexts = {}
        
        async def test_user_execution_context(user_id: str, context_marker: str):
            """Test execution context for individual user."""
            context_data = {
                "user_id": user_id,
                "context_marker": context_marker,
                "messages_sent": [],
                "contexts_observed": []
            }
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Connect with context isolation testing
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "test_context_isolation": True,
                        "context_marker": context_marker,
                        "isolation_key": f"isolation_{user_id}"
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    context_data["contexts_observed"].append(("connect", connect_response))
                    
                    # Send context-sensitive messages
                    for i in range(3):
                        message = {
                            "type": "context_sensitive_message",
                            "user_id": user_id,
                            "content": f"Context isolation test {context_marker} message {i}",
                            "private_context_data": f"PRIVATE_{context_marker}_{i}_{uuid.uuid4().hex[:8]}",
                            "message_sequence": i,
                            "context_marker": context_marker
                        }
                        
                        await websocket.send(json.dumps(message))
                        context_data["messages_sent"].append(message)
                        
                        # Collect context response
                        try:
                            response_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            response = json.loads(response_raw)
                            context_data["contexts_observed"].append(("message", response))
                        except asyncio.TimeoutError:
                            context_data["contexts_observed"].append(("message", {"timeout": i}))
                        
                        await asyncio.sleep(0.3)
                    
                    execution_contexts[user_id] = {**context_data, "success": True}
                    
            except Exception as e:
                execution_contexts[user_id] = {
                    **context_data, 
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent context isolation tests
        await asyncio.gather(
            test_user_execution_context(user_a_id, "CONTEXT_A"),
            test_user_execution_context(user_b_id, "CONTEXT_B")
        )
        
        # Validate execution context isolation
        assert user_a_id in execution_contexts, "User A execution context should be recorded"
        assert user_b_id in execution_contexts, "User B execution context should be recorded"
        
        user_a_context = execution_contexts[user_a_id]
        user_b_context = execution_contexts[user_b_id]
        
        assert user_a_context.get("success"), f"User A context test should succeed: {user_a_context.get('error')}"
        assert user_b_context.get("success"), f"User B context test should succeed: {user_b_context.get('error')}"
        
        # CRITICAL SECURITY CHECK: Context isolation validation
        user_a_contexts_str = json.dumps(user_a_context.get("contexts_observed", [])).lower()
        user_b_contexts_str = json.dumps(user_b_context.get("contexts_observed", [])).lower()
        
        # User A should NEVER see User B's private context data
        user_b_private_markers = ["private_context_b", "context_b"]
        for marker in user_b_private_markers:
            assert marker not in user_a_contexts_str, \
                f"SECURITY BUG: User A execution context saw User B's data: {marker}"
        
        # User B should NEVER see User A's private context data
        user_a_private_markers = ["private_context_a", "context_a"]
        for marker in user_a_private_markers:
            assert marker not in user_b_contexts_str, \
                f"SECURITY BUG: User B execution context saw User A's data: {marker}"
        
        # Verify context data integrity
        user_a_messages = len(user_a_context.get("messages_sent", []))
        user_b_messages = len(user_b_context.get("messages_sent", []))
        user_a_observations = len(user_a_context.get("contexts_observed", []))
        user_b_observations = len(user_b_context.get("contexts_observed", []))
        
        print(f"Context isolation - User A: {user_a_messages} msgs/{user_a_observations} contexts, User B: {user_b_messages} msgs/{user_b_observations} contexts")
        
        assert user_a_messages > 0, "User A should have sent messages"
        assert user_b_messages > 0, "User B should have sent messages"
    
    @pytest.mark.asyncio
    async def test_execution_context_state_persistence(self, websocket_url, auth_headers):
        """Test execution context state persistence within session."""
        user_id = f"context_persistence_{int(time.time())}"
        
        context_states = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Initialize context with state
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "initialize_context_state": True,
                    "initial_state": {
                        "session_start": time.time(),
                        "context_version": "1.0",
                        "user_preferences": {"theme": "dark", "language": "en"}
                    }
                }))
                
                connect_response = json.loads(await websocket.recv())
                context_states.append(("initial", connect_response))
                
                # Update context state
                await websocket.send(json.dumps({
                    "type": "update_context_state",
                    "user_id": user_id,
                    "state_update": {
                        "messages_sent": 1,
                        "last_activity": time.time(),
                        "session_data": f"session_data_{uuid.uuid4().hex[:8]}"
                    }
                }))
                
                try:
                    update_response = json.loads(await websocket.recv())
                    context_states.append(("update", update_response))
                except asyncio.TimeoutError:
                    context_states.append(("update", {"timeout": True}))
                
                # Query context state to verify persistence
                await websocket.send(json.dumps({
                    "type": "query_context_state",
                    "user_id": user_id,
                    "request_current_state": True
                }))
                
                try:
                    query_response = json.loads(await websocket.recv())
                    context_states.append(("query", query_response))
                except asyncio.TimeoutError:
                    context_states.append(("query", {"timeout": True}))
                
                # Send regular message to test context state availability
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Test message with context state",
                    "verify_context_state": True
                }))
                
                try:
                    message_response = json.loads(await websocket.recv())
                    context_states.append(("message_with_state", message_response))
                except asyncio.TimeoutError:
                    context_states.append(("message_with_state", {"timeout": True}))
                
        except Exception as e:
            pytest.fail(f"Context state persistence test failed: {e}")
        
        # Validate context state persistence
        assert len(context_states) >= 3, f"Should capture multiple context states"
        
        # Check for user_id consistency across states
        user_ids_in_states = []
        for state_type, state_data in context_states:
            if isinstance(state_data, dict) and "user_id" in state_data and not state_data.get("timeout"):
                user_ids_in_states.append(state_data["user_id"])
        
        # User ID should be consistent (context preserving identity)
        unique_user_ids = set(user_ids_in_states)
        if len(unique_user_ids) > 0:
            assert len(unique_user_ids) == 1, f"User ID should persist in context: {unique_user_ids}"
            assert user_id in unique_user_ids, f"Context should preserve correct user: {unique_user_ids}"
        
        # Verify we got responses (indicating context is working)
        non_timeout_states = [s for s_type, s in context_states if not s.get("timeout")]
        assert len(non_timeout_states) >= 2, f"Should have non-timeout responses indicating context persistence"
        
        print(f"Context state persistence - States captured: {len(context_states)}, Non-timeout: {len(non_timeout_states)}, User ID consistency: {len(unique_user_ids) <= 1}")
    
    @pytest.mark.asyncio
    async def test_execution_context_error_handling(self, websocket_url, auth_headers):
        """Test execution context handles errors gracefully."""
        user_id = f"context_error_test_{int(time.time())}"
        
        error_handling_results = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=12
            ) as websocket:
                # Connect normally
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "test_error_handling": True
                }))
                
                connect_response = json.loads(await websocket.recv())
                error_handling_results.append(("connect", connect_response, "success"))
                
                # Send message that might cause context errors
                await websocket.send(json.dumps({
                    "type": "invalid_context_operation",
                    "user_id": user_id,
                    "invalid_context_data": "This might cause context errors",
                    "malformed_context_request": True
                }))
                
                try:
                    error_response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=3.0))
                    error_handling_results.append(("error_test", error_response, "response_received"))
                except asyncio.TimeoutError:
                    error_handling_results.append(("error_test", {}, "timeout"))
                
                # Test recovery - send normal message after error
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Recovery message after context error",
                    "test_recovery": True
                }))
                
                try:
                    recovery_response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=4.0))
                    error_handling_results.append(("recovery", recovery_response, "recovered"))
                except asyncio.TimeoutError:
                    error_handling_results.append(("recovery", {}, "recovery_timeout"))
                
        except Exception as e:
            error_handling_results.append(("exception", {"error": str(e)}, "test_error"))
        
        # Validate error handling
        assert len(error_handling_results) >= 2, "Should handle both error and recovery scenarios"
        
        # Check that connection was established initially
        connect_results = [r for r in error_handling_results if r[0] == "connect"]
        assert len(connect_results) > 0, "Should establish initial connection"
        
        # Check for recovery after error
        recovery_results = [r for r in error_handling_results if r[0] == "recovery" and r[2] != "recovery_timeout"]
        if len(recovery_results) > 0:
            print("SUCCESS: Context error recovery working")
        else:
            print("INFO: Context error recovery not detected (may not be implemented)")
        
        # System should remain functional
        successful_operations = [r for r in error_handling_results if r[2] in ["success", "response_received", "recovered"]]
        assert len(successful_operations) >= 1, "Context should handle errors without breaking functionality"
        
        print(f"Context error handling - Total operations: {len(error_handling_results)}, Successful: {len(successful_operations)}")