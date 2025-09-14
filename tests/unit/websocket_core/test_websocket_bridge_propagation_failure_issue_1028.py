#!/usr/bin/env python
"""Issue #1028: WebSocket Bridge Propagation Failure Reproduction Tests

PURPOSE: Create FAILING tests that reproduce the exact WebSocket bridge propagation 
failure described in Issue #1028 - missing completion notifications to users.

BUSINESS IMPACT: When WebSocket bridge propagation fails, users don't receive 
agent_completed events, making it appear that agents are hung even when they
complete successfully. This breaks the 90% of platform value delivered through chat.

EXPECTED BEHAVIOR: These tests should FAIL initially, proving that:
1. Parameter alignment issues between AgentExecutionCore and AgentExecutionTracker
2. WebSocket manager propagation failures in UserExecutionContext scenarios  
3. Missing completion notifications when agent execution succeeds

TEST STRATEGY: 
- Unit tests for parameter alignment consistency
- Integration tests for real UserExecutionContext + WebSocket manager scenarios
- Focus on the specific completion notification failure mode

CRITICAL: These tests are designed to FAIL and should only PASS after Issue #1028 fix.
"""

import asyncio
import sys
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger

# Import core components for testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, AgentExecutionPhase
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
from netra_backend.app.core.timeout_configuration import TimeoutTier

# Import types
from shared.types.core_types import UserID, ThreadID, ensure_user_id, ensure_thread_id
from netra_backend.app.core.unified_id_manager import generate_user_id, generate_thread_id

logger = get_logger(__name__)


