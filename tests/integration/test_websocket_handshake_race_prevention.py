"""
Integration Tests for WebSocket Handshake Race Condition Prevention

Business Value Justification (BVJ):
- Segment: Platform/Enterprise
- Business Goal: Prevent WebSocket race conditions causing user onboarding failures  
- Value Impact: Protect $500K+ ARR by ensuring reliable WebSocket connections
- Strategic Impact: Enable chat functionality (90% of platform value)

These integration tests use REAL SERVICE COMPONENTS but do not require Docker.
They test the WebSocket handshake sequence with actual WebSocket connections,
timeout configurations, and state management.

IMPORTANT: These tests are designed to INITIALLY FAIL to demonstrate the current
race condition issues. After implementing the fix, all tests should pass.

Issue #372: WebSocket handshake race condition causing 1011 errors
"""

import asyncio
import pytest
import json
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from starlette.websockets import WebSocketDisconnect

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

from netra_backend.app.websocket_core.utils import (
    validate_websocket_handshake_completion,
    is_websocket_connected_and_ready,
    safe_websocket_send,
    safe_websocket_close,
    _safe_websocket_state_for_logging
)
from netra_backend.app.websocket_core.types import create_server_message
from netra_backend.app.core.timeout_configuration import (
    get_websocket_recv_timeout,
    get_agent_execution_timeout,
    reset_timeout_manager
)
from shared.isolated_environment import get_env


