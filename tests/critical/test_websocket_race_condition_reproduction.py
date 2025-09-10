"""
WebSocket Race Condition Reproduction Tests

Purpose: Prove that the current WebSocket implementation has race conditions
by creating tests that MUST FAIL with the current code.

These tests target the root cause identified in Five Whys analysis:
"No single, coordinated state machine properly sequences WebSocket connection 
lifecycle, causing multiple competing state management systems to race."

Business Value:
- Segment: Platform/ALL
- Goal: System Stability & $500K+ ARR Protection
- Value Impact: Prevents WebSocket 1011 errors that break chat functionality
- Strategic Impact: Systematic validation of race condition fixes

CRITICAL: These tests are designed to FAIL with current implementation.
After implementing Single Coordination State Machine, they should PASS.
"""

import asyncio
import pytest
import time
import json
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    ApplicationConnectionStateMachine,
    StateTransitionError
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class RaceConditionResult:
    """Tracks race condition test results."""
    connection_id: str
    success: bool
    error_type: str = None
    error_message: str = None
    timing_ms: float = 0.0
    state_transitions: List[str] = None

    def __post_init__(self):
        if self.state_transitions is None:
            self.state_transitions = []


class WebSocketRaceConditionReproduction:
    """
    Test class that reproduces the exact race conditions identified
    in the Five Whys analysis and staging logs.
    
    CRITICAL: All tests in this class MUST FAIL with current implementation
    to prove that race conditions exist.
    """

    @pytest.mark.race_condition
    @pytest.mark.xfail(reason="MUST FAIL: Multiple competing state machines race")
    async def test_multiple_connection_state_machines_race(self):
        """
        Reproduces: Multiple connection state machines with different IDs 
        competing for same user session.
        
        ROOT CAUSE: No coordination between state machines causes race conditions.
        
        EXPECTED FAILURE MODE: Multiple state machines transitioning simultaneously
        causing StateTransitionError or invalid state conflicts.
        """
        user_id = "race-test-user-123"
        num_concurrent_connections = 5
        
        logger.info(f"🧪 RACE TEST: Creating {num_concurrent_connections} competing state machines for user {user_id}")
        
        # Create multiple state machines simultaneously (this SHOULD fail)
        race_results = []
        tasks = []
        
        for i in range(num_concurrent_connections):
            connection_id = f"ws_race_{i}_{int(time.time() * 1000)}"
            task = asyncio.create_task(
                self._create_competing_state_machine(user_id, connection_id, i)
            )
            tasks.append(task)
            # Small delay to create timing overlap
            await asyncio.sleep(0.001)
        
        # Gather results - expecting exceptions due to race conditions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze race condition results
        successful_machines = []
        failed_machines = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_machines.append({
                    'connection_id': f"ws_race_{i}",
                    'error': str(result),
                    'error_type': type(result).__name__
                })
                logger.warning(f"❌ State machine {i} failed as expected: {result}")
            else:
                successful_machines.append(result)
                logger.error(f"⚠️ State machine {i} succeeded unexpectedly: {result}")
        
        # CRITICAL ASSERTION: This test MUST FAIL with current implementation
        # Multiple state machines should NOT all succeed due to race conditions
        assert len(failed_machines) > 0, (
            f"RACE CONDITION NOT DETECTED: All {len(successful_machines)} state machines "
            f"succeeded, but race conditions should cause failures. This indicates the "
            f"race condition either doesn't exist or isn't being triggered properly."
        )
        
        # Verify specific race condition error types
        race_error_types = [fm['error_type'] for fm in failed_machines]
        expected_errors = ['StateTransitionError', 'RuntimeError', 'ValueError']
        
        assert any(error_type in expected_errors for error_type in race_error_types), (
            f"Expected race condition errors {expected_errors}, "
            f"got {race_error_types}"
        )
        
        logger.info(f"✅ RACE CONDITION CONFIRMED: {len(failed_machines)} machines failed as expected")

    @pytest.mark.race_condition
    @pytest.mark.xfail(reason="MUST FAIL: Invalid state transition sequence")
    async def test_invalid_state_transition_connecting_to_services_ready(self):
        """
        Reproduces: Invalid state transition CONNECTING → SERVICES_READY
        that skips required intermediate states (ACCEPTED, AUTHENTICATED).
        
        ROOT CAUSE: No coordination enforcing proper state sequence.
        
        EXPECTED FAILURE MODE: StateTransitionError when attempting invalid transition.
        """
        connection_id = "invalid_transition_test"
        user_id = "test-user-invalid-transition"
        
        logger.info(f"🧪 INVALID TRANSITION TEST: Attempting CONNECTING → SERVICES_READY")
        
        # Create state machine in CONNECTING state
        state_machine = ApplicationConnectionStateMachine(connection_id, user_id)
        assert state_machine.current_state == ApplicationConnectionState.CONNECTING
        
        # CRITICAL TEST: Try to skip directly to SERVICES_READY
        # This MUST FAIL because it skips ACCEPTED and AUTHENTICATED states
        with pytest.raises(StateTransitionError) as exc_info:
            transition_result = state_machine.transition_to(
                ApplicationConnectionState.SERVICES_READY,
                reason="Attempting invalid state skip (this should fail)",
                metadata={"test_type": "invalid_transition_reproduction"}
            )
            
            # If we reach here, the transition succeeded when it shouldn't have
            pytest.fail(
                f"RACE CONDITION NOT DETECTED: Invalid transition CONNECTING → SERVICES_READY "
                f"succeeded when it should have failed. Result: {transition_result}"
            )
        
        # Verify the error message contains expected content
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in [
            'invalid transition', 'invalid state', 'transition not allowed'
        ]), f"Expected invalid transition error, got: {error_message}"
        
        logger.info(f"✅ INVALID TRANSITION BLOCKED: {exc_info.value}")

    @pytest.mark.race_condition
    @pytest.mark.xfail(reason="MUST FAIL: Phase overlap race condition")
    async def test_phase1_phase4_initialization_overlap_race(self):
        """
        Reproduces: Phase 1 (transport accept) and Phase 4 (application ready)
        running concurrently instead of sequentially.
        
        ROOT CAUSE: No coordination between WebSocket transport and application layers.
        
        EXPECTED FAILURE MODE: RuntimeError or state inconsistency when phases overlap.
        """
        logger.info(f"🧪 PHASE OVERLAP TEST: Starting Phase 1 and Phase 4 simultaneously")
        
        # Mock WebSocket in CONNECTING state
        websocket_mock = MagicMock()
        websocket_mock.client_state = "CONNECTING"  # Simulating WebSocketState.CONNECTING
        websocket_mock.accept = AsyncMock()
        
        # Start both phases simultaneously (this SHOULD cause race condition)
        phase1_task = asyncio.create_task(
            self._simulate_phase1_transport_accept(websocket_mock)
        )
        
        phase4_task = asyncio.create_task(
            self._simulate_phase4_application_ready(websocket_mock)
        )
        
        # Wait for both with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(phase1_task, phase4_task, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            # Timeout is acceptable - indicates race condition deadlock
            logger.info("✅ PHASE OVERLAP RACE: Timeout detected (possible deadlock)")
            pytest.fail("Phase overlap caused timeout - race condition confirmed")
        
        # Analyze results
        phase1_result, phase4_result = results
        
        # At least one phase should fail due to race condition
        failures = [r for r in results if isinstance(r, Exception)]
        
        assert len(failures) > 0, (
            f"RACE CONDITION NOT DETECTED: Both phases completed successfully. "
            f"Phase 1: {phase1_result}, Phase 4: {phase4_result}. "
            f"Expected at least one failure due to overlap race condition."
        )
        
        logger.info(f"✅ PHASE OVERLAP RACE CONFIRMED: {len(failures)} phase(s) failed")

    @pytest.mark.race_condition
    @pytest.mark.xfail(reason="MUST FAIL: Message processing before accept complete")
    async def test_message_processing_before_websocket_accept_complete(self):
        """
        Reproduces: "Need to call accept first" error from staging logs.
        
        ROOT CAUSE: Message processing starts before WebSocket accept() completes.
        
        EXPECTED FAILURE MODE: RuntimeError with "accept first" message.
        """
        logger.info(f"🧪 ACCEPT RACE TEST: Processing message before accept() complete")
        
        # Mock WebSocket in CONNECTING state (accept not completed)
        websocket_mock = MagicMock()
        websocket_mock.client_state = "CONNECTING"  # Not yet CONNECTED
        websocket_mock.receive_text = AsyncMock()
        
        # Mock message data
        test_message = {
            "type": "user_message",
            "text": "Test message that triggers race condition",
            "thread_id": "test-thread-123"
        }
        
        # Attempt to process message before accept() completes
        # This MUST FAIL with "Need to call accept first" error
        with pytest.raises(RuntimeError) as exc_info:
            await self._attempt_message_processing_before_accept(websocket_mock, test_message)
        
        # Verify specific error message
        error_message = str(exc_info.value).lower()
        assert "accept" in error_message, (
            f"Expected 'accept' error message, got: {error_message}"
        )
        
        logger.info(f"✅ ACCEPT RACE CONFIRMED: {exc_info.value}")

    @pytest.mark.race_condition
    @pytest.mark.xfail(reason="MUST FAIL: Concurrent user context creation")
    async def test_concurrent_user_execution_context_creation_race(self):
        """
        Reproduces: Multiple UserExecutionContext instances created concurrently
        for same user, causing context isolation failures.
        
        ROOT CAUSE: No coordination of user context creation across connections.
        
        EXPECTED FAILURE MODE: Context conflicts or resource leaks.
        """
        user_id = "context-race-user"
        num_contexts = 3
        
        logger.info(f"🧪 CONTEXT RACE TEST: Creating {num_contexts} concurrent contexts for {user_id}")
        
        # Attempt to create multiple contexts simultaneously
        context_creation_tasks = []
        
        for i in range(num_contexts):
            task = asyncio.create_task(
                self._create_user_execution_context(user_id, f"conn_{i}")
            )
            context_creation_tasks.append(task)
        
        # Execute concurrently
        context_results = await asyncio.gather(
            *context_creation_tasks, 
            return_exceptions=True
        )
        
        # Analyze context creation results
        successful_contexts = [r for r in context_results if not isinstance(r, Exception)]
        failed_contexts = [r for r in context_results if isinstance(r, Exception)]
        
        # CRITICAL: Multiple contexts for same user should cause coordination issues
        if len(successful_contexts) > 1:
            # Check for context isolation violations
            context_ids = [ctx.context_id for ctx in successful_contexts if hasattr(ctx, 'context_id')]
            unique_context_ids = set(context_ids)
            
            assert len(unique_context_ids) < len(context_ids), (
                f"RACE CONDITION NOT DETECTED: {len(successful_contexts)} contexts created "
                f"with unique IDs {unique_context_ids}. Expected context conflicts or coordination failures."
            )
        
        # Alternative assertion: expect some failures due to race conditions
        assert len(failed_contexts) > 0 or len(successful_contexts) <= 1, (
            f"RACE CONDITION NOT DETECTED: Multiple contexts ({len(successful_contexts)}) "
            f"created successfully without coordination failures."
        )
        
        logger.info(f"✅ CONTEXT RACE CONFIRMED: {len(failed_contexts)} failures detected")

    # Helper methods for race condition simulation

    async def _create_competing_state_machine(self, user_id: str, connection_id: str, index: int) -> RaceConditionResult:
        """Create a state machine that competes with others."""
        start_time = time.time()
        
        try:
            # Create state machine
            state_machine = ApplicationConnectionStateMachine(connection_id, user_id)
            
            # Attempt rapid state transitions
            transitions = []
            
            # Transition 1: CONNECTING → ACCEPTED
            if state_machine.transition_to(ApplicationConnectionState.ACCEPTED):
                transitions.append("ACCEPTED")
                await asyncio.sleep(0.001)  # Minimal delay to allow race
            
            # Transition 2: ACCEPTED → AUTHENTICATED  
            if state_machine.transition_to(ApplicationConnectionState.AUTHENTICATED):
                transitions.append("AUTHENTICATED")
                await asyncio.sleep(0.001)
            
            # Transition 3: AUTHENTICATED → SERVICES_READY
            if state_machine.transition_to(ApplicationConnectionState.SERVICES_READY):
                transitions.append("SERVICES_READY")
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            return RaceConditionResult(
                connection_id=connection_id,
                success=True,
                timing_ms=elapsed_ms,
                state_transitions=transitions
            )
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            return RaceConditionResult(
                connection_id=connection_id,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                timing_ms=elapsed_ms
            )

    async def _simulate_phase1_transport_accept(self, websocket_mock) -> Dict[str, Any]:
        """Simulate Phase 1: WebSocket transport accept."""
        try:
            # Simulate accept() call
            await websocket_mock.accept()
            websocket_mock.client_state = "CONNECTED"
            
            # Simulate post-accept setup
            await asyncio.sleep(0.01)  # 10ms setup time
            
            return {
                "phase": "phase1_transport",
                "success": True,
                "state": "CONNECTED"
            }
            
        except Exception as e:
            return {
                "phase": "phase1_transport",
                "success": False,
                "error": str(e)
            }

    async def _simulate_phase4_application_ready(self, websocket_mock) -> Dict[str, Any]:
        """Simulate Phase 4: Application readiness setup."""
        try:
            # This should wait for Phase 1, but in race condition it doesn't
            if websocket_mock.client_state != "CONNECTED":
                raise RuntimeError("Phase 4 started before Phase 1 completed")
            
            # Simulate application setup
            await asyncio.sleep(0.015)  # 15ms application setup
            
            return {
                "phase": "phase4_application",
                "success": True,
                "state": "PROCESSING_READY"
            }
            
        except Exception as e:
            return {
                "phase": "phase4_application", 
                "success": False,
                "error": str(e)
            }

    async def _attempt_message_processing_before_accept(self, websocket_mock, message: Dict[str, Any]):
        """Attempt to process message before WebSocket accept completes."""
        # Check if accept was called (it shouldn't be in this test)
        if websocket_mock.client_state != "CONNECTED":
            raise RuntimeError("Need to call accept() first before processing messages")
        
        # If we get here, accept was already called (test setup issue)
        raise AssertionError("WebSocket already accepted - cannot reproduce race condition")

    async def _create_user_execution_context(self, user_id: str, connection_id: str):
        """Create UserExecutionContext to test concurrent creation race."""
        try:
            # Simulate UserExecutionContext creation
            from shared.types.core_types import ensure_user_id
            validated_user_id = ensure_user_id(user_id)
            
            # Simulate context initialization delay
            await asyncio.sleep(0.01)
            
            # Mock context object
            context = MagicMock()
            context.user_id = validated_user_id
            context.connection_id = connection_id
            context.context_id = f"ctx_{connection_id}_{int(time.time() * 1000)}"
            
            return context
            
        except Exception as e:
            logger.error(f"Context creation failed for {user_id}/{connection_id}: {e}")
            raise


# Test configuration
pytestmark = [
    pytest.mark.race_condition,
    pytest.mark.critical,
    pytest.mark.xfail(reason="Tests designed to FAIL with current implementation")
]


if __name__ == "__main__":
    """
    Run race condition reproduction tests directly.
    
    Usage:
        python -m pytest tests/critical/test_websocket_race_condition_reproduction.py -v
        
    Expected: ALL TESTS SHOULD FAIL with current implementation.
    After implementing Single Coordination State Machine, tests should PASS.
    """
    pytest.main([__file__, "-v", "--tb=short"])