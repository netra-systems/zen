"""
E2E Tests for WebSocket Timestamp Validation in Staging Environment

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Risk Reduction & Stability
- Value Impact: Validates WebSocket chat functionality (90% of business value) works end-to-end
- Strategic Impact: Prevents timestamp validation failures from breaking user chat experience

CRITICAL E2E REQUIREMENTS per CLAUDE.md:
- ALL E2E tests MUST use authentication (JWT/OAuth) 
- Real services only - NO MOCKS
- Tests reproduce staging environment conditions
- Must test full WebSocket agent workflow with real timestamps

This test suite reproduces the staging error:
"WebSocketMessage timestamp - Input should be a valid number, unable to parse string as a number 
[type=float_parsing, input_value='2025-09-08T16:50:01.447585', input_type=str]"
"""

import pytest
import asyncio
import time
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# CRITICAL: Absolute imports per CLAUDE.md
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, get_authenticated_user_context
from test_framework.ssot.websocket import WebSocketTestHelper
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketTimestampValidationE2E:
    """E2E tests for WebSocket timestamp validation with full authentication."""

    @pytest.fixture
    async def auth_helper(self):
        """E2E auth helper with real JWT tokens."""
        helper = E2EAuthHelper()
        await helper.setup()
        yield helper
        await helper.cleanup()

    @pytest.fixture
    async def authenticated_user(self, auth_helper):
        """Get authenticated user context with JWT token."""
        return await get_authenticated_user_context(
            user_id="websocket-timestamp-e2e-user",
            email="timestamp.test@netra-staging.com"
        )

    @pytest.fixture
    def websocket_helper(self):
        """WebSocket helper for real connections."""
        return WebSocketTestHelper()

    @pytest.fixture
    def env(self):
        """Isolated environment for staging configuration.""" 
        return IsolatedEnvironment()

    async def test_authenticated_websocket_timestamp_validation_failure(
        self, auth_helper, authenticated_user, websocket_helper, env
    ):
        """
        CRITICAL E2E TEST: Full authenticated WebSocket flow with timestamp validation.
        
        This test reproduces the exact staging scenario:
        1. User authenticates with real JWT 
        2. Establishes WebSocket connection
        3. Sends start_agent message with ISO datetime timestamp
        4. Should fail on timestamp validation
        """
        user_context = authenticated_user
        
        # Connect to WebSocket with authentication
        websocket_connection = await websocket_helper.connect_authenticated(
            user_context=user_context,
            env=env
        )
        
        try:
            # Exact staging message that caused the error
            staging_message = {
                "type": "start_agent",
                "payload": {
                    "user_request": "Execute unified_data_agent with data: {'query': 'Analyze system performance metrics for Q4 2024', 'metrics': ['cpu', 'memory', 'disk'], 'timeframe': '3_months'}",
                    "agent_type": "unified_data_agent",
                    "priority": "high",
                    "message_id": "req_61eebcb6",
                    "user": "staging-e2e-user-001"
                },
                "timestamp": "2025-09-08T16:50:01.447585",  # ISO string causing error
                "message_id": "req_61eebcb6", 
                "user_id": user_context.user_id,
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}"
            }
            
            # Send message through authenticated WebSocket
            # This should fail due to timestamp validation
            with pytest.raises(Exception) as exc_info:
                await websocket_connection.send_message(staging_message)
            
            # Verify timestamp validation error
            error_str = str(exc_info.value).lower()
            timestamp_error_keywords = [
                'timestamp', 'float_parsing', 'validation', 
                'parse string as a number', 'input_value'
            ]
            
            assert any(keyword in error_str for keyword in timestamp_error_keywords), \
                f"Expected timestamp validation error, got: {exc_info.value}"
            
        finally:
            await websocket_connection.close()

    async def test_authenticated_websocket_valid_timestamp_success(
        self, auth_helper, authenticated_user, websocket_helper, env  
    ):
        """Test authenticated WebSocket flow with valid timestamp succeeds."""
        user_context = authenticated_user
        
        # Connect with authentication  
        websocket_connection = await websocket_helper.connect_authenticated(
            user_context=user_context,
            env=env
        )
        
        try:
            # Message with valid float timestamp
            valid_message = {
                "type": "start_agent",
                "payload": {
                    "user_request": "Execute unified_data_agent with valid timestamp",
                    "agent_type": "unified_data_agent",
                    "message_id": f"req_valid_{uuid.uuid4().hex[:8]}"
                },
                "timestamp": time.time(),  # Valid float timestamp
                "user_id": user_context.user_id,
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}"
            }
            
            # This should succeed
            response = await websocket_connection.send_message_and_wait_response(
                message=valid_message,
                timeout_seconds=10
            )
            
            # Verify successful processing
            assert response is not None
            assert "error" not in response.get("type", "").lower()
            
        except Exception as e:
            pytest.fail(f"Valid timestamp message should succeed: {e}")
        finally:
            await websocket_connection.close()

    async def test_multi_user_websocket_timestamp_validation(
        self, auth_helper, websocket_helper, env
    ):
        """Test timestamp validation with multiple authenticated users."""
        # Create multiple authenticated users
        users = []
        connections = []
        
        try:
            for i in range(3):
                user_context = await get_authenticated_user_context(
                    user_id=f"multi-user-timestamp-{i}",
                    email=f"user{i}.timestamp@netra-staging.com"
                )
                users.append(user_context)
                
                connection = await websocket_helper.connect_authenticated(
                    user_context=user_context,
                    env=env
                )
                connections.append(connection)
            
            # Each user sends message with invalid timestamp
            for i, (user, connection) in enumerate(zip(users, connections)):
                invalid_message = {
                    "type": "agent_thinking", 
                    "payload": {
                        "reasoning": f"User {i} processing request...",
                        "step": 1,
                        "total_steps": 5
                    },
                    "timestamp": f"2025-09-08T16:5{i}:01.{i}{i}{i}{i}{i}{i}",  # ISO string
                    "user_id": user.user_id,
                    "thread_id": f"thread_user_{i}"
                }
                
                # Should fail for each user
                with pytest.raises(Exception) as exc_info:
                    await connection.send_message(invalid_message)
                
                # Verify timestamp error
                assert any(keyword in str(exc_info.value).lower() 
                          for keyword in ['timestamp', 'validation', 'float']), \
                    f"User {i} should get timestamp validation error"
        
        finally:
            # Cleanup all connections
            for connection in connections:
                await connection.close()

    async def test_agent_pipeline_timestamp_validation_e2e(
        self, auth_helper, authenticated_user, websocket_helper, env
    ):
        """Test complete agent pipeline with timestamp validation."""
        user_context = authenticated_user
        
        websocket_connection = await websocket_helper.connect_authenticated(
            user_context=user_context,
            env=env
        )
        
        try:
            # Test critical agent events with invalid timestamps
            agent_pipeline_messages = [
                {
                    "type": "agent_started",
                    "payload": {"agent_type": "unified_data_agent", "status": "initializing"},
                    "timestamp": "2025-09-08T16:50:01.111111"
                },
                {
                    "type": "agent_thinking", 
                    "payload": {"reasoning": "Analyzing user request for data insights"},
                    "timestamp": "2025-09-08T16:50:02.222222"
                },
                {
                    "type": "tool_executing",
                    "payload": {"tool": "performance_analyzer", "status": "running"},
                    "timestamp": "2025-09-08T16:50:03.333333"
                },
                {
                    "type": "tool_completed", 
                    "payload": {"tool": "performance_analyzer", "results": {"cpu": "85%"}},
                    "timestamp": "2025-09-08T16:50:04.444444"
                },
                {
                    "type": "agent_completed",
                    "payload": {"status": "success", "results": "Analysis complete"},
                    "timestamp": "2025-09-08T16:50:05.555555"
                }
            ]
            
            # Each message should fail timestamp validation
            for i, message in enumerate(agent_pipeline_messages):
                message.update({
                    "user_id": user_context.user_id,
                    "message_id": f"agent_pipeline_{i}",
                    "thread_id": f"thread_pipeline_{uuid.uuid4().hex[:8]}"
                })
                
                with pytest.raises(Exception) as exc_info:
                    await websocket_connection.send_message(message)
                
                # Verify timestamp validation prevents pipeline execution
                error_str = str(exc_info.value).lower()
                assert any(keyword in error_str for keyword in [
                    'timestamp', 'validation', 'float_parsing'
                ]), f"Pipeline step {message['type']} should fail timestamp validation"
        
        finally:
            await websocket_connection.close()

    async def test_websocket_chat_functionality_timestamp_protection(
        self, auth_helper, authenticated_user, websocket_helper, env
    ):
        """
        CRITICAL: Test that timestamp validation protects chat functionality.
        
        This test validates that the 90% of business value (chat) is protected
        from timestamp parsing failures.
        """
        user_context = authenticated_user
        
        websocket_connection = await websocket_helper.connect_authenticated(
            user_context=user_context,
            env=env
        )
        
        try:
            # Simulate user sending chat message with malformed timestamp
            chat_message = {
                "type": "user_message",
                "payload": {
                    "content": "Analyze my business metrics for the last quarter",
                    "conversation_id": f"conv_{uuid.uuid4().hex[:8]}",
                    "expectation": "detailed_analysis"
                },
                "timestamp": "2025-09-08T16:50:01.000000",  # ISO string
                "user_id": user_context.user_id,
                "message_id": f"chat_{uuid.uuid4().hex[:8]}"
            }
            
            # Chat should be protected from timestamp validation failure
            with pytest.raises(Exception) as exc_info:
                await websocket_connection.send_message(chat_message)
            
            # Verify the protection mechanism works
            assert "timestamp" in str(exc_info.value).lower(), \
                "Chat should be protected by timestamp validation"
            
            # Test that valid timestamp allows chat to work
            chat_message["timestamp"] = time.time()
            
            try:
                response = await websocket_connection.send_message_and_wait_response(
                    message=chat_message,
                    timeout_seconds=15
                )
                
                # Chat functionality should work with valid timestamp
                assert response is not None
                chat_successful = True
            except Exception as e:
                pytest.fail(f"Chat with valid timestamp should work: {e}")
        
        finally:
            await websocket_connection.close()

    async def test_staging_environment_timestamp_compatibility(
        self, auth_helper, authenticated_user, websocket_helper, env
    ):
        """Test timestamp validation compatibility with staging environment."""
        user_context = authenticated_user
        
        websocket_connection = await websocket_helper.connect_authenticated(
            user_context=user_context,
            env=env
        )
        
        try:
            # Test various timestamp formats that might appear in staging
            staging_timestamp_formats = [
                {
                    "format": "iso_microseconds",
                    "value": "2025-09-08T16:50:01.447585",
                    "should_fail": True
                },
                {
                    "format": "iso_with_timezone", 
                    "value": "2025-09-08T16:50:01.447585+00:00",
                    "should_fail": True
                },
                {
                    "format": "iso_zulu",
                    "value": "2025-09-08T16:50:01.447585Z", 
                    "should_fail": True
                },
                {
                    "format": "unix_float",
                    "value": 1725811801.447585,
                    "should_fail": False
                },
                {
                    "format": "unix_int", 
                    "value": 1725811801,
                    "should_fail": False
                }
            ]
            
            for test_case in staging_timestamp_formats:
                message = {
                    "type": "heartbeat",
                    "payload": {"status": "alive"},
                    "timestamp": test_case["value"],
                    "user_id": user_context.user_id,
                    "message_id": f"staging_{test_case['format']}"
                }
                
                if test_case["should_fail"]:
                    with pytest.raises(Exception) as exc_info:
                        await websocket_connection.send_message(message)
                    
                    assert "timestamp" in str(exc_info.value).lower(), \
                        f"Format {test_case['format']} should fail validation"
                else:
                    # Valid timestamps should work
                    try:
                        await websocket_connection.send_message(message)
                    except Exception as e:
                        pytest.fail(f"Valid format {test_case['format']} should work: {e}")
        
        finally:
            await websocket_connection.close()


