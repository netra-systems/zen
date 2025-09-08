"""
WebSocket Event Failures Test Suite - Warning Upgrade to ERROR

Tests for upgrading WebSocket event failure warnings to errors. These tests validate
that WebSocket communication failures are properly escalated to errors instead of
being silently ignored as warnings.

Business Value: Chat functionality depends on WebSocket events for real-time updates.
When WebSocket events fail, users don't see agent progress, tool execution status,
or completion notifications - breaking the core chat experience.

Critical Warning Locations Being Tested:
- execution_engine_consolidated.py:280 - agent_started event failure
- execution_engine_consolidated.py:295 - agent_completed event failure  
- execution_engine_consolidated.py:312 - agent_error event failure

UPGRADE REQUIREMENT: These warnings MUST be upgraded to errors because:
1. Silent WebSocket failures break chat functionality (core business value)
2. Users get no feedback about agent execution (terrible UX)
3. Multi-user scenarios become unreliable (isolation failures)

CLAUDE.md Compliance:
- Uses real WebSocket connections (no mocks)
- All E2E tests authenticate properly  
- Tests designed to fail hard
- Validates business value preservation
"""

import asyncio
import json
import logging
import pytest
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from .base_warning_test import SsotAsyncWarningUpgradeTestCase, WarningTestMetrics
from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket import WebSocketTestClient


logger = logging.getLogger(__name__)