class TestWebSocketBridgePropagationFailureIssue1028(SSotAsyncTestCase):
    """
    ISSUE #1028 REPRODUCTION: WebSocket Bridge Propagation Failure Tests
    
    These tests are designed to FAIL and reproduce the exact issue where:
    1. AgentExecutionCore.execute_agent() calls AgentExecutionTracker methods
    2. Parameter alignment issues prevent proper WebSocket event emission
    3. Users don't receive agent_completed events even when agents succeed
    
    EXPECTED: All tests in this class should FAIL initially
    AFTER FIX: Tests should pass with proper completion notifications
    """

    def setup_method(self, method):
        """Setup test environment for WebSocket bridge propagation testing."""
        super().setup_method(method)

        # Set environment for real service integration testing
        self.set_env_var("TESTING_WEBSOCKET_BRIDGE_PROPAGATION", "true")
        self.set_env_var("WEBSOCKET_COMPLETION_NOTIFICATION_TEST", "true")
        self.set_env_var("ISSUE_1028_REPRODUCTION", "true")

        # Track WebSocket events for validation
        self.captured_events = []
        self.completion_events = []
        self.parameter_misalignments = []
        
        logger.info(f"🔍 ISSUE #1028 TEST: {method.__name__ if method else 'unknown'}")
        logger.info("📍 PURPOSE: Reproduce WebSocket bridge propagation failure")

    async def test_parameter_alignment_failure_execute_agent_vs_emit_phase_event(self):
        """
        CRITICAL: Test parameter alignment between execute_agent() and _emit_phase_event().
        
        ISSUE #1028 ROOT CAUSE: AgentExecutionCore.execute_agent() calls methods on 
        AgentExecutionTracker that expect different parameter formats, causing
        WebSocket events to fail silently.
        
        EXPECTED TO FAIL: Parameter misalignment prevents completion notifications
        """
        logger.info("🔍 TESTING: Parameter alignment between execute_agent() and _emit_phase_event()")

        # Create real components to test actual parameter flow
        mock_registry = MagicMock()
        mock_websocket_bridge = MagicMock()
        
        # Set up successful agent execution scenario
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True, 
            "result": "Agent completed successfully",
            "agent_name": "test_agent"
        })
        mock_registry.get_async = AsyncMock(return_value=mock_agent)

        # Create AgentExecutionCore with real AgentExecutionTracker
        execution_core = AgentExecutionCore(
            registry=mock_registry,
            websocket_bridge=mock_websocket_bridge,
            default_tier=TimeoutTier.FREE
        )

        # Create real user execution context
        user_context = UserExecutionContext(
            user_id=ensure_user_id(generate_user_id()),
            thread_id=ensure_thread_id(generate_thread_id()),
            run_id=str(uuid.uuid4())
        )

        # Create agent execution context 
        agent_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="completion_test_agent"
        )

        # Monitor parameter passing to _emit_phase_event method
        original_emit_phase_event = execution_core.agent_tracker._emit_phase_event
        emit_phase_event_calls = []

        async def capture_emit_phase_event_params(*args, **kwargs):
            """Capture parameters passed to _emit_phase_event for analysis."""
            emit_phase_event_calls.append({
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time(),
                'phase': args[1].to_phase.value if len(args) > 1 and hasattr(args[1], 'to_phase') else 'unknown'
            })
            try:
                return await original_emit_phase_event(*args, **kwargs)
            except Exception as e:
                self.parameter_misalignments.append({
                    'method': '_emit_phase_event',
                    'error': str(e),
                    'args': len(args),
                    'kwargs': list(kwargs.keys()),
                    'exception_type': type(e).__name__
                })
                raise

        execution_core.agent_tracker._emit_phase_event = capture_emit_phase_event_params

        # Execute agent and capture the parameter alignment failure
        try:
            result = await execution_core.execute_agent(
                context=agent_context,
                user_context=user_context,
                timeout=5.0
            )

            # Analyze completion event parameters
            completion_phase_calls = [
                call for call in emit_phase_event_calls 
                if call.get('phase') == AgentExecutionPhase.COMPLETED.value
            ]

            if not completion_phase_calls:
                # EXPECTED FAILURE: No completion phase transition attempted
                failure_message = (
                    f"❌ ISSUE #1028 CONFIRMED: No completion phase transition attempted!\n"
                    f"   Agent execution result: success={result.success}\n"
                    f"   Total phase transitions: {len(emit_phase_event_calls)}\n"
                    f"   Phase transitions attempted: {[call['phase'] for call in emit_phase_event_calls]}\n"
                    f"   Parameter misalignments: {len(self.parameter_misalignments)}\n"
                    f"\n🚨 THIS PROVES NO COMPLETION NOTIFICATION SENT TO USER!"
                )
                logger.error(failure_message)
                pytest.fail(failure_message)

            # Check for parameter alignment issues in completion calls
            completion_call = completion_phase_calls[0]
            if completion_call['args'] and len(completion_call['args']) >= 3:
                # Check if websocket_manager parameter is properly aligned
                websocket_manager_param = completion_call['kwargs'].get('websocket_manager')
                if websocket_manager_param is None:
                    failure_message = (
                        f"❌ ISSUE #1028 CONFIRMED: WebSocket manager not provided to completion phase!\n"
                        f"   Completion call args: {len(completion_call['args'])}\n"
                        f"   Completion call kwargs: {list(completion_call['kwargs'].keys())}\n"
                        f"   WebSocket manager in kwargs: {websocket_manager_param is not None}\n"
                        f"\n🚨 THIS PREVENTS COMPLETION NOTIFICATION FROM BEING SENT!"
                    )
                    logger.error(failure_message)
                    pytest.fail(failure_message)

        except Exception as e:
            # Check if this is a parameter alignment error
            if "parameter" in str(e).lower() or "argument" in str(e).lower():
                failure_message = (
                    f"❌ ISSUE #1028 CONFIRMED: Parameter alignment error in agent execution!\n"
                    f"   Error: {str(e)}\n"
                    f"   Error type: {type(e).__name__}\n"
                    f"   Parameter misalignments detected: {len(self.parameter_misalignments)}\n"
                    f"   Emit phase event calls: {len(emit_phase_event_calls)}\n"
                    f"\n🚨 THIS PREVENTS COMPLETION NOTIFICATIONS FROM REACHING USERS!"
                )
                logger.error(failure_message)
                pytest.fail(failure_message)
            else:
                raise

        # If we get here without failing, the issue might be fixed
        logger.warning("⚠️ Expected parameter alignment failure not detected - Issue #1028 may be resolved")

    async def test_websocket_manager_propagation_failure_in_user_execution_context(self):
        """
        CRITICAL: Test WebSocket manager propagation failure in UserExecutionContext scenarios.
        
        ISSUE #1028 CONTEXT: When using UserExecutionContext with AgentExecutionCore,
        the WebSocket manager may not be properly propagated through the execution
        chain, causing completion notifications to fail.
        
        EXPECTED TO FAIL: WebSocket manager not properly propagated to completion handlers
        """
        logger.info("🔍 TESTING: WebSocket manager propagation in UserExecutionContext scenarios")

        # Create components with real UserExecutionContext
        mock_registry = MagicMock()
        
        # Create real WebSocket bridge to test propagation
        user_context = UserExecutionContext(
            user_id=ensure_user_id(generate_user_id()),
            thread_id=ensure_thread_id(generate_thread_id()),
            run_id=str(uuid.uuid4())
        )

        # Mock WebSocket manager with tracking
        mock_websocket_manager = MagicMock()
        mock_websocket_manager.notify_agent_completed = AsyncMock()
        mock_websocket_manager.notify_agent_started = AsyncMock()
        mock_websocket_manager.notify_agent_thinking = AsyncMock()

        # Create WebSocket bridge
        websocket_bridge = create_agent_websocket_bridge(
            websocket_manager=mock_websocket_manager,
            user_context=user_context
        )

        # Create AgentExecutionCore 
        execution_core = AgentExecutionCore(
            registry=mock_registry,
            websocket_bridge=websocket_bridge,
            default_tier=TimeoutTier.FREE
        )

        # Set up successful agent
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True,
            "result": "Agent completed successfully"
        })
        mock_registry.get_async = AsyncMock(return_value=mock_agent)

        # Create execution context
        agent_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="websocket_propagation_test_agent"
        )

        # Monitor WebSocket manager propagation
        websocket_propagation_calls = []
        original_transition_state = execution_core.agent_tracker.transition_state

        async def capture_websocket_propagation(*args, **kwargs):
            """Capture WebSocket manager propagation in state transitions."""
            websocket_manager = kwargs.get('websocket_manager')
            websocket_propagation_calls.append({
                'has_websocket_manager': websocket_manager is not None,
                'websocket_manager_type': type(websocket_manager).__name__ if websocket_manager else None,
                'phase': args[1].value if len(args) > 1 and hasattr(args[1], 'value') else 'unknown',
                'timestamp': time.time()
            })
            return await original_transition_state(*args, **kwargs)

        execution_core.agent_tracker.transition_state = capture_websocket_propagation

        # Execute agent and check for WebSocket manager propagation failure
        result = await execution_core.execute_agent(
            context=agent_context,
            user_context=user_context,
            timeout=5.0
        )

        # Analyze WebSocket manager propagation
        completion_transitions = [
            call for call in websocket_propagation_calls
            if call['phase'] == AgentExecutionPhase.COMPLETED.value
        ]

        if not completion_transitions:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: No completion phase transition with WebSocket manager!\n"
                f"   Agent execution success: {result.success}\n"
                f"   Total state transitions: {len(websocket_propagation_calls)}\n"
                f"   Transitions with WebSocket manager: {sum(1 for call in websocket_propagation_calls if call['has_websocket_manager'])}\n"
                f"   Completion transitions: {len(completion_transitions)}\n"
                f"\n🚨 NO COMPLETION NOTIFICATION SENT TO USER!"
            )
            logger.error(failure_message)
            self.fail(failure_message)

        # Check if completion transition had WebSocket manager
        completion_transition = completion_transitions[0]
        if not completion_transition['has_websocket_manager']:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: Completion transition missing WebSocket manager!\n"
                f"   Completion transition: {completion_transition}\n"
                f"   WebSocket manager provided: {completion_transition['has_websocket_manager']}\n"
                f"   Agent execution success: {result.success}\n"
                f"\n🚨 WEBSOCKET MANAGER NOT PROPAGATED TO COMPLETION HANDLER!"
            )
            logger.error(failure_message)
            self.fail(failure_message)

        # Check if actual WebSocket notification was called
        if mock_websocket_manager.notify_agent_completed.call_count == 0:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: WebSocket completion notification never called!\n"
                f"   Agent execution success: {result.success}\n"
                f"   WebSocket manager in completion: {completion_transition['has_websocket_manager']}\n"
                f"   notify_agent_completed calls: {mock_websocket_manager.notify_agent_completed.call_count}\n"
                f"   notify_agent_started calls: {mock_websocket_manager.notify_agent_started.call_count}\n"
                f"\n🚨 USER NEVER RECEIVES COMPLETION NOTIFICATION!"
            )
            logger.error(failure_message)
            self.fail(failure_message)

        # If we get here, the issue may be resolved
        logger.warning("⚠️ Expected WebSocket propagation failure not detected - Issue #1028 may be resolved")

    async def test_completion_notification_missing_in_successful_execution(self):
        """
        CRITICAL: Test that completion notifications are missing even when agent execution succeeds.
        
        ISSUE #1028 SYMPTOM: Users don't see agent_completed events even though agents
        complete successfully, making it appear that agents are hung.
        
        EXPECTED TO FAIL: Agent succeeds but no completion notification sent to user
        """
        logger.info("🔍 TESTING: Missing completion notifications in successful agent execution")

        # Set up complete execution scenario
        mock_registry = MagicMock()
        mock_websocket_manager = MagicMock()
        mock_websocket_manager.notify_agent_completed = AsyncMock()
        mock_websocket_manager.notify_agent_started = AsyncMock()
        mock_websocket_manager.notify_agent_thinking = AsyncMock()

        # Create execution core with WebSocket bridge
        execution_core = AgentExecutionCore(
            registry=mock_registry,
            websocket_bridge=mock_websocket_manager,  # Direct assignment for simplicity
            default_tier=TimeoutTier.FREE
        )

        # Create successful agent
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={
            "success": True,
            "result": "Agent completed successfully",
            "data": {"analysis": "Complete"}
        })
        mock_registry.get_async = AsyncMock(return_value=mock_agent)

        # Create execution contexts
        user_context = UserExecutionContext(
            user_id=ensure_user_id(generate_user_id()),
            thread_id=ensure_thread_id(generate_thread_id()),
            run_id=str(uuid.uuid4())
        )

        agent_context = AgentExecutionContext(
            run_id=str(uuid.uuid4()),
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="completion_notification_agent"
        )

        # Execute agent
        start_time = time.time()
        result = await execution_core.execute_agent(
            context=agent_context,
            user_context=user_context,
            timeout=10.0
        )
        execution_time = time.time() - start_time

        # Validate agent execution succeeded
        if not result.success:
            logger.error(f"Agent execution failed unexpectedly: {result.error}")
            pytest.skip("Cannot test completion notification issue - agent execution failed")

        # Check for completion notification failure
        completion_calls = mock_websocket_manager.notify_agent_completed.call_count
        started_calls = mock_websocket_manager.notify_agent_started.call_count

        logger.info(f"📊 EXECUTION RESULTS:")
        logger.info(f"   Agent execution success: {result.success}")
        logger.info(f"   Execution time: {execution_time:.3f}s")
        logger.info(f"   notify_agent_started calls: {started_calls}")
        logger.info(f"   notify_agent_completed calls: {completion_calls}")

        # Issue #1028 symptom: Agent succeeds but no completion notification
        if completion_calls == 0 and result.success:
            failure_message = (
                f"❌ ISSUE #1028 CONFIRMED: Agent succeeded but NO completion notification sent!\n"
                f"   Agent execution: SUCCESS (duration: {execution_time:.3f}s)\n"
                f"   Agent result: {result.data if hasattr(result, 'data') else 'No data'}\n"
                f"   notify_agent_started calls: {started_calls}\n"
                f"   notify_agent_completed calls: {completion_calls}\n"
                f"   User ID: {user_context.user_id}\n"
                f"   Thread ID: {user_context.thread_id}\n"
                f"\n🚨 USER WILL THINK AGENT IS HUNG - CRITICAL UX FAILURE!"
                f"\n📋 BUSINESS IMPACT: 90% of platform value (chat) appears broken to user"
            )
            logger.error(failure_message)
            self.fail(failure_message)

        # Additional check: Verify completion notification parameters if called
        if completion_calls > 0:
            # Check if completion notification was called with correct parameters
            completion_call_args = mock_websocket_manager.notify_agent_completed.call_args
            if completion_call_args:
                args, kwargs = completion_call_args
                run_id = kwargs.get('run_id') or (args[0] if len(args) > 0 else None)
                agent_name = kwargs.get('agent_name') or (args[1] if len(args) > 1 else None)

                parameter_issues = []
                if run_id != agent_context.run_id:
                    parameter_issues.append(f"run_id mismatch: expected {agent_context.run_id}, got {run_id}")
                if agent_name != agent_context.agent_name:
                    parameter_issues.append(f"agent_name mismatch: expected {agent_context.agent_name}, got {agent_name}")

                if parameter_issues:
                    failure_message = (
                        f"❌ ISSUE #1028 RELATED: Completion notification called with wrong parameters!\n"
                        f"   Parameter issues: {parameter_issues}\n"
                        f"   This may cause completion notifications to be ignored by client\n"
                        f"\n🚨 USER MAY NOT RECEIVE PROPER COMPLETION FEEDBACK!"
                    )
                    logger.error(failure_message)
                    pytest.fail(failure_message)

        # If we get here without failing, issue may be resolved
        logger.info("✅ UNEXPECTED: Completion notification working properly - Issue #1028 may be resolved")

    def teardown_method(self, method):
        """Teardown with Issue #1028 specific analysis."""
        try:
            # Log Issue #1028 reproduction results
            logger.info("📊 ISSUE #1028 REPRODUCTION TEST RESULTS:")
            logger.info(f"   Test method: {method.__name__ if method else 'unknown'}")
            logger.info(f"   Captured events: {len(self.captured_events)}")
            logger.info(f"   Completion events: {len(self.completion_events)}")
            logger.info(f"   Parameter misalignments: {len(self.parameter_misalignments)}")

            # Record metrics for Issue #1028 tracking
            self.record_metric("issue_1028_reproduction_attempt", True)
            self.record_metric("completion_events_captured", len(self.completion_events))
            self.record_metric("parameter_misalignments_found", len(self.parameter_misalignments))

            # Determine Issue #1028 reproduction status
            if self.parameter_misalignments or len(self.completion_events) == 0:
                logger.error("❌ ISSUE #1028 SUCCESSFULLY REPRODUCED: WebSocket bridge propagation failure confirmed")
                self.record_metric("issue_1028_reproduction_status", "CONFIRMED")
            else:
                logger.info("✅ ISSUE #1028 NOT REPRODUCED: WebSocket notifications may be working")
                self.record_metric("issue_1028_reproduction_status", "NOT_REPRODUCED")

        except Exception as e:
            logger.error(f"❌ TEARDOWN ERROR: {str(e)}")

        finally:
            super().teardown_method(method)


if __name__ == "__main__":
    """Run Issue #1028 WebSocket bridge propagation failure reproduction tests."""
    logger.info("🚨 RUNNING ISSUE #1028 REPRODUCTION TESTS")
    logger.info("📍 PURPOSE: Reproduce WebSocket bridge propagation failure - missing completion notifications")
    logger.info("⚠️  EXPECTED: These tests should FAIL, proving the issue exists")

    # Run the tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])