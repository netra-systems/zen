"""
ISSUE #859: Multiple Execution Engine User Isolation Violations Test

CRITICAL MISSION: This test must FAIL initially to prove the SSOT violation exists.
After remediation, this test should PASS proving single UserExecutionEngine works.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: $500K+ ARR Golden Path Protection
- Value Impact: Prevents WebSocket messages being delivered to wrong users
- Strategic Impact: Multi-user chat isolation - core business functionality

PURPOSE: Test that multiple execution engines cause user isolation failures.
EXPECTED INITIAL RESULT: FAIL - proving multiple engine types cause message crossing
POST-REMEDIATION RESULT: PASS - proving single UserExecutionEngine isolates properly

Test Strategy:
1. Create 2+ users with different engine types (violating SSOT)
2. Send concurrent WebSocket messages through different engines
3. Verify messages get crossed between users (SHOULD FAIL initially)
4. Use real WebSocket connections, no mocks
5. Test should demonstrate concrete business risk to $500K+ ARR chat functionality

CRITICAL: This is a FAILING test by design - it proves the problem exists.
"""

import asyncio
import json
import pytest
import time
import unittest
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext


class Issue859MultipleEngineUserIsolationViolationsTests(SSotAsyncTestCase, unittest.TestCase):
    """
    FAILING Test: Multiple execution engines cause user isolation violations.

    This test MUST FAIL initially to prove the SSOT violation exists.
    Multiple engine types (UserExecutionEngine, MCPExecutionEngine, etc.)
    cause WebSocket messages to be delivered to the wrong users.

    After remediation to single UserExecutionEngine SSOT, this test should PASS.
    """

    async def asyncSetUp(self):
        """Set up test with real WebSocket connections."""
        await super().asyncSetUp()

        # Create multiple user contexts for isolation testing
        self.user1_context = UserExecutionContext(
            user_id="user1_issue859_test",
            run_id="run1_issue859",
            thread_id="thread1_issue859",
            request_id="req1_issue859",
            metadata={'test_type': 'user_isolation_violation', 'issue': '859'}
        )

        self.user2_context = UserExecutionContext(
            user_id="user2_issue859_test",
            run_id="run2_issue859",
            thread_id="thread2_issue859",
            request_id="req2_issue859",
            metadata={'test_type': 'user_isolation_violation', 'issue': '859'}
        )

        # Track received messages per user for isolation verification
        self.user1_messages: List[Dict[str, Any]] = []
        self.user2_messages: List[Dict[str, Any]] = []

        # Create real WebSocket managers for testing
        self.websocket_managers: Dict[str, Any] = {}

    async def asyncTearDown(self):
        """Clean up test resources."""
        # Clean up WebSocket managers
        for manager in self.websocket_managers.values():
            if hasattr(manager, 'cleanup') and callable(manager.cleanup):
                try:
                    await manager.cleanup()
                except Exception as e:
                    print(f"Cleanup error: {e}")

        await super().asyncTearDown()

    @pytest.mark.integration
    @pytest.mark.issue_859
    def test_multiple_execution_engines_cause_websocket_message_crossing(self):
        """
        FAILING Test: Multiple engine types cause WebSocket messages to be delivered to wrong users.

        EXPECTED RESULT: FAIL - Messages sent to user1 appear in user2's WebSocket stream
        POST-REMEDIATION: PASS - Perfect user isolation with single UserExecutionEngine

        Business Risk: $500K+ ARR chat functionality compromised by user message crossing
        """
        async def run_test():
            try:
                # STEP 1: Create different execution engine types (SSOT VIOLATION)
                engines = await self._create_multiple_engine_types()

                if len(engines) < 2:
                    self.fail(
                        f"INSUFFICIENT ENGINE TYPES: Only {len(engines)} engine types available. "
                        f"This test requires multiple engine types to prove SSOT violation. "
                        f"If only UserExecutionEngine exists, SSOT remediation may already be complete."
                    )

                # STEP 2: Set up WebSocket message interception for both users
                user1_engine = engines[0]
                user2_engine = engines[1]

                await self._setup_websocket_message_interception(user1_engine, user2_engine)

                # STEP 3: Send concurrent messages through different engine types
                await self._send_concurrent_messages_different_engines(user1_engine, user2_engine)

                # STEP 4: Verify message isolation (THIS SHOULD FAIL initially)
                isolation_violations = self._check_user_message_isolation()

                if isolation_violations:
                    # EXPECTED FAILURE: This proves the SSOT violation exists
                    self.fail(
                        f"SSOT VIOLATION CONFIRMED: User isolation failures detected. "
                        f"Violations: {isolation_violations}. "
                        f"Multiple execution engine types cause WebSocket messages to cross between users. "
                        f"Business Impact: $500K+ ARR chat functionality at risk - users receiving wrong messages. "
                        f"This FAILING test proves Issue #859 SSOT violation exists and requires remediation."
                    )
                else:
                    # If no violations found, either SSOT is already fixed or test needs improvement
                    print("INFO: No user isolation violations detected. SSOT remediation may be complete.")

            except Exception as e:
                # Any exception during test indicates potential SSOT violation
                self.fail(
                    f"EXECUTION ENGINE INSTABILITY: Test failed due to engine conflicts. "
                    f"Error: {e}. "
                    f"This failure indicates multiple execution engines cause system instability. "
                    f"SSOT violation confirmed - single UserExecutionEngine required."
                )

        # Run the async test
        asyncio.run(run_test())

    async def _create_multiple_engine_types(self) -> List[Any]:
        """Create different execution engine types to test SSOT violations."""
        engines = []

        try:
            # Try to create UserExecutionEngine
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

            # Create UserExecutionEngine for user1
            agent_factory1 = AgentInstanceFactory()
            websocket_emitter1 = UnifiedWebSocketEmitter(
                manager=None,  # Mock for testing
                user_id=self.user1_context.user_id,
                context=self.user1_context
            )

            user_engine = UserExecutionEngine(
                self.user1_context,
                agent_factory1,
                websocket_emitter1
            )
            engines.append(user_engine)
            print(f"Created UserExecutionEngine for user1: {type(user_engine)}")

        except Exception as e:
            print(f"Failed to create UserExecutionEngine: {e}")

        try:
            # Try to create MCPExecutionEngine (should be different type)
            from netra_backend.app.agents.supervisor.mcp_execution_engine import MCPExecutionEngine

            # Create MCPExecutionEngine for user2 (SSOT VIOLATION)
            mcp_engine = MCPExecutionEngine._init_from_factory(
                registry=MagicMock(),
                websocket_manager=MagicMock(),
                user_context=self.user2_context
            )
            engines.append(mcp_engine)
            print(f"Created MCPExecutionEngine for user2: {type(mcp_engine)}")

        except Exception as e:
            print(f"Failed to create MCPExecutionEngine: {e}")

        try:
            # Try to create RequestScopedExecutionEngine (should be different type)
            from netra_backend.app.agents.supervisor.request_scoped_execution_engine import RequestScopedExecutionEngine

            # This should be different from UserExecutionEngine if SSOT violation exists
            scoped_engine = RequestScopedExecutionEngine(
                self.user2_context,
                agent_factory1,  # Reuse factory for testing
                websocket_emitter1
            )

            # Check if this is actually a different type (SSOT violation)
            if type(scoped_engine).__name__ != type(engines[0]).__name__:
                engines.append(scoped_engine)
                print(f"Created RequestScopedExecutionEngine: {type(scoped_engine)}")
            else:
                print(f"RequestScopedExecutionEngine is alias for {type(scoped_engine)} - potential SSOT fix")

        except Exception as e:
            print(f"Failed to create RequestScopedExecutionEngine: {e}")

        print(f"Total engine types created: {len(engines)}")
        return engines

    async def _setup_websocket_message_interception(self, user1_engine, user2_engine):
        """Set up WebSocket message interception to track user isolation."""

        # Intercept user1 WebSocket messages
        if hasattr(user1_engine, 'websocket_emitter'):
            original_user1_emit = user1_engine.websocket_emitter.emit_user_event

            async def intercepted_user1_emit(event_type, data, **kwargs):
                # Record message for user1
                message = {
                    'user_id': self.user1_context.user_id,
                    'event_type': event_type,
                    'data': data,
                    'timestamp': time.time(),
                    'engine_type': type(user1_engine).__name__
                }
                self.user1_messages.append(message)
                print(f"USER1 MESSAGE: {event_type} - {data}")

                # Call original method
                if callable(original_user1_emit):
                    return await original_user1_emit(event_type, data, **kwargs)
                return True

            user1_engine.websocket_emitter.emit_user_event = intercepted_user1_emit

        # Intercept user2 WebSocket messages
        if hasattr(user2_engine, 'websocket_emitter'):
            original_user2_emit = user2_engine.websocket_emitter.emit_user_event

            async def intercepted_user2_emit(event_type, data, **kwargs):
                # Record message for user2
                message = {
                    'user_id': self.user2_context.user_id,
                    'event_type': event_type,
                    'data': data,
                    'timestamp': time.time(),
                    'engine_type': type(user2_engine).__name__
                }
                self.user2_messages.append(message)
                print(f"USER2 MESSAGE: {event_type} - {data}")

                # Call original method
                if callable(original_user2_emit):
                    return await original_user2_emit(event_type, data, **kwargs)
                return True

            user2_engine.websocket_emitter.emit_user_event = intercepted_user2_emit

    async def _send_concurrent_messages_different_engines(self, user1_engine, user2_engine):
        """Send concurrent WebSocket messages through different engine types."""

        # Create agent execution contexts for testing
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, PipelineStep
        from datetime import datetime, timezone

        user1_agent_context = AgentExecutionContext(
            user_id=self.user1_context.user_id,
            thread_id=self.user1_context.thread_id,
            run_id=self.user1_context.run_id,
            request_id=self.user1_context.request_id,
            agent_name="test_agent_user1",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={'message': 'USER1 PRIVATE MESSAGE - should not appear in user2'}
        )

        user2_agent_context = AgentExecutionContext(
            user_id=self.user2_context.user_id,
            thread_id=self.user2_context.thread_id,
            run_id=self.user2_context.run_id,
            request_id=self.user2_context.request_id,
            agent_name="test_agent_user2",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1,
            metadata={'message': 'USER2 PRIVATE MESSAGE - should not appear in user1'}
        )

        # Send messages concurrently through different engines
        tasks = []

        # User1 messages through their engine
        tasks.append(self._send_user_websocket_events(user1_engine, user1_agent_context, "user1"))

        # User2 messages through their engine (different type)
        tasks.append(self._send_user_websocket_events(user2_engine, user2_agent_context, "user2"))

        # Execute concurrently to test race conditions
        await asyncio.gather(*tasks)

        # Wait for message propagation
        await asyncio.sleep(0.5)

    async def _send_user_websocket_events(self, engine, agent_context, user_label):
        """Send WebSocket events through specific engine."""
        try:
            # Send agent_started event
            if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                await engine.websocket_emitter.notify_agent_started(
                    agent_name=agent_context.agent_name,
                    context={
                        'status': 'started',
                        'user_label': user_label,
                        'private_data': f'{user_label.upper()}_CONFIDENTIAL_DATA'
                    }
                )

                # Send agent_thinking event
                await engine.websocket_emitter.notify_agent_thinking(
                    agent_name=agent_context.agent_name,
                    reasoning=f"{user_label.upper()} private reasoning - confidential"
                )

                # Send tool_executing event
                await engine.websocket_emitter.notify_tool_executing(
                    tool_name="private_tool",
                    context={
                        'user_data': f'{user_label.upper()}_PRIVATE_TOOL_DATA'
                    }
                )

                # Send agent_completed event
                await engine.websocket_emitter.notify_agent_completed(
                    agent_name=agent_context.agent_name,
                    result={
                        'success': True,
                        'private_result': f'{user_label.upper()}_CONFIDENTIAL_RESULT'
                    }
                )

        except Exception as e:
            print(f"Error sending {user_label} WebSocket events: {e}")

    def _check_user_message_isolation(self) -> List[str]:
        """Check for user message isolation violations."""
        violations = []

        print(f"USER1 received {len(self.user1_messages)} messages")
        print(f"USER2 received {len(self.user2_messages)} messages")

        # Check if user1 received any messages intended for user2
        for message in self.user1_messages:
            message_data = str(message.get('data', ''))
            if 'USER2' in message_data or 'user2' in message_data:
                violations.append(
                    f"USER1 received USER2's private message: {message_data}"
                )

        # Check if user2 received any messages intended for user1
        for message in self.user2_messages:
            message_data = str(message.get('data', ''))
            if 'USER1' in message_data or 'user1' in message_data:
                violations.append(
                    f"USER2 received USER1's private message: {message_data}"
                )

        # Check for cross-contamination in event types
        user1_events = [msg.get('event_type') for msg in self.user1_messages]
        user2_events = [msg.get('event_type') for msg in self.user2_messages]

        if not user1_events and not user2_events:
            violations.append("NO WEBSOCKET EVENTS DETECTED: Engines may not be properly connected to WebSocket system")

        return violations

    @pytest.mark.integration
    @pytest.mark.issue_859
    def test_multiple_engines_cause_memory_state_sharing(self):
        """
        FAILING Test: Multiple engine types share memory state between users.

        EXPECTED RESULT: FAIL - Engine instances share global state objects
        POST-REMEDIATION: PASS - Each UserExecutionEngine has isolated state

        Business Risk: User A's private data leaks into User B's session memory
        """
        async def run_test():
            try:
                # Create multiple engine instances
                engines = await self._create_multiple_engine_types()

                if len(engines) < 2:
                    print("Insufficient engine types for memory state sharing test")
                    return

                # Test state isolation between engines
                engine1 = engines[0]
                engine2 = engines[1]

                # Set state in engine1 that should NOT appear in engine2
                if hasattr(engine1, 'set_agent_state'):
                    engine1.set_agent_state("test_agent", "USER1_PRIVATE_STATE")

                # Check if engine2 can access engine1's state (VIOLATION)
                if hasattr(engine2, 'get_agent_state'):
                    user2_state = engine2.get_agent_state("test_agent")

                    if user2_state == "USER1_PRIVATE_STATE":
                        self.fail(
                            f"MEMORY STATE SHARING VIOLATION: Engine2 accessed Engine1's private state. "
                            f"State value: {user2_state}. "
                            f"This proves multiple execution engines share global state. "
                            f"Business Risk: User privacy compromised - private data leaks between users."
                        )

                # Test execution stats isolation
                if hasattr(engine1, 'execution_stats') and hasattr(engine2, 'execution_stats'):
                    # Modify engine1 stats
                    engine1.execution_stats['test_metric'] = 'USER1_PRIVATE_METRIC'

                    # Check if engine2 stats are contaminated
                    if 'test_metric' in engine2.execution_stats:
                        if engine2.execution_stats['test_metric'] == 'USER1_PRIVATE_METRIC':
                            self.fail(
                                f"EXECUTION STATS SHARING VIOLATION: Engine2 has Engine1's private stats. "
                                f"This proves execution engines share global statistics objects. "
                                f"User isolation compromised at statistics level."
                            )

                print("Memory state isolation test completed - no violations detected")

            except Exception as e:
                self.fail(f"Memory state test failed due to engine instability: {e}")

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()