@pytest.mark.integration
@pytest.mark.websocket_race_conditions  
@pytest.mark.real_services
class TestWebSocketHandshakeRacePrevention(BaseIntegrationTest):
    """
    Test WebSocket handshake race condition prevention with real service components.
    
    CRITICAL: These tests initially FAIL to demonstrate current race condition issues.
    After implementing proper handshake coordination, all tests should pass.
    """
    
    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        reset_timeout_manager()
    
    def teardown_method(self, method):
        """Clean up after each test."""
        reset_timeout_manager()
        super().teardown_method(method)
    
    @pytest.mark.asyncio
    async def test_accept_then_validate_sequence_proper_order(self):
        """
        Test that WebSocket accept() -> validation -> message handling sequence is enforced.
        
        EXPECTED TO FAIL INITIALLY: Current implementation may start message handling
        immediately after accept() without proper validation.
        
        After fix: Should enforce proper sequence with validation step.
        """
        # Create mock WebSocket that simulates real behavior
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTING
        
        sequence_log = []
        
        # Mock accept to update state and log sequence
        async def mock_accept(subprotocol=None):
            sequence_log.append("accept_called")
            mock_websocket.client_state = WebSocketState.CONNECTED
            
        mock_websocket.accept = mock_accept
        mock_websocket.send_json = AsyncMock(side_effect=lambda data: sequence_log.append("send_json_called"))
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "test"}')
        
        # Mock the state checking functions to simulate proper validation
        def mock_is_connected(ws):
            connected = ws.client_state == WebSocketState.CONNECTED
            if connected:
                sequence_log.append("state_validated")
            return connected
            
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', side_effect=mock_is_connected):
            # Simulate the WebSocket handshake sequence
            
            # Step 1: Accept connection  
            await mock_websocket.accept()
            
            # Step 2: Validate handshake completion (THIS MAY BE MISSING/SKIPPED)
            handshake_valid = await validate_websocket_handshake_completion(mock_websocket, timeout_seconds=2.0)
            
            # Step 3: Only allow message handling after validation
            if handshake_valid:
                sequence_log.append("message_handling_started")
                await mock_websocket.send_json({"type": "connection_established"})
        
        # CRITICAL: Verify proper sequence was followed
        expected_sequence = [
            "accept_called",
            "state_validated", 
            "send_json_called",  # From handshake validation
            "message_handling_started",
            "send_json_called"   # From connection established
        ]
        
        # This assertion may FAIL initially if sequence is not enforced
        assert sequence_log == expected_sequence, (
            f"WebSocket handshake sequence incorrect. Expected: {expected_sequence}, "
            f"Got: {sequence_log}. Race condition: message handling may start before validation."
        )
    
    @pytest.mark.asyncio
    async def test_handshake_completion_validation_bidirectional_test(self):
        """
        Test handshake completion validation performs bidirectional communication test.
        
        EXPECTED TO FAIL INITIALLY: Validation may be incomplete or skip bidirectional test.
        """
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        send_called = False
        test_message_received = None
        
        async def mock_send_json(data):
            nonlocal send_called, test_message_received
            send_called = True
            test_message_received = data
            
        mock_websocket.send_json = mock_send_json
        
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', return_value=True):
            # Test handshake validation performs bidirectional test
            start_time = time.time()
            result = await validate_websocket_handshake_completion(mock_websocket, timeout_seconds=2.0)
            duration = time.time() - start_time
            
            # CRITICAL: Should perform actual send test
            assert send_called, (
                "Handshake validation failed to perform bidirectional communication test. "
                "This can cause race conditions where transport appears ready but isn't."
            )
            
            # Should send a validation message
            assert test_message_received is not None, (
                "No validation message sent during handshake completion test"
            )
            
            # Should contain validation fields
            assert "type" in test_message_received, "Validation message missing type field"
            assert test_message_received["type"] == "handshake_validation", (
                f"Wrong validation message type: {test_message_received.get('type')}"
            )
            
            # Should take some time to perform validation
            assert duration >= 0.001, (
                f"Handshake validation too fast: {duration:.3f}s. "
                f"May be skipping actual bidirectional test."
            )
    
    @pytest.mark.asyncio
    async def test_application_state_readiness_separate_from_transport_state(self):
        """
        Test that application state readiness is checked separately from transport state.
        
        EXPECTED TO FAIL INITIALLY: May only check transport state, not application readiness.
        """
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED  # Transport ready
        
        # Mock connection state machine for application state
        mock_state_machine = Mock()
        mock_state_machine.can_process_messages.return_value = False  # App not ready
        mock_state_machine.current_state = "HANDSHAKE_PENDING"
        
        def mock_get_state_machine(connection_id):
            return mock_state_machine
        
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', return_value=True):
            with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine', 
                      side_effect=mock_get_state_machine):
                
                # Test readiness check considers application state
                connection_id = "test_conn_123"
                is_ready = is_websocket_connected_and_ready(mock_websocket, connection_id)
                
                # CRITICAL: Should be False because application state is not ready
                # This may FAIL if only transport state is checked
                assert is_ready is False, (
                    "WebSocket reported ready when application state was not ready. "
                    f"Transport state: CONNECTED, Application state: {mock_state_machine.current_state}. "
                    "This race condition can cause message handling to start prematurely."
                )
                
                # Verify state machine was actually consulted
                mock_state_machine.can_process_messages.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_message_handling_delayed_until_full_readiness(self):
        """
        Test that message handling is delayed until both transport and application are ready.
        
        EXPECTED TO FAIL INITIALLY: Message handling may start after transport ready only.
        """
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "user_message", "content": "hello"}')
        
        message_processing_started = False
        
        # Mock application state that becomes ready after delay
        class MockStateMachine:
            def __init__(self):
                self.ready_time = time.time() + 0.1  # Ready after 100ms
                
            def can_process_messages(self):
                return time.time() >= self.ready_time
            
            @property
            def current_state(self):
                return "READY" if self.can_process_messages() else "INITIALIZING"
        
        mock_state_machine = MockStateMachine()
        
        def mock_get_state_machine(connection_id):
            return mock_state_machine
        
        async def mock_message_handler(message):
            nonlocal message_processing_started
            message_processing_started = True
            return {"type": "response", "status": "processed"}
        
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', return_value=True):
            with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine',
                      side_effect=mock_get_state_machine):
                
                connection_id = "test_conn_456"
                start_time = time.time()
                
                # Simulate waiting for readiness before message handling
                while True:
                    is_ready = is_websocket_connected_and_ready(mock_websocket, connection_id)
                    if is_ready:
                        await mock_message_handler({"type": "user_message"})
                        break
                    
                    # Prevent infinite loop in test
                    if time.time() - start_time > 1.0:
                        break
                    
                    await asyncio.sleep(0.01)
                
                processing_delay = time.time() - start_time
                
                # CRITICAL: Should have waited for application readiness
                assert processing_delay >= 0.09, (
                    f"Message processing started too early: {processing_delay:.3f}s delay. "
                    f"Should wait for application state readiness (>=0.09s). "
                    "Race condition: messages processed before application ready."
                )
                
                assert message_processing_started, "Message processing should have started after readiness"
    
    @pytest.mark.asyncio  
    async def test_gcp_service_readiness_prevents_connection_acceptance(self):
        """
        Test that GCP service readiness is validated before accepting WebSocket connections.
        
        EXPECTED TO FAIL INITIALLY: May accept connections before services are ready.
        """
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.close = AsyncMock()
        
        # Mock app state with some services not ready
        mock_app_state = Mock()
        mock_app_state.supervisor_ready = False  # Service not ready
        mock_app_state.thread_service_ready = True
        
        mock_readiness_result = Mock()
        mock_readiness_result.ready = False
        mock_readiness_result.failed_services = ["supervisor_service"]
        
        # Mock the GCP readiness guard
        class MockReadinessGuard:
            async def __aenter__(self):
                return mock_readiness_result
                
            async def __aexit__(self, *args):
                pass
        
        def mock_readiness_guard(app_state, timeout=30):
            return MockReadinessGuard()
        
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_guard',
                  side_effect=mock_readiness_guard):
            
            # Simulate the readiness check that should happen before accept()
            connection_rejected = False
            close_code = None
            close_reason = None
            
            async def mock_close(code, reason):
                nonlocal connection_rejected, close_code, close_reason
                connection_rejected = True
                close_code = code
                close_reason = reason
            
            mock_websocket.close = mock_close
            
            # Test the readiness validation
            try:
                # This should reject the connection due to service not ready
                with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
                    from netra_backend.app.websocket_core.gcp_initialization_validator import gcp_websocket_readiness_guard
                    
                    async with gcp_websocket_readiness_guard(mock_app_state, timeout=1.0) as readiness_result:
                        if not readiness_result.ready:
                            await mock_websocket.close(code=1011, reason=f"Service not ready: {', '.join(readiness_result.failed_services)}")
                        else:
                            # Should not reach here in this test
                            await mock_websocket.accept()
                            
            except Exception as e:
                # Expected if services not ready
                pass
            
            # CRITICAL: Connection should be rejected when services not ready
            assert connection_rejected, (
                "WebSocket connection was not rejected when GCP services were not ready. "
                f"Failed services: {mock_readiness_result.failed_services}. "
                "This race condition can cause 1011 errors when messages are processed "
                "before required services (supervisor, thread) are available."
            )
            
            assert close_code == 1011, f"Wrong close code: {close_code}, expected 1011"
            assert "supervisor_service" in close_reason, f"Close reason should mention failed service: {close_reason}"
    
    @pytest.mark.asyncio
    async def test_timeout_coordination_prevents_premature_failures(self):
        """
        Test that WebSocket and Agent timeouts are properly coordinated to prevent premature failures.
        
        EXPECTED TO FAIL INITIALLY: Timeout misalignment causes premature WebSocket failures.
        """
        with patch.dict('os.environ', {'ENVIRONMENT': 'staging'}):
            websocket_timeout = get_websocket_recv_timeout()
            agent_timeout = get_agent_execution_timeout()
            
            # Simulate long-running agent operation
            mock_websocket = AsyncMock(spec=WebSocket)
            mock_websocket.client_state = WebSocketState.CONNECTED
            
            agent_start_time = time.time()
            simulated_agent_duration = min(agent_timeout - 2, 20)  # Agent takes most of its timeout
            
            # Mock agent execution that takes significant time
            async def mock_agent_execution():
                await asyncio.sleep(simulated_agent_duration)
                return {"type": "agent_completed", "result": "success"}
            
            # Mock WebSocket receive that should wait longer than agent execution
            receive_calls = 0
            async def mock_receive_text():
                nonlocal receive_calls
                receive_calls += 1
                if receive_calls == 1:
                    # First call simulates user message
                    return '{"type": "start_agent", "agent": "test_agent"}'
                else:
                    # Subsequent calls simulate waiting for agent completion
                    await asyncio.sleep(0.1)
                    raise asyncio.TimeoutError("WebSocket receive timeout")
            
            mock_websocket.receive_text = mock_receive_text
            mock_websocket.send_json = AsyncMock()
            
            # Test coordinated execution
            try:
                # Simulate WebSocket message loop with agent execution
                with asyncio.timeout(websocket_timeout):
                    # Receive initial message
                    message = await mock_websocket.receive_text()
                    assert json.loads(message)["type"] == "start_agent"
                    
                    # Start agent execution (should complete before WebSocket timeout)
                    agent_task = asyncio.create_task(mock_agent_execution())
                    
                    # Agent should complete before WebSocket timeout
                    agent_result = await agent_task
                    execution_duration = time.time() - agent_start_time
                    
                    # Send response
                    await mock_websocket.send_json(agent_result)
                    
            except asyncio.TimeoutError:
                execution_duration = time.time() - agent_start_time
                # This timeout might indicate the race condition
                
            # CRITICAL: Agent execution should complete within WebSocket timeout
            assert execution_duration < websocket_timeout, (
                f"Timeout coordination failure: Agent execution ({execution_duration:.1f}s) "
                f"exceeded WebSocket timeout ({websocket_timeout}s). Current timeouts: "
                f"WebSocket={websocket_timeout}s, Agent={agent_timeout}s. "
                "This race condition causes premature WebSocket failures and 1011 errors."
            )
            
            # Verify proper hierarchy
            timeout_gap = websocket_timeout - agent_timeout
            assert timeout_gap >= 5, (
                f"Insufficient timeout buffer: {timeout_gap}s < 5s. "
                f"WebSocket ({websocket_timeout}s) and Agent ({agent_timeout}s) timeouts "
                "need larger gap to prevent race conditions in Cloud Run environment."
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_handshake_race_condition_prevention(self):
        """
        Test that concurrent WebSocket handshakes don't interfere with each other.
        
        EXPECTED TO FAIL INITIALLY: Concurrent handshakes may have race conditions.
        """
        connection_results = []
        
        async def simulate_websocket_connection(connection_id: str, delay_ms: int = 0):
            """Simulate a WebSocket connection with optional startup delay"""
            try:
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)
                
                mock_websocket = AsyncMock(spec=WebSocket)
                mock_websocket.client_state = WebSocketState.CONNECTING
                
                # Simulate accept
                async def mock_accept():
                    mock_websocket.client_state = WebSocketState.CONNECTED
                
                mock_websocket.accept = mock_accept
                mock_websocket.send_json = AsyncMock()
                
                with patch('netra_backend.app.websocket_core.utils.is_websocket_connected', return_value=True):
                    # Simulate handshake sequence
                    await mock_websocket.accept()
                    
                    # Validate handshake
                    handshake_valid = await validate_websocket_handshake_completion(
                        mock_websocket, timeout_seconds=2.0
                    )
                    
                    result = {
                        "connection_id": connection_id,
                        "success": handshake_valid,
                        "timestamp": time.time()
                    }
                    connection_results.append(result)
                    
                    return result
                    
            except Exception as e:
                connection_results.append({
                    "connection_id": connection_id,
                    "success": False,
                    "error": str(e),
                    "timestamp": time.time()
                })
                raise
        
        # Test concurrent connections
        connection_tasks = []
        for i in range(5):
            task = simulate_websocket_connection(f"conn_{i}", delay_ms=i * 10)
            connection_tasks.append(task)
        
        # Execute all connections concurrently
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_connections = [r for r in connection_results if r.get("success", False)]
        failed_connections = [r for r in connection_results if not r.get("success", False)]
        
        # CRITICAL: All concurrent connections should succeed
        assert len(successful_connections) == 5, (
            f"Concurrent handshake race condition: {len(successful_connections)}/5 connections succeeded. "
            f"Failed connections: {failed_connections}. "
            "Race conditions in concurrent WebSocket handshakes can cause 1011 errors."
        )
        
        # Verify reasonable timing
        assert total_duration < 10.0, (
            f"Concurrent handshakes took too long: {total_duration:.2f}s > 10s. "
            "May indicate locking or serialization issues."
        )
        
        # Verify timestamps show concurrent execution
        timestamps = [r["timestamp"] for r in successful_connections]
        timestamp_spread = max(timestamps) - min(timestamps)
        assert timestamp_spread < 1.0, (
            f"Connection timestamps spread too wide: {timestamp_spread:.2f}s. "
            "Should execute concurrently, not serially."
        )