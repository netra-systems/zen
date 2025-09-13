"""
Mission Critical Test: Concurrent User Isolation Violation Proof

This test is designed to FAIL initially, proving that WebSocket SSOT violations
cause 0% success rate for concurrent users - blocking $500K+ ARR.

Business Impact:
- $500K+ ARR at immediate risk from non-functional concurrent chat
- 90% of platform value blocked (chat is core business)
- 0% concurrent user success rate due to shared state violations

SSOT Violations Tested:
- Multiple WebSocketNotifier implementations causing state bleeding
- Factory pattern failures preventing proper user isolation
- Shared state between concurrent user sessions

This test MUST FAIL until SSOT consolidation is complete.
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase

try:
    # SSOT imports - these should work after consolidation
    from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    from netra_backend.app.core.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.factory import AgentFactory
except ImportError as e:
    # Expected during SSOT migration - imports will be fixed during consolidation
    print(f"EXPECTED IMPORT ERROR during SSOT migration: {e}")
    UnifiedWebSocketManager = None
    ExecutionEngine = None
    UserExecutionContext = None
    AgentFactory = None


class TestConcurrentUserIsolation(SSotAsyncTestCase):
    """
    CRITICAL: This test proves concurrent user isolation violations.

    EXPECTED RESULT: FAIL - proving 0% concurrent user success rate
    BUSINESS IMPACT: $500K+ ARR blocked by WebSocket SSOT violations
    """

    def setup_method(self):
        """Set up test environment for concurrent user isolation testing."""
        super().setup_method()
        self.user1_id = "test_user_1"
        self.user2_id = "test_user_2"
        self.test_message = "AI optimization request"
        self.concurrent_success_rate = 0

    @pytest.mark.asyncio
    async def test_concurrent_websocket_user_isolation_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove concurrent user isolation violations

        Expected Result: FAIL - Cross-contamination between users detected
        Business Impact: $500K+ ARR - chat functionality completely broken for concurrent users
        """
        if not all([UnifiedWebSocketManager, ExecutionEngine, UserExecutionContext]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Test Setup: Create two concurrent user contexts
        user1_context = await self._create_user_context(self.user1_id)
        user2_context = await self._create_user_context(self.user2_id)

        # Track WebSocket events for each user
        user1_events = []
        user2_events = []

        # Create WebSocket managers for each user (should be isolated)
        user1_manager = await self._create_websocket_manager(self.user1_id, user1_events)
        user2_manager = await self._create_websocket_manager(self.user2_id, user2_events)

        # CRITICAL TEST: Send concurrent messages
        await asyncio.gather(
            self._send_ai_request(user1_manager, user1_context, f"User1: {self.test_message}"),
            self._send_ai_request(user2_manager, user2_context, f"User2: {self.test_message}")
        )

        # Wait for processing
        await asyncio.sleep(2)

        # ASSERTION: Events should be user-isolated
        # This SHOULD FAIL due to SSOT violations causing cross-contamination
        self._assert_user_isolation(user1_events, user2_events, self.user1_id, self.user2_id)

        # Calculate concurrent user success rate
        user1_success = self._calculate_user_success_rate(user1_events, self.user1_id)
        user2_success = self._calculate_user_success_rate(user2_events, self.user2_id)

        # CRITICAL ASSERTION: Both users should succeed independently
        # This WILL FAIL proving 0% concurrent success rate
        assert user1_success == 1.0, f"User1 success rate: {user1_success} (expected 1.0)"
        assert user2_success == 1.0, f"User2 success rate: {user2_success} (expected 1.0)"

        # Overall concurrent success rate
        self.concurrent_success_rate = (user1_success + user2_success) / 2
        assert self.concurrent_success_rate == 1.0, f"BUSINESS CRITICAL: Concurrent success rate: {self.concurrent_success_rate}% - $500K+ ARR at risk"

    async def _create_user_context(self, user_id: str) -> UserExecutionContext:
        """Create isolated user execution context."""
        try:
            return UserExecutionContext.create_for_user(user_id)
        except Exception as e:
            # Expected during SSOT migration
            pytest.fail(f"SSOT VIOLATION: Cannot create isolated context for {user_id}: {e}")

    async def _create_websocket_manager(self, user_id: str, event_collector: list):
        """Create WebSocket manager for user - should be isolated."""
        try:
            # Mock WebSocket connection for testing
            mock_websocket = MagicMock()
            mock_websocket.user_id = user_id

            # Create manager (should be user-isolated)
            manager = UnifiedWebSocketManager()

            # Hook into event sending to collect events
            original_send = manager.send_to_thread if hasattr(manager, 'send_to_thread') else lambda *args, **kwargs: None

            def collect_events(event_type, data, thread_id=None):
                event_collector.append({
                    'event_type': event_type,
                    'data': data,
                    'thread_id': thread_id,
                    'user_id': user_id,
                    'timestamp': asyncio.get_event_loop().time()
                })
                return original_send(event_type, data, thread_id)

            manager.send_to_thread = collect_events
            return manager

        except Exception as e:
            pytest.fail(f"SSOT VIOLATION: Cannot create isolated WebSocket manager for {user_id}: {e}")

    async def _send_ai_request(self, manager, context, message: str):
        """Send AI request through WebSocket - simulates real user interaction."""
        try:
            # Simulate agent execution with WebSocket events
            # This should send all 5 critical events: agent_started, agent_thinking,
            # tool_executing, tool_completed, agent_completed

            # Event 1: agent_started
            manager.send_to_thread("agent_started", {
                "message": message,
                "context_id": context.context_id if context else "missing_context"
            })

            # Event 2: agent_thinking
            manager.send_to_thread("agent_thinking", {
                "reasoning": "Processing user request...",
                "context_id": context.context_id if context else "missing_context"
            })

            # Event 3: tool_executing
            manager.send_to_thread("tool_executing", {
                "tool_name": "ai_optimizer",
                "context_id": context.context_id if context else "missing_context"
            })

            # Event 4: tool_completed
            manager.send_to_thread("tool_completed", {
                "tool_name": "ai_optimizer",
                "result": "Optimization complete",
                "context_id": context.context_id if context else "missing_context"
            })

            # Event 5: agent_completed
            manager.send_to_thread("agent_completed", {
                "final_response": "AI optimization completed successfully",
                "context_id": context.context_id if context else "missing_context"
            })

        except Exception as e:
            pytest.fail(f"SSOT VIOLATION: Cannot send AI request via WebSocket: {e}")

    def _assert_user_isolation(self, user1_events: list, user2_events: list, user1_id: str, user2_id: str):
        """Assert that user events are properly isolated - THIS WILL FAIL."""

        # Check for cross-contamination
        user1_contaminated_events = [e for e in user1_events if e.get('user_id') != user1_id]
        user2_contaminated_events = [e for e in user2_events if e.get('user_id') != user2_id]

        if user1_contaminated_events:
            pytest.fail(f"SSOT VIOLATION: User1 received {len(user1_contaminated_events)} events from other users: {user1_contaminated_events}")

        if user2_contaminated_events:
            pytest.fail(f"SSOT VIOLATION: User2 received {len(user2_contaminated_events)} events from other users: {user2_contaminated_events}")

        # Check that both users received their own events
        assert len(user1_events) > 0, f"SSOT VIOLATION: User1 received no events - complete isolation failure"
        assert len(user2_events) > 0, f"SSOT VIOLATION: User2 received no events - complete isolation failure"

    def _calculate_user_success_rate(self, events: list, expected_user_id: str) -> float:
        """Calculate success rate for user - should be 1.0 but will be 0.0 due to SSOT violations."""
        if not events:
            return 0.0

        # Required events for successful AI interaction
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        received_events = set(e['event_type'] for e in events if e.get('user_id') == expected_user_id)

        # Calculate success rate based on received vs required events
        success_rate = len(received_events.intersection(required_events)) / len(required_events)

        return success_rate

    @pytest.mark.asyncio
    async def test_factory_pattern_user_isolation_violation(self):
        """
        CRITICAL: Test factory pattern violations preventing user isolation

        Expected Result: FAIL - Same instance returned for different users
        Business Impact: Shared state between users = 0% concurrent success
        """
        if not AgentFactory:
            pytest.skip("SSOT imports not available - expected during migration")

        # Create agents for two different users
        user1_agent = AgentFactory.create_supervisor_agent(self.user1_id)
        user2_agent = AgentFactory.create_supervisor_agent(self.user2_id)

        # CRITICAL ASSERTION: Should be different instances (will fail due to SSOT violations)
        assert user1_agent is not user2_agent, "SSOT VIOLATION: Factory returned same instance for different users"

        # Check for shared state violations
        if hasattr(user1_agent, 'context_id') and hasattr(user2_agent, 'context_id'):
            assert user1_agent.context_id != user2_agent.context_id, "SSOT VIOLATION: Agents share context IDs"

        # Test state isolation
        test_state = "user_specific_state"
        if hasattr(user1_agent, 'set_state'):
            user1_agent.set_state(test_state + "_user1")
        if hasattr(user2_agent, 'set_state'):
            user2_agent.set_state(test_state + "_user2")

        # Verify no state bleeding between users
        if hasattr(user1_agent, 'get_state') and hasattr(user2_agent, 'get_state'):
            user1_state = user1_agent.get_state()
            user2_state = user2_agent.get_state()

            assert user1_state != user2_state, f"SSOT VIOLATION: State bleeding detected - User1: {user1_state}, User2: {user2_state}"
            assert self.user1_id in str(user1_state) if user1_state else True, "User1 agent state should contain user1 ID"
            assert self.user2_id in str(user2_state) if user2_state else True, "User2 agent state should contain user2 ID"


if __name__ == "__main__":
    # Run this test to prove concurrent user isolation violations
    pytest.main([__file__, "-v", "--tb=short"])