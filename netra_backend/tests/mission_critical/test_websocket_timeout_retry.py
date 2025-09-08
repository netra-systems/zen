"""
Mission Critical WebSocket Timeout and Retry Test Suite

Business Value Justification (BVJ):
- Segment: All tiers (core real-time communication infrastructure)
- Business Goal: Ensure WebSocket message delivery reliability with timeout/retry mechanisms
- Value Impact: Protects 90% of user value delivery through chat interface
- Strategic Impact: Critical for user engagement and prevents chat UI appearing broken

CRITICAL: This test suite validates the timeout/retry functionality for WebSocket send_to_thread method.
The feature being tested adds 5-second timeouts and exponential backoff retry to websocket.send_json() calls.

Test Coverage:
1. Normal message send completes within timeout
2. Message send times out and retries succeed on 2nd attempt  
3. Message send times out and retries succeed on 3rd attempt
4. All retry attempts fail - verify proper error handling
5. Exponential backoff timing (1s, 2s, 4s delays)
6. Concurrent sends with mixed success/failure
7. WebSocket disconnection during send
8. Large message handling with timeout
9. Recovery after timeout failures
10. Metric tracking for timeouts/retries

NOTE: These tests are designed to FAIL initially since the timeout/retry feature hasn't been implemented yet.
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from netra_backend.app.websocket_core import WebSocketManager, get_websocket_manager
from netra_backend.app.schemas.websocket_models import WebSocketMessage


class MockWebSocketWithTimeout:
    """Mock WebSocket that can simulate timeout scenarios."""
    
    def __init__(self, timeout_on_attempt: Optional[int] = None, 
                 disconnect_on_attempt: Optional[int] = None,
                 fail_after_attempts: Optional[int] = None):
        self.timeout_on_attempt = timeout_on_attempt
        self.disconnect_on_attempt = disconnect_on_attempt
        self.fail_after_attempts = fail_after_attempts
        self.call_count = 0
        self.state = WebSocketState.CONNECTED
        self.last_message = None
        self.send_times = []
        
    async def send_json(self, data: Dict[str, Any], timeout: Optional[float] = None):
        """Mock send_json that can simulate timeouts, disconnections, and failures."""
        self.call_count += 1
        self.last_message = data
        send_time = time.time()
        self.send_times.append(send_time)
        
        # Simulate disconnection
        if self.disconnect_on_attempt and self.call_count == self.disconnect_on_attempt:
            self.state = WebSocketState.DISCONNECTED
            raise WebSocketDisconnect(code=1006, reason="Connection lost during send")
        
        # Simulate timeout
        if self.timeout_on_attempt and self.call_count <= self.timeout_on_attempt:
            # Simulate timeout by raising asyncio.TimeoutError
            raise asyncio.TimeoutError("WebSocket send timed out")
        
        # Simulate permanent failure after X attempts
        if self.fail_after_attempts and self.call_count <= self.fail_after_attempts:
            raise Exception(f"Send failed on attempt {self.call_count}")
        
        # Simulate network delay for successful sends
        if timeout and timeout > 0:
            await asyncio.sleep(0.1)  # Small delay to simulate network latency
        
        return True


class WebSocketTimeoutRetryTestSuite:
    """Comprehensive test suite for WebSocket timeout and retry functionality."""

    def setup_method(self):
        """Setup test environment for each test."""
        self.manager = WebSocketManager()
        self.manager.connections = {}
        self.manager.user_connections = {}
        self.manager.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors_handled": 0,
            "broadcasts_sent": 0,
            "start_time": time.time(),
            # New metrics that should be tracked
            "timeout_retries": 0,
            "timeout_failures": 0,
            "send_timeouts": 0
        }
        
    def teardown_method(self):
        """Cleanup after each test."""
        if hasattr(self, 'manager'):
            self.manager.connections.clear()
            self.manager.user_connections.clear()
    
    def _create_mock_connection(self, thread_id: str, user_id: str = "test_user", 
                              websocket: Optional[MockWebSocketWithTimeout] = None) -> str:
        """Helper to create a mock connection."""
        connection_id = f"conn_{user_id}_{uuid.uuid4().hex[:8]}"
        websocket = websocket or MockWebSocketWithTimeout()
        
        self.manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": user_id,
            "websocket": websocket,
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "is_healthy": True,
            "client_ip": "127.0.0.1"
        }
        
        if user_id not in self.manager.user_connections:
            self.manager.user_connections[user_id] = set()
        self.manager.user_connections[user_id].add(connection_id)
        
        return connection_id


@pytest.mark.asyncio
class TestWebSocketTimeoutRetryBasic(WebSocketTimeoutRetryTestSuite):
    """Basic timeout and retry functionality tests."""
    
    async def test_normal_message_send_completes_within_timeout(self):
        """Test that normal message sends complete successfully without timeout."""
        # Setup
        thread_id = "thread_success_001"
        websocket = MockWebSocketWithTimeout()  # No timeout simulation
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "agent_update", "content": "Test message", "thread_id": thread_id}
        
        # Execute - this should pass WITHOUT timeout/retry implementation
        # But will FAIL once we add timeouts because send_json won't have timeout parameter
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            result = await self.manager.send_to_thread(thread_id, message)
        
        # Verify
        assert result is True, "Normal send should succeed"
        assert websocket.call_count == 1, "Should only call send_json once"
        assert websocket.last_message == message
        
        # This assertion will FAIL until timeout feature is implemented
        try:
            # Check if timeout parameter was passed (this should fail initially)
            assert hasattr(websocket, 'timeout_used'), "Timeout parameter should be used in send_json"
        except (AssertionError, AttributeError):
            pytest.fail("EXPECTED FAILURE: Timeout functionality not yet implemented")
    
    async def test_message_send_timeout_and_retry_second_attempt_success(self):
        """Test that a timed-out send retries and succeeds on second attempt."""
        # Setup - timeout on first attempt, succeed on second
        thread_id = "thread_retry_002"
        websocket = MockWebSocketWithTimeout(timeout_on_attempt=1)
        connection_id = self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "agent_update", "content": "Retry test message"}
        
        # Execute - this will FAIL until retry logic is implemented
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            start_time = time.time()
            result = await self.manager.send_to_thread(thread_id, message)
            end_time = time.time()
        
        # Verify retry behavior (will fail initially)
        try:
            assert result is True, "Should succeed after retry"
            assert websocket.call_count == 2, "Should retry once after timeout"
            
            # Check timing - should include retry delay
            assert end_time - start_time >= 1.0, "Should include 1s backoff delay"
            assert end_time - start_time < 3.0, "Should not take too long"
            
            # Check metrics tracking
            assert self.manager.connection_stats.get("timeout_retries", 0) == 1
            assert self.manager.connection_stats.get("send_timeouts", 0) == 1
        except (AssertionError, KeyError):
            pytest.fail("EXPECTED FAILURE: Retry logic not yet implemented")
    
    async def test_message_send_timeout_and_retry_third_attempt_success(self):
        """Test that a send succeeds on third attempt after two timeouts."""
        # Setup - timeout on first two attempts, succeed on third
        thread_id = "thread_retry_003"
        websocket = MockWebSocketWithTimeout(timeout_on_attempt=2)
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "agent_update", "content": "Triple retry test"}
        
        # Execute
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            start_time = time.time()
            result = await self.manager.send_to_thread(thread_id, message)
            end_time = time.time()
        
        # Verify (will fail initially)
        try:
            assert result is True, "Should succeed after 2 retries"
            assert websocket.call_count == 3, "Should make 3 attempts total"
            
            # Check exponential backoff timing: 1s + 2s = 3s minimum
            assert end_time - start_time >= 3.0, "Should include exponential backoff delays"
            assert end_time - start_time < 6.0, "Should not take excessively long"
            
            # Check metrics
            assert self.manager.connection_stats.get("timeout_retries", 0) == 2
            assert self.manager.connection_stats.get("send_timeouts", 0) == 2
        except (AssertionError, KeyError):
            pytest.fail("EXPECTED FAILURE: Exponential backoff retry logic not implemented")
    
    async def test_all_retry_attempts_fail_proper_error_handling(self):
        """Test proper error handling when all retry attempts fail."""
        # Setup - fail all 3 attempts
        thread_id = "thread_fail_004"
        websocket = MockWebSocketWithTimeout(fail_after_attempts=3)
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "agent_update", "content": "Failure test"}
        
        # Execute
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            result = await self.manager.send_to_thread(thread_id, message)
        
        # Verify failure handling (will fail initially)
        try:
            assert result is False, "Should return False after all retries fail"
            assert websocket.call_count == 3, "Should attempt maximum 3 times"
            
            # Check error metrics
            assert self.manager.connection_stats.get("timeout_failures", 0) == 1
            assert self.manager.connection_stats.get("errors_handled", 0) >= 1
        except (AssertionError, KeyError):
            pytest.fail("EXPECTED FAILURE: Error handling for max retry failures not implemented")


@pytest.mark.asyncio
class TestWebSocketTimeoutRetryTiming(WebSocketTimeoutRetryTestSuite):
    """Test exponential backoff timing and timeout values."""
    
    async def test_exponential_backoff_timing_precision(self):
        """Test that exponential backoff follows correct timing pattern (1s, 2s, 4s)."""
        # Setup
        thread_id = "thread_backoff_005"
        websocket = MockWebSocketWithTimeout(timeout_on_attempt=2)  # Fail first 2 attempts
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "timing_test", "content": "Backoff timing verification"}
        
        # Execute with precise timing
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            start_time = time.time()
            result = await self.manager.send_to_thread(thread_id, message)
            end_time = time.time()
        
        # Verify timing precision (will fail initially)
        try:
            total_time = end_time - start_time
            
            # Expected: initial attempt + 1s delay + retry + 2s delay + final success
            # Minimum: 3.0s, Maximum: 4.0s (with small buffer for execution time)
            assert total_time >= 3.0, f"Backoff timing too fast: {total_time}s"
            assert total_time <= 4.5, f"Backoff timing too slow: {total_time}s"
            
            # Check individual retry times
            retry_times = getattr(websocket, 'send_times', [])
            if len(retry_times) >= 3:
                # First to second retry should be ~1s
                delay_1 = retry_times[1] - retry_times[0]
                assert 0.9 <= delay_1 <= 1.3, f"First retry delay incorrect: {delay_1}s"
                
                # Second to third retry should be ~2s  
                delay_2 = retry_times[2] - retry_times[1]
                assert 1.9 <= delay_2 <= 2.3, f"Second retry delay incorrect: {delay_2}s"
        except (AssertionError, AttributeError):
            pytest.fail("EXPECTED FAILURE: Exponential backoff timing not implemented")
    
    async def test_timeout_value_configuration(self):
        """Test that 5-second timeout is properly configured."""
        # This test checks that the timeout value is correctly set
        thread_id = "thread_timeout_006"
        websocket = MockWebSocketWithTimeout()
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "timeout_config_test"}
        
        # Mock the timeout to capture what timeout value is used
        original_send_json = websocket.send_json
        timeout_used = None
        
        async def capture_timeout_send_json(data, timeout=None):
            nonlocal timeout_used
            timeout_used = timeout
            return await original_send_json(data, timeout)
        
        websocket.send_json = capture_timeout_send_json
        
        # Execute
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            await self.manager.send_to_thread(thread_id, message)
        
        # Verify timeout configuration (will fail initially)
        try:
            assert timeout_used is not None, "Timeout parameter should be passed to send_json"
            assert timeout_used == 5.0, f"Timeout should be 5 seconds, got {timeout_used}"
        except AssertionError:
            pytest.fail("EXPECTED FAILURE: 5-second timeout not implemented")


@pytest.mark.asyncio
class TestWebSocketTimeoutRetryConcurrency(WebSocketTimeoutRetryTestSuite):
    """Test concurrent timeout/retry scenarios."""
    
    async def test_concurrent_sends_mixed_success_failure(self):
        """Test multiple concurrent sends with mixed timeout/success patterns."""
        # Setup multiple connections with different behavior
        connections_data = [
            ("thread_concurrent_1", MockWebSocketWithTimeout()),  # Success
            ("thread_concurrent_2", MockWebSocketWithTimeout(timeout_on_attempt=1)),  # Retry once
            ("thread_concurrent_3", MockWebSocketWithTimeout(fail_after_attempts=3)),  # Fail all
            ("thread_concurrent_4", MockWebSocketWithTimeout(timeout_on_attempt=2)),  # Retry twice
            ("thread_concurrent_5", MockWebSocketWithTimeout()),  # Success
        ]
        
        connection_ids = []
        websockets_list = []
        for thread_id, websocket in connections_data:
            conn_id = self._create_mock_connection(thread_id, websocket=websocket)
            connection_ids.append(conn_id)
            websockets_list.append(websocket)
        
        messages = [
            {"type": "concurrent_test", "content": f"Message {i+1}"} 
            for i in range(len(connections_data))
        ]
        
        # Execute concurrent sends
        with patch.object(self.manager, '_serialize_message_safely', side_effect=lambda x: x):
            tasks = [
                self.manager.send_to_thread(thread_id, msg) 
                for (thread_id, _), msg in zip(connections_data, messages)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
        
        # Verify concurrent behavior (will fail initially)
        try:
            # Check individual results
            assert results[0] is True, "First connection should succeed immediately"
            assert results[1] is True, "Second connection should succeed after retry"
            assert results[2] is False, "Third connection should fail after max retries"
            assert results[3] is True, "Fourth connection should succeed after 2 retries"
            assert results[4] is True, "Fifth connection should succeed immediately"
            
            # Check call counts
            assert websockets_list[0].call_count == 1, "Success connection: 1 call"
            assert websockets_list[1].call_count == 2, "Single retry connection: 2 calls"
            assert websockets_list[2].call_count == 3, "Failed connection: 3 calls (max)"
            assert websockets_list[3].call_count == 3, "Double retry connection: 3 calls"
            assert websockets_list[4].call_count == 1, "Success connection: 1 call"
            
            # Concurrent execution should not take much longer than longest retry
            # Longest is thread_concurrent_4 with ~3s of backoff
            assert end_time - start_time <= 5.0, "Concurrent execution should be efficient"
            
            # Check aggregated metrics  
            expected_retries = 5  # 0 + 1 + 2 + 2 + 0 = 5 total retries
            expected_failures = 1
            assert self.manager.connection_stats.get("timeout_retries", 0) == expected_retries
            assert self.manager.connection_stats.get("timeout_failures", 0) == expected_failures
        except (AssertionError, KeyError):
            pytest.fail("EXPECTED FAILURE: Concurrent retry handling not implemented")
    
    async def test_websocket_disconnection_during_send(self):
        """Test handling of WebSocket disconnection during message send."""
        # Setup - disconnect on first attempt
        thread_id = "thread_disconnect_007"
        websocket = MockWebSocketWithTimeout(disconnect_on_attempt=1)
        connection_id = self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "disconnect_test", "content": "Test disconnection handling"}
        
        # Execute
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            result = await self.manager.send_to_thread(thread_id, message)
        
        # Verify disconnection handling (will fail initially)
        try:
            assert result is False, "Should return False when WebSocket disconnects"
            
            # Connection should be cleaned up
            assert connection_id not in self.manager.connections, "Connection should be cleaned up"
            
            # Metrics should reflect the disconnection
            assert self.manager.connection_stats.get("errors_handled", 0) >= 1
        except (AssertionError, KeyError):
            pytest.fail("EXPECTED FAILURE: Disconnection handling during retry not implemented")


@pytest.mark.asyncio  
class TestWebSocketTimeoutRetryEdgeCases(WebSocketTimeoutRetryTestSuite):
    """Test edge cases and error scenarios."""
    
    async def test_large_message_handling_with_timeout(self):
        """Test timeout/retry behavior with large messages."""
        # Setup
        thread_id = "thread_large_008"
        websocket = MockWebSocketWithTimeout(timeout_on_attempt=1)  # Timeout once, then succeed
        self._create_mock_connection(thread_id, websocket=websocket)
        
        # Create large message (should still be handled properly)
        large_message = {
            "type": "large_message_test",
            "content": "x" * 10000,  # 10KB message
            "data": list(range(1000)),  # Additional bulk data
            "metadata": {"size": "large", "test": True}
        }
        
        # Execute
        with patch.object(self.manager, '_serialize_message_safely', return_value=large_message):
            start_time = time.time()
            result = await self.manager.send_to_thread(thread_id, large_message)
            end_time = time.time()
        
        # Verify large message handling (will fail initially)
        try:
            assert result is True, "Large message should succeed after retry"
            assert websocket.call_count == 2, "Should retry once"
            assert websocket.last_message == large_message, "Full message should be sent"
            
            # Should include retry delay
            assert end_time - start_time >= 1.0, "Should include retry backoff"
        except AssertionError:
            pytest.fail("EXPECTED FAILURE: Large message timeout/retry handling not implemented")
    
    async def test_recovery_after_timeout_failures(self):
        """Test that connections can recover after experiencing timeout failures."""
        # Setup - connection that fails initially but can recover
        thread_id = "thread_recovery_009"
        websocket = MockWebSocketWithTimeout(timeout_on_attempt=1)
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message1 = {"type": "recovery_test", "content": "First message - should timeout then succeed"}
        message2 = {"type": "recovery_test", "content": "Second message - should succeed immediately"}
        
        # Execute first message (with timeout and retry)
        with patch.object(self.manager, '_serialize_message_safely', return_value=message1):
            result1 = await self.manager.send_to_thread(thread_id, message1)
        
        # Reset websocket to not timeout (simulate recovery)
        websocket.timeout_on_attempt = None
        
        # Execute second message (should succeed immediately)
        with patch.object(self.manager, '_serialize_message_safely', return_value=message2):
            result2 = await self.manager.send_to_thread(thread_id, message2)
        
        # Verify recovery (will fail initially)
        try:
            assert result1 is True, "First message should succeed after retry"
            assert result2 is True, "Second message should succeed immediately"
            
            # Total calls: 2 for first message (timeout + retry), 1 for second
            assert websocket.call_count == 3, "Should handle recovery correctly"
            
            # Connection should remain healthy
            conn = self.manager.connections[list(self.manager.connections.keys())[0]]
            assert conn["is_healthy"] is True, "Connection should remain healthy after recovery"
        except (AssertionError, KeyError, IndexError):
            pytest.fail("EXPECTED FAILURE: Recovery after timeout failures not implemented")
    
    async def test_metric_tracking_comprehensive(self):
        """Test comprehensive metric tracking for timeout/retry operations."""
        # Setup multiple scenarios to generate various metrics
        test_scenarios = [
            ("success_thread", MockWebSocketWithTimeout()),  # Immediate success
            ("retry_once_thread", MockWebSocketWithTimeout(timeout_on_attempt=1)),  # 1 retry
            ("retry_twice_thread", MockWebSocketWithTimeout(timeout_on_attempt=2)),  # 2 retries
            ("fail_thread", MockWebSocketWithTimeout(fail_after_attempts=3)),  # Total failure
            ("disconnect_thread", MockWebSocketWithTimeout(disconnect_on_attempt=1)),  # Disconnection
        ]
        
        # Create connections
        for thread_id, websocket in test_scenarios:
            self._create_mock_connection(thread_id, websocket=websocket)
        
        # Execute all scenarios
        messages = [{"type": "metric_test", "content": f"Message for {thread_id}"} 
                   for thread_id, _ in test_scenarios]
        
        with patch.object(self.manager, '_serialize_message_safely', side_effect=lambda x: x):
            for (thread_id, _), message in zip(test_scenarios, messages):
                await self.manager.send_to_thread(thread_id, message)
        
        # Verify comprehensive metrics (will fail initially)
        try:
            stats = self.manager.connection_stats
            
            # Expected metrics based on scenarios:
            # - retry_once: 1 retry, 1 timeout
            # - retry_twice: 2 retries, 2 timeouts  
            # - fail_thread: 2 retries, 3 timeouts, 1 failure
            # - disconnect: 0 retries, 0 timeouts, 1 error
            
            assert stats.get("timeout_retries", 0) == 3, "Should track total retry attempts"
            assert stats.get("send_timeouts", 0) >= 3, "Should track timeout occurrences" 
            assert stats.get("timeout_failures", 0) == 1, "Should track final failures"
            assert stats.get("errors_handled", 0) >= 2, "Should track various errors"
            
            # Verify successful sends are also counted
            assert stats.get("messages_sent", 0) >= 3, "Should count successful sends"
        except (AssertionError, KeyError):
            pytest.fail("EXPECTED FAILURE: Comprehensive timeout/retry metrics not implemented")


@pytest.mark.asyncio
class TestWebSocketTimeoutRetryIntegration(WebSocketTimeoutRetryTestSuite):
    """Integration tests with real WebSocket manager behavior."""
    
    async def test_integration_with_actual_websocket_manager(self):
        """Test timeout/retry integration with actual WebSocket manager methods."""
        # Use actual WebSocket manager instance
        actual_manager = get_websocket_manager()
        
        # Setup mock WebSocket that supports timeout parameter
        mock_websocket = MockWebSocketWithTimeout(timeout_on_attempt=1)
        
        # Patch the manager's connections to use our mock
        thread_id = "integration_thread_010"
        connection_id = f"conn_integration_{uuid.uuid4().hex[:8]}"
        
        actual_manager.connections[connection_id] = {
            "connection_id": connection_id,
            "user_id": "integration_user",
            "websocket": mock_websocket,
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "is_healthy": True,
        }
        
        message = {"type": "integration_test", "content": "Integration test message"}
        
        # Execute using actual manager
        try:
            result = await actual_manager.send_to_thread(thread_id, message)
            
            # Verify integration behavior (will fail initially)
            assert result is True, "Integration should succeed after implementing timeout/retry"
            assert mock_websocket.call_count == 2, "Should retry once on timeout"
            
            # Cleanup
            del actual_manager.connections[connection_id]
            
        except Exception as e:
            pytest.fail(f"EXPECTED FAILURE: Integration with timeout/retry not implemented: {e}")
    
    async def test_backward_compatibility_existing_behavior(self):
        """Test that existing behavior is preserved when no timeouts occur."""
        # This test ensures we don't break existing functionality
        thread_id = "compat_thread_011"
        websocket = MockWebSocketWithTimeout()  # No timeouts or failures
        self._create_mock_connection(thread_id, websocket=websocket)
        
        message = {"type": "compatibility_test", "content": "Backward compatibility verification"}
        
        # Execute - should behave exactly as before when no timeouts occur
        with patch.object(self.manager, '_serialize_message_safely', return_value=message):
            start_time = time.time()
            result = await self.manager.send_to_thread(thread_id, message)
            end_time = time.time()
        
        # Verify backward compatibility
        assert result is True, "Should maintain existing success behavior"
        assert websocket.call_count == 1, "Should only call once when no timeout"
        assert websocket.last_message == message, "Should send correct message"
        
        # Should be fast (no retry delays)
        assert end_time - start_time < 0.5, "Should be fast when no retries needed"
        
        # Should not affect normal connection lifecycle
        conn = self.manager.connections[list(self.manager.connections.keys())[0]]
        assert conn["message_count"] == 1, "Should increment message count"
        assert conn["is_healthy"] is True, "Should maintain healthy status"


# Test configuration and markers
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.mission_critical,
    pytest.mark.timeout_retry
]

if __name__ == "__main__":
    # Run specific test groups
    import sys
    
    if "--fast" in sys.argv:
        # Run only basic tests for fast feedback
        pytest.main([__file__ + "::TestWebSocketTimeoutRetryBasic", "-v"])
    elif "--timing" in sys.argv:  
        # Run timing-specific tests
        pytest.main([__file__ + "::TestWebSocketTimeoutRetryTiming", "-v"])
    elif "--concurrency" in sys.argv:
        # Run concurrency tests
        pytest.main([__file__ + "::TestWebSocketTimeoutRetryConcurrency", "-v"])
    else:
        # Run all tests
        pytest.main([__file__, "-v", "--tb=short"])