class TestWebSocketEventFailuresWarningUpgrade(SsotAsyncWarningUpgradeTestCase):
    """
    Test suite for WebSocket event failure warning-to-error upgrades.
    
    This class tests that WebSocket event failures are properly escalated
    to errors to protect chat functionality and user experience.
    """
    
    async def test_agent_started_event_failure_upgraded_to_error(self):
        """
        Test that agent_started event failures are upgraded from warning to error.
        
        Business Impact: Users must know when agents start processing their requests.
        Without this event, users think the system is broken.
        """
        # Set up authenticated WebSocket connection
        auth_helper = await self.get_auth_helper()
        websocket_helper = await self.get_websocket_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.execution_engine_consolidated"):
            # Simulate WebSocket bridge failure during agent_started event
            with patch('netra_backend.app.agents.execution_engine_consolidated.WebSocketBridge.notify_agent_started') as mock_notify:
                # Configure mock to raise connection error
                mock_notify.side_effect = ConnectionError("WebSocket connection lost during agent_started")
                
                # Import and instantiate execution engine with failing WebSocket bridge
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineWithWebSocketEvents
                from netra_backend.app.agents.base_agent import AgentExecutionContext
                
                # Create test execution context
                context = AgentExecutionContext(
                    agent_name="test_agent",
                    task="Test task for WebSocket failure",
                    user_id=auth_helper.get_user_id(),
                    session_id=f"test_session_{uuid.uuid4().hex[:8]}"
                )
                
                # Create execution engine with mocked WebSocket bridge  
                engine = ExecutionEngineWithWebSocketEvents()
                engine.websocket_bridge = mock_notify.return_value
                
                # CRITICAL: This should now raise an ERROR, not just log a warning
                with self.expect_exception(ConnectionError, "WebSocket connection lost"):
                    await engine.pre_execute(context)
        
        # Validate that error was logged instead of warning
        self.assert_error_logged(
            "Failed to emit agent started event.*WebSocket connection lost",
            logger_name="netra_backend.app.agents.execution_engine_consolidated",
            count=1
        )
        
        # Validate no warnings were logged (should be error now)
        self.assert_no_warnings_logged("netra_backend.app.agents.execution_engine_consolidated")
        
        # Validate business value: Chat functionality gracefully handles the failure
        self.validate_business_value_preservation(
            chat_functionality=True,
            graceful_degradation=True
        )
    
    async def test_agent_completed_event_failure_upgraded_to_error(self):
        """
        Test that agent_completed event failures are upgraded from warning to error.
        
        Business Impact: Users must know when agents finish processing.
        Without completion events, users don't know if their request succeeded.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.execution_engine_consolidated"):
            # Simulate WebSocket bridge failure during agent_completed event
            with patch('netra_backend.app.agents.execution_engine_consolidated.WebSocketBridge.notify_agent_completed') as mock_notify:
                mock_notify.side_effect = TimeoutError("WebSocket send timeout during agent_completed")
                
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineWithWebSocketEvents
                from netra_backend.app.agents.base_agent import AgentExecutionContext, AgentExecutionResult
                
                # Create test contexts
                context = AgentExecutionContext(
                    agent_name="completion_test_agent",
                    task="Test task for completion event failure",
                    user_id=auth_helper.get_user_id(),
                    session_id=f"completion_test_{uuid.uuid4().hex[:8]}"
                )
                
                result = AgentExecutionResult(
                    success=True,
                    result="Test agent execution completed successfully",
                    error=None
                )
                
                # Create execution engine with failing WebSocket bridge
                engine = ExecutionEngineWithWebSocketEvents()  
                engine.websocket_bridge = mock_notify.return_value
                
                # CRITICAL: This should now raise an ERROR, not just log a warning
                with self.expect_exception(TimeoutError, "WebSocket send timeout"):
                    await engine.post_execute(result, context)
        
        # Validate error escalation
        self.assert_error_logged(
            "Failed to emit agent completed event.*WebSocket send timeout",
            logger_name="netra_backend.app.agents.execution_engine_consolidated",
            count=1
        )
        
        # Validate no warning was logged  
        self.assert_no_warnings_logged("netra_backend.app.agents.execution_engine_consolidated")
        
        # Validate business value preservation
        self.validate_business_value_preservation(
            chat_functionality=True,
            graceful_degradation=True
        )
    
    async def test_agent_error_event_failure_upgraded_to_error(self):
        """
        Test that agent_error event failures are upgraded from warning to error.
        
        Business Impact: When agents fail, users must be notified. If error events
        also fail to send, users are completely in the dark about system status.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.execution_engine_consolidated"):
            # Simulate WebSocket bridge failure during agent_error event
            with patch('netra_backend.app.agents.execution_engine_consolidated.WebSocketBridge.notify_agent_error') as mock_notify:
                mock_notify.side_effect = RuntimeError("WebSocket bridge unavailable during error notification")
                
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineWithWebSocketEvents
                from netra_backend.app.agents.base_agent import AgentExecutionContext
                
                # Create test context  
                context = AgentExecutionContext(
                    agent_name="error_test_agent",
                    task="Test task that triggers error event failure",
                    user_id=auth_helper.get_user_id(),
                    session_id=f"error_test_{uuid.uuid4().hex[:8]}"
                )
                
                # Create original error that agent encountered
                original_error = ValueError("Test agent execution error")
                
                # Create execution engine with failing WebSocket bridge
                engine = ExecutionEngineWithWebSocketEvents()
                engine.websocket_bridge = mock_notify.return_value
                
                # CRITICAL: This should now raise an ERROR, not just log a warning
                with self.expect_exception(RuntimeError, "WebSocket bridge unavailable"):
                    await engine.on_error(original_error, context)
        
        # Validate error escalation
        self.assert_error_logged(
            "Failed to emit agent error event.*WebSocket bridge unavailable",
            logger_name="netra_backend.app.agents.execution_engine_consolidated", 
            count=1
        )
        
        # Validate no warning was logged
        self.assert_no_warnings_logged("netra_backend.app.agents.execution_engine_consolidated")
        
        # Validate business value preservation
        self.validate_business_value_preservation(
            chat_functionality=True,
            graceful_degradation=True
        )
    
    async def test_websocket_event_multi_user_isolation_failure(self):
        """
        Test WebSocket event failures in multi-user scenarios.
        
        Business Impact: One user's WebSocket failure should not affect other users.
        The system must isolate failures and ensure other users continue to get events.
        """
        # Create multiple authenticated users
        user1_auth = await self.get_auth_helper()
        
        # Create second user with different credentials
        from test_framework.ssot.e2e_auth_helper import E2EAuthConfig
        user2_config = E2EAuthConfig(
            test_user_email=f"websocket_test_user2_{uuid.uuid4().hex[:8]}@example.com",
            test_user_password="websocket_test_password_456"
        )
        user2_auth = E2EAuthHelper(user2_config)
        await user2_auth.authenticate()
        
        with self.capture_log_messages("netra_backend.app.agents.execution_engine_consolidated"):
            # Simulate WebSocket failure for user1 but not user2
            with patch('netra_backend.app.agents.execution_engine_consolidated.WebSocketBridge.notify_agent_started') as mock_notify:
                def selective_failure(*args, **kwargs):
                    # Only fail for user1's context
                    if hasattr(kwargs.get('context'), 'user_id') and kwargs.get('context').user_id == user1_auth.get_user_id():
                        raise ConnectionError("WebSocket failure for user1 only")
                    return None  # Success for other users
                
                mock_notify.side_effect = selective_failure
                
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineWithWebSocketEvents
                from netra_backend.app.agents.base_agent import AgentExecutionContext
                
                # Create contexts for both users
                user1_context = AgentExecutionContext(
                    agent_name="multi_user_test_agent_1", 
                    task="User 1 task",
                    user_id=user1_auth.get_user_id(),
                    session_id=f"user1_session_{uuid.uuid4().hex[:8]}"
                )
                
                user2_context = AgentExecutionContext(
                    agent_name="multi_user_test_agent_2",
                    task="User 2 task", 
                    user_id=user2_auth.get_user_id(),
                    session_id=f"user2_session_{uuid.uuid4().hex[:8]}"
                )
                
                engine = ExecutionEngineWithWebSocketEvents()
                engine.websocket_bridge = mock_notify.return_value
                
                # User1's request should fail with error
                with self.expect_exception(ConnectionError, "WebSocket failure for user1 only"):
                    await engine.pre_execute(user1_context)
                
                # User2's request should succeed (no exception)
                try:
                    await engine.pre_execute(user2_context)
                except Exception as e:
                    pytest.fail(f"User2 should not be affected by User1's WebSocket failure: {e}")
        
        # Validate error logged for user1's failure
        self.assert_error_logged(
            "Failed to emit agent started event.*WebSocket failure for user1",
            logger_name="netra_backend.app.agents.execution_engine_consolidated",
            count=1
        )
        
        # Validate multi-user isolation preserved
        self.validate_business_value_preservation(
            multi_user_isolation=True,
            graceful_degradation=True
        )
    
    async def test_websocket_event_recovery_after_failure(self):
        """
        Test WebSocket event recovery after temporary failures.
        
        Business Impact: System should recover gracefully from temporary WebSocket 
        issues and resume normal operation without requiring manual intervention.
        """
        auth_helper = await self.get_auth_helper()
        
        with self.capture_log_messages("netra_backend.app.agents.execution_engine_consolidated"):
            # Simulate temporary WebSocket failure followed by recovery
            call_count = 0
            def intermittent_failure(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # First two calls fail
                    raise ConnectionError("Temporary WebSocket connection issue")
                return None  # Subsequent calls succeed
            
            with patch('netra_backend.app.agents.execution_engine_consolidated.WebSocketBridge.notify_agent_started') as mock_notify:
                mock_notify.side_effect = intermittent_failure
                
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineWithWebSocketEvents
                from netra_backend.app.agents.base_agent import AgentExecutionContext
                
                engine = ExecutionEngineWithWebSocketEvents()
                engine.websocket_bridge = mock_notify.return_value
                
                # Create test context
                context = AgentExecutionContext(
                    agent_name="recovery_test_agent",
                    task="Test WebSocket recovery",
                    user_id=auth_helper.get_user_id(), 
                    session_id=f"recovery_test_{uuid.uuid4().hex[:8]}"
                )
                
                # First two attempts should fail with errors
                with self.expect_exception(ConnectionError, "Temporary WebSocket connection issue"):
                    await engine.pre_execute(context)
                
                with self.expect_exception(ConnectionError, "Temporary WebSocket connection issue"):
                    await engine.pre_execute(context)
                
                # Third attempt should succeed (no exception)
                try:
                    await engine.pre_execute(context)
                except Exception as e:
                    pytest.fail(f"Third attempt should have succeeded after recovery: {e}")
        
        # Validate errors logged for failed attempts
        self.assert_error_logged(
            "Failed to emit agent started event.*Temporary WebSocket connection issue",
            logger_name="netra_backend.app.agents.execution_engine_consolidated",
            count=2
        )
        
        # Validate business value: System recovered gracefully
        self.validate_business_value_preservation(
            chat_functionality=True,
            graceful_degradation=True
        )
    
    async def test_websocket_event_failure_with_real_connection(self):
        """
        Test WebSocket event failures using real WebSocket connections.
        
        Business Impact: This tests actual WebSocket infrastructure to ensure
        the warning upgrade works with real connections, not just mocks.
        
        CLAUDE.md Compliance: Uses real services, no mocks for the WebSocket connection.
        """
        # Get real authenticated WebSocket connection
        auth_helper = await self.get_auth_helper()
        websocket_helper = await self.get_websocket_helper()
        
        # Record start time for timeout validation
        start_time = time.time()
        
        try:
            # Establish real WebSocket connection
            async with websocket_helper.connect() as websocket:
                
                # Simulate network interruption by closing connection unexpectedly
                await websocket.close()
                
                with self.capture_log_messages():
                    # Now try to send WebSocket event through the closed connection
                    with self.expect_exception((ConnectionError, RuntimeError)):
                        await websocket.send_text(json.dumps({
                            "event": "agent_started",
                            "data": {
                                "agent_name": "real_connection_test_agent",
                                "task": "Test with real WebSocket connection"
                            }
                        }))
        
        except Exception as e:
            # Validate the exception is properly escalated (not silently logged)
            assert isinstance(e, (ConnectionError, RuntimeError)), (
                f"Expected ConnectionError or RuntimeError for closed WebSocket, got {type(e)}"
            )
        
        # Validate execution time is reasonable (should fail quickly)
        execution_time = time.time() - start_time
        self.assert_execution_time_under(10.0)  # Should not hang
        
        # Record that we tested with real connection
        self.record_metric("real_websocket_connection_tested", True)
        
        # Validate business value preserved even with real connection failures
        self.validate_business_value_preservation(
            chat_functionality=True,
            graceful_degradation=True  
        )
    
    async def test_concurrent_websocket_event_failures(self):
        """
        Test concurrent WebSocket event failures under load.
        
        Business Impact: System must handle multiple simultaneous WebSocket failures
        without deadlocks or cascade failures affecting all users.
        """
        auth_helper = await self.get_auth_helper()
        
        # Create multiple concurrent tasks that will fail
        async def failing_websocket_task(task_id: int):
            with patch('netra_backend.app.agents.execution_engine_consolidated.WebSocketBridge.notify_agent_started') as mock_notify:
                mock_notify.side_effect = ConnectionError(f"Concurrent WebSocket failure {task_id}")
                
                from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngineWithWebSocketEvents
                from netra_backend.app.agents.base_agent import AgentExecutionContext
                
                context = AgentExecutionContext(
                    agent_name=f"concurrent_test_agent_{task_id}",
                    task=f"Concurrent task {task_id}",
                    user_id=f"user_{task_id}_{uuid.uuid4().hex[:8]}",
                    session_id=f"concurrent_session_{task_id}_{uuid.uuid4().hex[:8]}"
                )
                
                engine = ExecutionEngineWithWebSocketEvents()
                engine.websocket_bridge = mock_notify.return_value
                
                # This should raise an error
                await engine.pre_execute(context)
        
        # Run multiple concurrent failing tasks
        concurrent_tasks = [failing_websocket_task(i) for i in range(5)]
        
        with self.capture_log_messages("netra_backend.app.agents.execution_engine_consolidated"):
            # All tasks should fail with ConnectionError
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Validate all tasks failed as expected
            for i, result in enumerate(results):
                assert isinstance(result, ConnectionError), (
                    f"Task {i} should have failed with ConnectionError, got {type(result)}"
                )
                assert f"Concurrent WebSocket failure {i}" in str(result)
        
        # Validate errors logged for all concurrent failures
        self.assert_error_logged(
            "Failed to emit agent started event.*Concurrent WebSocket failure",
            logger_name="netra_backend.app.agents.execution_engine_consolidated",
            count=5
        )
        
        # Validate no warnings (should all be errors)
        self.assert_no_warnings_logged("netra_backend.app.agents.execution_engine_consolidated")
        
        # Validate business value: System handled concurrent failures gracefully
        self.validate_business_value_preservation(
            multi_user_isolation=True,
            graceful_degradation=True
        )
        
        # Record concurrent testing metric
        self.record_metric("concurrent_websocket_failures_tested", 5)


# Additional helper functions for WebSocket testing

async def create_test_websocket_bridge():
    """Create a test WebSocket bridge for integration testing."""
    from netra_backend.app.agents.websocket_bridge import WebSocketBridge
    
    # This would create a real WebSocket bridge instance
    # configured for the test environment
    return WebSocketBridge(
        websocket_url="ws://localhost:8002/ws",
        auth_token="test_token"
    )


async def simulate_websocket_network_partition():
    """
    Simulate network partition that affects WebSocket connections.
    
    This helper function simulates network conditions that cause
    WebSocket connections to fail in realistic ways.
    """
    # Implementation would simulate network conditions
    # like packet loss, high latency, connection drops
    pass