class TestWebSocketTimestampValidationPerformanceE2E:
    """E2E performance tests for timestamp validation."""

    @pytest.fixture
    async def authenticated_user(self):
        """Get authenticated user for performance testing."""
        return await get_authenticated_user_context(
            user_id="perf-timestamp-e2e-user",
            email="perf.timestamp@netra-staging.com"
        )

    async def test_high_volume_timestamp_validation_e2e(
        self, authenticated_user, websocket_helper, env
    ):
        """Test timestamp validation performance under high message volume."""
        user_context = authenticated_user
        
        websocket_connection = await websocket_helper.connect_authenticated(
            user_context=user_context,
            env=env
        )
        
        try:
            # Create 50 messages with valid timestamps
            messages = []
            base_time = time.time()
            
            for i in range(50):
                message = {
                    "type": "agent_progress",
                    "payload": {"step": i + 1, "total": 50, "status": f"processing_{i}"},
                    "timestamp": base_time + (i * 0.1),  # Valid float timestamps
                    "user_id": user_context.user_id,
                    "message_id": f"perf_msg_{i:03d}",
                    "thread_id": f"perf_thread_{uuid.uuid4().hex[:8]}"
                }
                messages.append(message)
            
            # Measure end-to-end processing time
            start_time = time.perf_counter()
            
            successful_messages = 0
            for message in messages:
                try:
                    await websocket_connection.send_message(message)
                    successful_messages += 1
                except Exception:
                    # Continue for performance measurement
                    pass
            
            end_time = time.perf_counter()
            processing_time_ms = (end_time - start_time) * 1000
            avg_time_per_message = processing_time_ms / len(messages)
            
            # Performance assertions
            assert avg_time_per_message < 10.0, \
                f"E2E timestamp validation too slow: {avg_time_per_message}ms/msg"
            assert successful_messages >= 40, \
                f"Too many E2E messages failed: {successful_messages}/50"
        
        finally:
            await websocket_connection.close()


if __name__ == "__main__":
    # Run the critical failing test
    pytest.main([
        __file__ + "::TestWebSocketTimestampValidationE2E::test_authenticated_websocket_timestamp_validation_failure",
        "-v", "--tb=short", "-s"
    ])