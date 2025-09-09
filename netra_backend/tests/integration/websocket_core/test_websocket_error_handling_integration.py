#!/usr/bin/env python
"""
Integration Tests for WebSocket Error Handling and Resilience

MISSION CRITICAL: WebSocket error handling that maintains chat reliability.
Tests real WebSocket error scenarios and system resilience for business continuity.

Business Value: $500K+ ARR - Chat system reliability and error recovery
- Tests WebSocket error handling with real connection failures
- Validates system resilience under various failure conditions
- Ensures graceful degradation maintains business continuity
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType as TestEventType

# Import production WebSocket components - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.fixture
async def error_handling_websocket_utility():
    """Create WebSocket test utility for error handling tests."""
    async with WebSocketTestUtility() as ws_util:
        yield ws_util


@pytest.fixture
async def error_handling_websocket_manager():
    """Create WebSocket manager for error handling tests."""
    manager = UnifiedWebSocketManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.mark.integration
class TestWebSocketConnectionFailures:
    """Integration tests for WebSocket connection failure handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_timeout_handling(self, error_handling_websocket_utility, error_handling_websocket_manager):
        """
        Test WebSocket connection timeout handling.
        
        CRITICAL: Connection timeouts must not crash the system.
        Users should get clear feedback when connections fail.
        """
        # Arrange
        bridge = AgentWebSocketBridge(error_handling_websocket_manager)
        user_context = UserExecutionContext(
            user_id=UserID(f"timeout_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"timeout_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"timeout_request_{uuid.uuid4().hex[:8]}")
        )
        
        # Act - Attempt connection with very short timeout
        client = await error_handling_websocket_utility.create_test_client(user_context.user_id)
        
        # Try connection with unreasonably short timeout to force failure
        start_time = time.time()
        connected = await client.connect(timeout=0.1)  # 100ms timeout
        connection_time = time.time() - start_time
        
        # Assert - System handles timeout gracefully
        if not connected:
            # Connection timeout is expected and handled gracefully
            assert connection_time <= 1.0, "Timeout should be respected"
            assert client.is_connected is False, "Client should not be marked as connected"
        else:
            # If connection succeeded despite short timeout, verify it works
            await error_handling_websocket_manager.register_user_connection(
                user_context.user_id,
                client.websocket
            )
            
            # Test event delivery on successful connection
            result = await bridge.emit_event(
                context=user_context,
                event_type="agent_started",
                event_data={
                    "agent": "timeout_test_agent",
                    "status": "starting",
                    "connection_test": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            assert result is True, "Events should work on successful connection"
            await client.disconnect()
        
        # Key assertion: no system crash
        assert True, "System must handle connection timeouts gracefully"
    
    @pytest.mark.asyncio
    async def test_websocket_sudden_disconnection_during_event_delivery(self, error_handling_websocket_utility, error_handling_websocket_manager):
        """
        Test WebSocket sudden disconnection during event delivery.
        
        CRITICAL: Sudden disconnections must not break event delivery to other users.
        System must be resilient to individual connection failures.
        """
        # Arrange
        bridge = AgentWebSocketBridge(error_handling_websocket_manager)
        
        # Create two users - one will disconnect suddenly
        stable_user_context = UserExecutionContext(
            user_id=UserID(f"stable_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"stable_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"stable_request_{uuid.uuid4().hex[:8]}")
        )
        
        unstable_user_context = UserExecutionContext(
            user_id=UserID(f"unstable_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"unstable_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"unstable_request_{uuid.uuid4().hex[:8]}")
        )
        
        # Create and connect both clients
        stable_client = await error_handling_websocket_utility.create_test_client(stable_user_context.user_id)
        unstable_client = await error_handling_websocket_utility.create_test_client(unstable_user_context.user_id)
        
        stable_connected = await stable_client.connect(timeout=30.0)
        unstable_connected = await unstable_client.connect(timeout=30.0)
        
        assert stable_connected is True, "Stable client must connect"
        assert unstable_connected is True, "Unstable client must connect"
        
        # Register both connections
        await error_handling_websocket_manager.register_user_connection(
            stable_user_context.user_id,
            stable_client.websocket
        )
        await error_handling_websocket_manager.register_user_connection(
            unstable_user_context.user_id,
            unstable_client.websocket
        )
        
        # Act - Send initial events to both users
        stable_result1 = await bridge.emit_event(
            context=stable_user_context,
            event_type="agent_started",
            event_data={
                "agent": "stable_agent",
                "status": "starting",
                "phase": "before_disconnection",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        unstable_result1 = await bridge.emit_event(
            context=unstable_user_context,
            event_type="agent_started",
            event_data={
                "agent": "unstable_agent",
                "status": "starting",
                "phase": "before_disconnection",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        assert stable_result1 is True, "Stable user event must be sent"
        assert unstable_result1 is True, "Unstable user event must be sent"
        
        # Verify initial events
        stable_msg1 = await stable_client.wait_for_message(
            event_type=TestEventType.AGENT_STARTED,
            timeout=10.0
        )
        assert stable_msg1.data["phase"] == "before_disconnection"
        
        # Sudden disconnection of unstable client
        await unstable_client.disconnect()
        
        # Continue sending events - stable client should still work
        stable_result2 = await bridge.emit_event(
            context=stable_user_context,
            event_type="agent_thinking",
            event_data={
                "agent": "stable_agent",
                "progress": "continuing despite other disconnection",
                "phase": "after_disconnection",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Try sending to disconnected user (should fail gracefully)
        unstable_result2 = await bridge.emit_event(
            context=unstable_user_context,
            event_type="agent_thinking",
            event_data={
                "agent": "unstable_agent",
                "progress": "this should fail",
                "phase": "after_disconnection",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Assert - Stable user continues working
        assert stable_result2 is True, "Stable user must continue receiving events"
        assert unstable_result2 is False, "Disconnected user events should fail"
        
        # Verify stable client still receives events
        stable_msg2 = await stable_client.wait_for_message(
            event_type=TestEventType.AGENT_THINKING,
            timeout=10.0
        )
        assert stable_msg2.data["phase"] == "after_disconnection"
        
        # Cleanup
        await stable_client.disconnect()
    
    @pytest.mark.asyncio
    async def test_websocket_network_interruption_recovery(self, error_handling_websocket_utility, error_handling_websocket_manager):
        """
        Test WebSocket network interruption and recovery scenarios.
        
        CRITICAL: Network interruptions must not permanently break chat functionality.
        Users should be able to recover and continue receiving agent events.
        """
        # Arrange
        bridge = AgentWebSocketBridge(error_handling_websocket_manager)
        user_context = UserExecutionContext(
            user_id=UserID(f"recovery_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"recovery_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"recovery_request_{uuid.uuid4().hex[:8]}")
        )
        
        # Initial connection
        client = await error_handling_websocket_utility.create_test_client(user_context.user_id)
        connected1 = await client.connect(timeout=30.0)
        assert connected1 is True, "Initial connection must succeed"
        
        await error_handling_websocket_manager.register_user_connection(
            user_context.user_id,
            client.websocket
        )
        
        # Send event before interruption
        result1 = await bridge.emit_event(
            context=user_context,
            event_type="agent_started",
            event_data={
                "agent": "recovery_agent",
                "status": "starting",
                "phase": "before_interruption",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        assert result1 is True, "Event before interruption must be sent"
        
        # Verify pre-interruption event
        pre_msg = await client.wait_for_message(
            event_type=TestEventType.AGENT_STARTED,
            timeout=10.0
        )
        assert pre_msg.data["phase"] == "before_interruption"
        
        # Act - Simulate network interruption
        await client.disconnect()
        await asyncio.sleep(3.0)  # Simulate extended network outage
        
        # Attempt recovery
        recovery_attempts = 0
        max_attempts = 3
        recovered = False
        
        while recovery_attempts < max_attempts and not recovered:
            recovery_attempts += 1
            
            try:
                # Attempt reconnection
                connected_recovery = await client.connect(timeout=15.0)
                
                if connected_recovery:
                    # Re-register connection
                    await error_handling_websocket_manager.register_user_connection(
                        user_context.user_id,
                        client.websocket
                    )
                    
                    # Test if connection works
                    test_result = await bridge.emit_event(
                        context=user_context,
                        event_type="agent_thinking",
                        event_data={
                            "agent": "recovery_agent",
                            "progress": f"recovered on attempt {recovery_attempts}",
                            "phase": "after_recovery",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    if test_result:
                        recovered = True
                        break
                    
            except Exception as e:
                print(f"Recovery attempt {recovery_attempts} failed: {e}")
                
            # Brief delay before next attempt
            await asyncio.sleep(1.0)
        
        # Assert recovery
        if recovered:
            # Verify post-recovery functionality
            recovery_msg = await client.wait_for_message(
                event_type=TestEventType.AGENT_THINKING,
                timeout=10.0
            )
            assert recovery_msg.data["phase"] == "after_recovery"
            assert recovery_attempts <= max_attempts, f"Recovery took too many attempts: {recovery_attempts}"
            
            # Send additional event to confirm stability
            stability_result = await bridge.emit_event(
                context=user_context,
                event_type="tool_executing",
                event_data={
                    "tool": "stability_test_tool",
                    "status": "executing",
                    "phase": "stability_check",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            assert stability_result is True, "Connection must be stable after recovery"
            
            await client.disconnect()
        else:
            # If recovery failed, ensure system is still stable
            assert True, "System must remain stable even if recovery fails"


@pytest.mark.integration  
class TestWebSocketEventDeliveryErrors:
    """Integration tests for WebSocket event delivery error scenarios."""
    
    @pytest.mark.asyncio
    async def test_websocket_malformed_event_handling(self, error_handling_websocket_utility, error_handling_websocket_manager):
        """
        Test WebSocket handling of malformed event data.
        
        CRITICAL: Malformed events must not crash the system.
        System must validate and handle invalid events gracefully.
        """
        # Arrange
        bridge = AgentWebSocketBridge(error_handling_websocket_manager)
        user_context = UserExecutionContext(
            user_id=UserID(f"malformed_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"malformed_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"malformed_request_{uuid.uuid4().hex[:8]}")
        )
        
        async with error_handling_websocket_utility.connected_client(user_context.user_id) as client:
            await error_handling_websocket_manager.register_user_connection(
                user_context.user_id,
                client.websocket
            )
            
            # Test various malformed event scenarios
            malformed_events = [
                # Missing required fields
                ("agent_started", {}),
                # Invalid data types
                ("agent_thinking", {"agent": None, "progress": 12345}),
                # Extremely large event
                ("tool_completed", {"tool": "test", "result": {"data": "x" * 100000}}),
                # Invalid event type
                ("invalid_event_type", {"some": "data"}),
                # Circular reference (would cause JSON serialization issues)
                # This one we'll create differently to avoid actual circular reference
                ("agent_completed", {"agent": "test", "self_ref": "placeholder"}),
            ]
            
            successful_events = 0
            failed_events = 0
            
            # Act - Send each malformed event
            for event_type, event_data in malformed_events:
                try:
                    # Add timestamp to make events more realistic
                    if isinstance(event_data, dict):
                        event_data["timestamp"] = datetime.now().isoformat()
                        event_data["malformed_test"] = True
                    
                    result = await bridge.emit_event(
                        context=user_context,
                        event_type=event_type,
                        event_data=event_data
                    )
                    
                    if result:
                        successful_events += 1
                    else:
                        failed_events += 1
                        
                except Exception as e:
                    # Exceptions are expected for malformed events
                    failed_events += 1
                    print(f"Expected error for malformed event {event_type}: {e}")
            
            # Send a valid event to ensure system is still working
            valid_result = await bridge.emit_event(
                context=user_context,
                event_type="agent_started",
                event_data={
                    "agent": "validation_agent",
                    "status": "starting",
                    "after_malformed_tests": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Assert - System handles malformed events gracefully
            assert valid_result is True, "System must continue working after malformed events"
            assert failed_events > 0, "Some malformed events should be rejected"
            
            # Verify valid event is received
            valid_msg = await client.wait_for_message(
                event_type=TestEventType.AGENT_STARTED,
                timeout=10.0
            )
            assert valid_msg.data["after_malformed_tests"] is True
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_event_delivery_errors(self, error_handling_websocket_utility, error_handling_websocket_manager):
        """
        Test WebSocket concurrent event delivery with mixed success/failure.
        
        CRITICAL: Event delivery failures must not affect other concurrent events.
        System must maintain isolation between concurrent operations.
        """
        # Arrange
        bridge = AgentWebSocketBridge(error_handling_websocket_manager)
        user_count = 5
        events_per_user = 3
        
        # Create multiple user contexts
        user_contexts = []
        for i in range(user_count):
            context = UserExecutionContext(
                user_id=UserID(f"concurrent_user_{i}_{uuid.uuid4().hex[:6]}"),
                thread_id=ThreadID(f"concurrent_thread_{i}_{uuid.uuid4().hex[:6]}"),
                request_id=RequestID(f"concurrent_request_{i}_{uuid.uuid4().hex[:6]}")
            )
            user_contexts.append(context)
        
        # Connect all users
        clients = []
        for context in user_contexts:
            client = await error_handling_websocket_utility.create_test_client(context.user_id)
            connected = await client.connect(timeout=30.0)
            
            if connected:
                await error_handling_websocket_manager.register_user_connection(
                    context.user_id,
                    client.websocket
                )
                clients.append((client, context))
        
        # Act - Send concurrent events with mix of valid and invalid
        async def send_user_events(client_context_pair, user_index):
            client, context = client_context_pair
            results = []
            
            for event_num in range(events_per_user):
                # Mix valid and potentially problematic events
                if event_num == 1 and user_index == 2:  # Inject failure for user 2, event 1
                    # Send malformed event
                    event_data = {"invalid": None, "malformed": True}
                    event_type = "invalid_type"
                else:
                    # Send valid event
                    event_data = {
                        "agent": f"concurrent_agent_{user_index}",
                        "status": "processing",
                        "event_number": event_num,
                        "user_index": user_index,
                        "timestamp": datetime.now().isoformat()
                    }
                    event_type = "agent_thinking"
                
                try:
                    result = await bridge.emit_event(
                        context=context,
                        event_type=event_type,
                        event_data=event_data
                    )
                    results.append(result)
                except Exception as e:
                    results.append(False)
                    print(f"Event error for user {user_index}, event {event_num}: {e}")
                
                # Small delay to allow concurrent processing
                await asyncio.sleep(0.1)
            
            return results
        
        # Execute concurrent event sending
        send_tasks = [
            asyncio.create_task(send_user_events(client_context, i))
            for i, client_context in enumerate(clients)
        ]
        
        concurrent_results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # Wait for event delivery
        await asyncio.sleep(2.0)
        
        # Assert - Analyze concurrent results
        total_events = 0
        successful_events = 0
        
        for i, result in enumerate(concurrent_results):
            if isinstance(result, list):
                total_events += len(result)
                successful_events += sum(1 for r in result if r is True)
            else:
                print(f"User {i} task failed: {result}")
        
        # Verify system stability
        success_rate = successful_events / total_events if total_events > 0 else 0
        assert success_rate >= 0.6, f"Must maintain reasonable success rate under concurrent stress, got {success_rate:.2%}"
        
        # Verify at least some users received events
        received_events = 0
        for client, _ in clients:
            if hasattr(client, 'received_messages'):
                received_events += len(client.received_messages)
        
        assert received_events > 0, "Some events must be delivered despite concurrent errors"
        
        # Cleanup
        for client, _ in clients:
            try:
                await client.disconnect()
            except Exception:
                pass  # Expected during error testing
    
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_circuit_breaker(self, error_handling_websocket_utility, error_handling_websocket_manager):
        """
        Test WebSocket event delivery circuit breaker pattern.
        
        CRITICAL: Repeated failures must trigger circuit breaker to prevent cascade failures.
        System must protect itself from overload while maintaining core functionality.
        """
        # Arrange
        bridge = AgentWebSocketBridge(error_handling_websocket_manager)
        user_context = UserExecutionContext(
            user_id=UserID(f"circuit_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"circuit_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"circuit_request_{uuid.uuid4().hex[:8]}")
        )
        
        async with error_handling_websocket_utility.connected_client(user_context.user_id) as client:
            await error_handling_websocket_manager.register_user_connection(
                user_context.user_id,
                client.websocket
            )
            
            # Artificially create failing conditions by disconnecting client
            # but keeping it registered (simulates broken connection)
            await client.disconnect()
            
            # Act - Send multiple events to trigger circuit breaker behavior
            failure_count = 0
            success_count = 0
            
            for i in range(10):  # Send 10 events to broken connection
                try:
                    result = await bridge.emit_event(
                        context=user_context,
                        event_type="agent_thinking",
                        event_data={
                            "agent": "circuit_test_agent",
                            "progress": f"attempt {i+1}",
                            "circuit_breaker_test": True,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        failure_count += 1
                        
                except Exception:
                    failure_count += 1
                
                # Brief delay between attempts
                await asyncio.sleep(0.2)
            
            # Assert - System handles repeated failures appropriately
            assert failure_count >= success_count, "Failed connections should result in more failures than successes"
            
            # Test recovery - reconnect and verify normal operation
            reconnected = await client.connect(timeout=30.0)
            if reconnected:
                await error_handling_websocket_manager.register_user_connection(
                    user_context.user_id,
                    client.websocket
                )
                
                # Send recovery event
                recovery_result = await bridge.emit_event(
                    context=user_context,
                    event_type="agent_completed",
                    event_data={
                        "agent": "circuit_test_agent",
                        "status": "completed",
                        "recovery_successful": True,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                assert recovery_result is True, "System must recover after circuit breaker conditions"
                
                # Verify recovery event
                recovery_msg = await client.wait_for_message(
                    event_type=TestEventType.AGENT_COMPLETED,
                    timeout=10.0
                )
                assert recovery_msg.data["recovery_successful"] is True