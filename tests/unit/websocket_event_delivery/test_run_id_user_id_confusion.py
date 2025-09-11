"""
Unit Tests for WebSocket Event Delivery ID Confusion (Issue #373)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent silent failures in core chat functionality
- Value Impact: Ensures all 5 critical WebSocket events reach users correctly
- Strategic Impact: Protects $500K+ ARR by preventing event delivery failures

This test suite implements the test plan for issue #373 - Silent WebSocket Event Delivery Failures.
It demonstrates the User ID/Run ID confusion issue where WebSocket events are routed using
run_id instead of user_id, causing events to be sent to non-existent connections.

Key Test Coverage:
1. User ID vs Run ID confusion reproduction - shows incorrect routing
2. Silent failure pattern reproduction - demonstrates execution continues despite failures  
3. Missing event delivery confirmation - verifies no retry mechanism exists

Expected Behavior: These tests are DESIGNED TO FAIL to demonstrate current issues.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Core imports from SSOT Import Registry
from netra_backend.app.services.user_execution_context import UserExecutionContext, create_isolated_execution_context
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, create_agent_websocket_bridge
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from shared.types.core_types import UserID, ThreadID, RunID


class TestRunIdUserIdConfusion(SSotAsyncTestCase):
    """Unit tests demonstrating User ID vs Run ID confusion in WebSocket event delivery."""

    def setup_method(self, method=None):
        """Set up test fixtures with distinct user_id and run_id."""
        super().setup_method(method)
        
        # Create distinct IDs to highlight the confusion
        self.user_id = "user_12345678"
        self.thread_id = "thread_abcdefgh"
        self.run_id = "run_98765432"  # Deliberately different from user_id
        self.agent_name = "TestOptimizationAgent"
        
        # Create UserExecutionContext with distinct IDs
        self.user_context = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            websocket_client_id=self.user_id,  # WebSocket should use user_id
            agent_context={
                "agent_name": self.agent_name,
                "user_query": "Test query for optimization analysis"
            },
            audit_metadata={
                "test_context": "issue_373_reproduction",
                "expected_behavior": "events_should_use_user_id_not_run_id"
            }
        )
        
        # Mock WebSocket Manager to capture what ID is used for routing
        self.mock_websocket_manager = AsyncMock(spec=WebSocketManager)
        self.mock_websocket_manager.send_to_user = AsyncMock(return_value=True)
        self.mock_websocket_manager.emit_critical_event = AsyncMock(return_value=None)
        
        # Mock UnifiedWebSocketEmitter
        self.mock_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        self.mock_emitter.emit_agent_started = AsyncMock(return_value=True)
        self.mock_emitter.emit_agent_thinking = AsyncMock(return_value=True)
        self.mock_emitter.emit_tool_executing = AsyncMock(return_value=True)
        self.mock_emitter.emit_tool_completed = AsyncMock(return_value=True)
        self.mock_emitter.emit_agent_completed = AsyncMock(return_value=True)

    async def test_run_id_user_id_confusion_reproduction(self):
        """
        CRITICAL TEST: Demonstrate that agent notifications use run_id instead of user_id.
        
        This test SHOULD FAIL because the current implementation incorrectly uses run_id
        for WebSocket routing instead of user_id, causing events to be sent to non-existent
        connections.
        
        Expected Failure: WebSocket manager receives run_id when it should receive user_id.
        """
        # Create AgentWebSocketBridge with mocked components
        with patch('netra_backend.app.services.agent_websocket_bridge.WebSocketManager') as mock_ws_class:
            mock_ws_class.return_value = self.mock_websocket_manager
            
            # Use the factory method with websocket_manager parameter
            bridge = create_agent_websocket_bridge(
                user_context=self.user_context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # PHASE 1: Test notify_agent_started - should use user_id but currently uses run_id
            await bridge.notify_agent_started(
                run_id=self.run_id,  # Current implementation passes run_id
                agent_name=self.agent_name,
                context={"user_query": "Test optimization request"}
            )
            
            # CRITICAL ASSERTION: This SHOULD FAIL - demonstrates the ID confusion
            # The WebSocket manager should be called with user_id but is called with run_id
            
            # What SHOULD happen (correct behavior):
            expected_user_routing_calls = [
                call(self.user_id, {  # Should route to user_id
                    "type": "agent_started",
                    "agent_name": self.agent_name,
                    "user_id": self.user_id,  # Message should contain user_id
                    "run_id": self.run_id     # Message can reference run_id
                })
            ]
            
            # What ACTUALLY happens (incorrect behavior - demonstrates issue):
            # The method internally tries to resolve thread_id from run_id and fails,
            # or routes to the wrong connection
            
            # Check if WebSocket manager was called at all
            if self.mock_websocket_manager.send_to_user.called:
                actual_calls = self.mock_websocket_manager.send_to_user.call_args_list
                print(f"DEBUG: WebSocket manager called with: {actual_calls}")
                
                # Analyze what ID was used for routing
                for call_args in actual_calls:
                    routing_id = call_args[0][0] if call_args[0] else None
                    print(f"DEBUG: Event routed using ID: {routing_id}")
                    
                    # This assertion SHOULD FAIL - demonstrating the issue
                    assert routing_id == self.user_id, (
                        f"ISSUE #373: WebSocket event routed using {routing_id} instead of user_id {self.user_id}. "
                        f"This causes events to be sent to non-existent connections."
                    )
            else:
                # No WebSocket calls made - also indicates failure
                pytest.fail(
                    f"ISSUE #373: WebSocket manager was not called at all. "
                    f"Event delivery failed silently for user_id={self.user_id}, run_id={self.run_id}"
                )

    async def test_silent_failure_pattern_reproduction(self):
        """
        CRITICAL TEST: Demonstrate that execution continues despite WebSocket event delivery failures.
        
        This test SHOULD FAIL because the current implementation doesn't properly handle
        WebSocket delivery failures, allowing execution to continue silently while users
        receive no feedback.
        
        Expected Failure: Execution should fail when critical events can't be delivered.
        """
        # Setup WebSocket manager to simulate "no connections found" failure
        self.mock_websocket_manager.send_to_user = AsyncMock(return_value=False)
        self.mock_websocket_manager.emit_critical_event = AsyncMock(
            side_effect=Exception("No WebSocket connection found for user")
        )
        
        # Track all event delivery attempts
        event_delivery_results = []
        
        with patch('netra_backend.app.services.agent_websocket_bridge.WebSocketManager') as mock_ws_class:
            mock_ws_class.return_value = self.mock_websocket_manager
            
            bridge = create_agent_websocket_bridge(
                user_context=self.user_context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # Attempt to deliver all 5 critical events
            critical_events = [
                ("agent_started", lambda: bridge.notify_agent_started(self.run_id, self.agent_name)),
                ("agent_thinking", lambda: bridge.notify_agent_thinking(self.run_id, self.agent_name, "Analyzing requirements")),
                ("tool_executing", lambda: bridge.notify_tool_executing(self.run_id, "optimization_analyzer")),
                ("tool_completed", lambda: bridge.notify_tool_completed(self.run_id, "optimization_analyzer", {"status": "completed"})),
                ("agent_completed", lambda: bridge.notify_agent_completed(self.run_id, self.agent_name, {"status": "success"}))
            ]
            
            # Attempt each event delivery
            for event_name, event_func in critical_events:
                try:
                    result = await event_func()
                    event_delivery_results.append({
                        "event": event_name,
                        "result": result,
                        "exception": None
                    })
                except Exception as e:
                    event_delivery_results.append({
                        "event": event_name,
                        "result": False,
                        "exception": str(e)
                    })
            
            # CRITICAL ASSERTION: This SHOULD FAIL - demonstrates silent failures
            failed_events = [r for r in event_delivery_results if not r["result"]]
            
            # Check if execution continued despite failures
            if len(failed_events) > 0:
                # This assertion SHOULD FAIL - showing the silent failure pattern
                assert len(failed_events) == 0, (
                    f"ISSUE #373: {len(failed_events)} critical events failed delivery but execution continued silently. "
                    f"Failed events: {[e['event'] for e in failed_events]}. "
                    f"Users receive no feedback when WebSocket connections fail."
                )
            
            # Additional check: Verify no error propagation
            # The system should fail fast when critical events can't be delivered
            for result in event_delivery_results:
                if result["exception"]:
                    # This assertion SHOULD FAIL - exceptions should stop execution
                    assert result["exception"] is None, (
                        f"ISSUE #373: Event '{result['event']}' threw exception '{result['exception']}' "
                        f"but execution continued. Critical events must be delivered or execution should fail."
                    )

    async def test_event_delivery_confirmation_missing(self):
        """
        CRITICAL TEST: Verify that failed events are not retried or confirmed.
        
        This test SHOULD FAIL because the current implementation lacks proper
        event delivery confirmation and retry mechanisms.
        
        Expected Failure: No retry logic exists when event delivery fails.
        """
        # Setup WebSocket manager to fail intermittently
        call_count = 0
        
        def mock_send_with_failures(user_id, message):
            nonlocal call_count
            call_count += 1
            # Fail first 2 attempts, succeed on 3rd (if retry exists)
            if call_count <= 2:
                return False
            return True
        
        self.mock_websocket_manager.send_to_user = AsyncMock(side_effect=mock_send_with_failures)
        
        with patch('netra_backend.app.services.agent_websocket_bridge.WebSocketManager') as mock_ws_class:
            mock_ws_class.return_value = self.mock_websocket_manager
            
            bridge = create_agent_websocket_bridge(
                user_context=self.user_context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # Attempt agent_started event that should fail initially
            result = await bridge.notify_agent_started(
                run_id=self.run_id,
                agent_name=self.agent_name,
                context={"user_query": "Test optimization"}
            )
            
            # Check how many delivery attempts were made
            actual_attempts = self.mock_websocket_manager.send_to_user.call_count
            
            # CRITICAL ASSERTION: This SHOULD FAIL - demonstrates missing retry logic
            expected_min_attempts = 3  # Should retry failed events
            
            assert actual_attempts >= expected_min_attempts, (
                f"ISSUE #373: Only {actual_attempts} delivery attempts made, expected at least {expected_min_attempts}. "
                f"No retry mechanism exists for failed event delivery. "
                f"Critical events are lost when initial delivery fails."
            )
            
            # Additional check: Verify delivery confirmation
            # The method should return False when delivery fails, True when it succeeds
            if call_count <= 2:  # If no retries happened, result should be False
                assert result, (
                    f"ISSUE #373: Event delivery returned {result} despite WebSocket failures. "
                    f"Methods should return False when event delivery fails to enable proper error handling."
                )

    async def test_websocket_connection_id_vs_user_id_mismatch(self):
        """
        CRITICAL TEST: Demonstrate mismatch between UserExecutionContext user_id and WebSocket routing.
        
        This test shows that even when UserExecutionContext contains the correct user_id,
        the WebSocket event methods don't use it correctly for routing.
        
        Expected Failure: WebSocket events should use UserExecutionContext.user_id for routing.
        """
        # Create a realistic UserExecutionContext with proper user_id
        context_with_user_id = UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            websocket_client_id=self.user_id,  # This is correct - WebSocket should route to user_id
            agent_context={"test": "websocket_routing"}
        )
        
        # Mock a method that should accept UserExecutionContext and route correctly
        async def mock_agent_method_with_context(context: UserExecutionContext):
            """Simulates an agent method that should use UserExecutionContext for routing."""
            # This is what SHOULD happen - use context.user_id for WebSocket routing
            bridge = create_agent_websocket_bridge(
                user_context=context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # BUT current implementation uses run_id instead of context.user_id
            return await bridge.notify_agent_started(
                run_id=context.run_id,  # ISSUE: Using run_id instead of user_id
                agent_name=self.agent_name
            )
        
        # Execute the method with proper context
        await mock_agent_method_with_context(context_with_user_id)
        
        # Verify WebSocket manager was called
        if self.mock_websocket_manager.send_to_user.called:
            call_args = self.mock_websocket_manager.send_to_user.call_args_list[0]
            routing_id_used = call_args[0][0] if call_args[0] else None
            
            # CRITICAL ASSERTION: This SHOULD FAIL - shows the mismatch
            assert routing_id_used == context_with_user_id.user_id, (
                f"ISSUE #373: WebSocket routed using {routing_id_used} but UserExecutionContext.user_id is {context_with_user_id.user_id}. "
                f"WebSocket events should use context.user_id for routing, not run_id. "
                f"This causes events to be sent to wrong/non-existent connections."
            )
        else:
            pytest.fail(
                f"ISSUE #373: WebSocket manager not called despite valid UserExecutionContext with user_id={context_with_user_id.user_id}"
            )

    async def test_multiple_concurrent_users_id_isolation(self):
        """
        CRITICAL TEST: Demonstrate that concurrent users with different user_id/run_id combinations
        can experience cross-contamination in WebSocket event routing.
        
        Expected Failure: Events for different users may be misrouted due to run_id usage.
        """
        # Create multiple user contexts with distinct IDs
        user_contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"user_{i}_123456",
                thread_id=f"thread_{i}_abcdef",
                run_id=f"run_{i}_789012",
                websocket_client_id=f"user_{i}_123456",
                agent_context={"user_index": i}
            )
            user_contexts.append(context)
        
        # Track which user_id each event was routed to
        routing_calls = []
        
        def track_routing(user_id, message):
            routing_calls.append({
                "routed_to_user_id": user_id,
                "message_run_id": message.get("run_id"),
                "message_type": message.get("type")
            })
            return True
        
        self.mock_websocket_manager.send_to_user = AsyncMock(side_effect=track_routing)
        
        with patch('netra_backend.app.services.agent_websocket_bridge.WebSocketManager') as mock_ws_class:
            mock_ws_class.return_value = self.mock_websocket_manager
            
            bridge = create_agent_websocket_bridge(
                user_context=self.user_context,
                websocket_manager=self.mock_websocket_manager
            )
            
            # Send events for each user concurrently
            tasks = []
            for context in user_contexts:
                task = bridge.notify_agent_started(
                    run_id=context.run_id,  # Current implementation uses run_id
                    agent_name=f"Agent_for_user_{context.user_id}"
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        # Verify each event was routed to the correct user_id
        for i, context in enumerate(user_contexts):
            if i < len(routing_calls):
                routing_call = routing_calls[i]
                
                # CRITICAL ASSERTION: This SHOULD FAIL - demonstrates routing issues
                assert routing_call["routed_to_user_id"] == context.user_id, (
                    f"ISSUE #373: Event for user {context.user_id} was routed to {routing_call['routed_to_user_id']}. "
                    f"Concurrent users experience misrouted events due to run_id vs user_id confusion."
                )
            else:
                pytest.fail(
                    f"ISSUE #373: No routing call found for user {context.user_id}. "
                    f"Events may be lost in concurrent user scenarios."
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])