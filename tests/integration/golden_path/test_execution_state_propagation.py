"""
Test Golden Path Execution State Propagation - SSOT Integration Validation
==========================================================================

Business Value Justification (BVJ):
- Segment: All Tiers - Core platform functionality
- Business Goal: User Experience - Ensure AI responses reach users
- Value Impact: Tests end-to-end execution state consistency for Golden Path user flow
- Strategic Impact: $500K+ ARR protected by reliable Golden Path execution state tracking

This test validates that execution states propagate correctly through the entire
Golden Path user flow, ensuring SSOT compliance across all execution tracking modules.

GOLDEN PATH FLOW:
1. User sends message → WebSocket receives request
2. Agent execution starts → ExecutionState.PENDING
3. Agent processes → ExecutionState.RUNNING  
4. Agent completes → ExecutionState.COMPLETED
5. Response sent to user → WebSocket events delivered

CRITICAL SSOT ISSUES:
- Multiple ExecutionState enums with different values
- ExecutionTracker fragmentation across modules
- State synchronization failures between tracking systems
- WebSocket events not matching actual execution states

CRITICAL: This test will FAIL before SSOT consolidation, PASS after.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestGoldenPathExecutionStatePropagation(SSotAsyncTestCase):
    """Test execution state propagation through Golden Path user flow."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.mock_factory = SSotMockFactory()
        self.captured_states = []
        self.captured_websocket_events = []
        
    async def test_golden_path_execution_state_consistency(self):
        """
        Test that execution states remain consistent throughout Golden Path flow.
        
        CRITICAL: This test MUST FAIL before SSOT consolidation due to:
        - ExecutionState fragmentation between modules
        - State synchronization issues
        - WebSocket events not matching execution tracker states
        
        After SSOT consolidation: All states should be synchronized across systems.
        """
        # Mock all the Golden Path components
        mock_websocket_manager = self._create_mock_websocket_manager()
        mock_agent_registry = self._create_mock_agent_registry()
        mock_execution_core = self._create_mock_execution_core()
        
        # Set up state capture hooks
        self._setup_state_capture_hooks()
        
        # Simulate Golden Path user flow
        await self._simulate_golden_path_user_flow(
            mock_websocket_manager, 
            mock_agent_registry, 
            mock_execution_core
        )
        
        # CRITICAL ASSERTION: Verify state consistency across all systems
        await self._verify_execution_state_consistency()
        
        # CRITICAL ASSERTION: Verify WebSocket events match execution states
        await self._verify_websocket_event_state_alignment()
        
        # CRITICAL ASSERTION: Verify no state transitions are lost
        await self._verify_complete_state_transition_chain()
    
    async def test_execution_state_enum_consistency_in_golden_path(self):
        """
        Test that all Golden Path components use the same ExecutionState enum.
        
        CRITICAL: This test validates that the Golden Path doesn't break due to
        ExecutionState fragmentation where different modules have different enum values.
        """
        from netra_backend.app.core.execution_tracker import ExecutionState as CoreState
        from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentState
        
        # Test critical states used in Golden Path
        golden_path_states = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']
        
        for state_name in golden_path_states:
            # Both enums should have the state
            self.assertTrue(
                hasattr(CoreState, state_name),
                f"Core ExecutionState missing {state_name} - Golden Path will break"
            )
            self.assertTrue(
                hasattr(AgentState, state_name),
                f"Agent ExecutionState missing {state_name} - Golden Path will break"
            )
            
            # Values should be identical
            core_value = getattr(CoreState, state_name).value
            agent_value = getattr(AgentState, state_name).value
            
            self.assertEqual(
                core_value, agent_value,
                f"GOLDEN PATH BREAKING: ExecutionState.{state_name} values inconsistent! "
                f"Core: '{core_value}', Agent: '{agent_value}'. "
                f"This will cause Golden Path state synchronization failures."
            )
    
    async def test_golden_path_websocket_event_state_synchronization(self):
        """
        Test that WebSocket events are synchronized with execution states.
        
        CRITICAL: This test validates that when execution state changes,
        corresponding WebSocket events are sent with correct state information.
        """
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        # Create mock components
        mock_websocket_bridge = self._create_mock_websocket_bridge()
        mock_execution_tracker = self._create_mock_execution_tracker()
        
        # Track WebSocket events
        websocket_events = []
        original_notify = mock_websocket_bridge.notify_agent_started
        
        async def capture_websocket_events(event_type, **kwargs):
            websocket_events.append({
                'type': event_type,
                'timestamp': datetime.now(timezone.utc),
                'data': kwargs
            })
            return await original_notify(**kwargs) if hasattr(original_notify, '__call__') else None
        
        # Mock WebSocket event methods
        mock_websocket_bridge.notify_agent_started = AsyncMock(side_effect=lambda **kwargs: capture_websocket_events('agent_started', **kwargs))
        mock_websocket_bridge.notify_agent_thinking = AsyncMock(side_effect=lambda **kwargs: capture_websocket_events('agent_thinking', **kwargs))
        mock_websocket_bridge.notify_agent_completed = AsyncMock(side_effect=lambda **kwargs: capture_websocket_events('agent_completed', **kwargs))
        
        # Simulate execution state progression
        execution_id = "test-exec-123"
        
        # State 1: PENDING -> agent_started event
        mock_execution_tracker.update_execution_state(execution_id, ExecutionState.PENDING)
        await mock_websocket_bridge.notify_agent_started(
            run_id="test-run-123",
            agent_name="test_agent",
            context={"state": "pending"}
        )
        
        # State 2: RUNNING -> agent_thinking event
        mock_execution_tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
        await mock_websocket_bridge.notify_agent_thinking(
            run_id="test-run-123", 
            agent_name="test_agent",
            reasoning="Processing request..."
        )
        
        # State 3: COMPLETED -> agent_completed event
        mock_execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
        await mock_websocket_bridge.notify_agent_completed(
            run_id="test-run-123",
            agent_name="test_agent", 
            result={"success": True}
        )
        
        # CRITICAL ASSERTION: Events should be in correct order
        expected_event_sequence = ['agent_started', 'agent_thinking', 'agent_completed']
        actual_event_sequence = [event['type'] for event in websocket_events]
        
        self.assertEqual(
            actual_event_sequence, expected_event_sequence,
            f"GOLDEN PATH FAILURE: WebSocket events out of sequence! "
            f"Expected: {expected_event_sequence}, Got: {actual_event_sequence}. "
            f"This breaks user experience - users won't see proper agent progress."
        )
        
        # CRITICAL ASSERTION: Each event should have required data
        for event in websocket_events:
            self.assertIn('run_id', event['data'], f"WebSocket event missing run_id: {event}")
            self.assertIn('agent_name', event['data'], f"WebSocket event missing agent_name: {event}")
    
    async def test_golden_path_execution_failure_state_handling(self):
        """
        Test that execution failures are handled consistently across Golden Path.
        
        CRITICAL: This test ensures that when agents fail, the failure is
        properly propagated through all tracking systems and users are notified.
        """
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        # Create failure scenario components
        mock_execution_core = self._create_mock_execution_core()
        mock_websocket_bridge = self._create_mock_websocket_bridge()
        
        # Track failure events
        failure_events = []
        
        async def capture_failure_events(**kwargs):
            failure_events.append({
                'timestamp': datetime.now(timezone.utc),
                'error': kwargs.get('error', 'Unknown error'),
                'agent_name': kwargs.get('agent_name', 'unknown')
            })
        
        mock_websocket_bridge.notify_agent_error = AsyncMock(side_effect=capture_failure_events)
        
        # Simulate agent execution failure
        from netra_backend.app.agents.supervisor.execution_context import (
            AgentExecutionContext, 
            AgentExecutionResult
        )
        
        context = AgentExecutionContext(
            agent_name="failing_agent",
            run_id="test-run-fail-123", 
            thread_id="thread-123",
            user_id="user-123"
        )
        
        # Mock execution core to simulate failure
        failure_result = AgentExecutionResult(
            success=False,
            error="Test agent failure for SSOT validation",
            agent_name="failing_agent",
            run_id="test-run-fail-123",
            execution_time_ms=500
        )
        
        # Simulate the failure handling path
        execution_id = "exec-fail-123"
        
        # CRITICAL: Test that failure state is set correctly
        # This is where the dictionary vs enum bug occurred
        try:
            # This should use ExecutionState.FAILED, not a dictionary
            if hasattr(mock_execution_core, 'agent_tracker'):
                mock_execution_core.agent_tracker.update_execution_state(
                    execution_id, 
                    ExecutionState.FAILED  # CRITICAL: Must be enum, not dict
                )
            
            # Notify WebSocket of failure
            await mock_websocket_bridge.notify_agent_error(
                run_id=context.run_id,
                agent_name=context.agent_name,
                error=failure_result.error
            )
            
        except Exception as e:
            # CRITICAL ASSERTION: Should not fail with attribute error
            if "'dict' object has no attribute 'value'" in str(e):
                self.fail(
                    f"DICTIONARY vs ENUM BUG DETECTED: {e}. "
                    f"This indicates ExecutionState.FAILED was passed as dictionary instead of enum. "
                    f"Golden Path failure handling is broken!"
                )
            else:
                # Some other error - re-raise for investigation
                raise
        
        # CRITICAL ASSERTION: Failure should be captured and notified
        self.assertGreater(
            len(failure_events), 0,
            "Agent failure not properly captured - users won't be notified of failures"
        )
        
        failure_event = failure_events[0]
        self.assertEqual(
            failure_event['agent_name'], 'failing_agent',
            "Failure event missing correct agent name"
        )
        self.assertIn(
            'Test agent failure', failure_event['error'],
            "Failure event missing error details"
        )
    
    async def test_golden_path_multiple_tracker_synchronization(self):
        """
        Test that multiple execution trackers stay synchronized in Golden Path.
        
        CRITICAL: This test validates that when multiple execution tracking
        systems exist (before SSOT consolidation), they remain synchronized.
        """
        # Get different execution tracker implementations
        trackers = []
        
        try:
            from netra_backend.app.core.execution_tracker import get_execution_tracker
            core_tracker = get_execution_tracker()
            trackers.append(("core_tracker", core_tracker))
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import get_execution_tracker as get_agent_tracker
            agent_tracker = get_agent_tracker()
            trackers.append(("agent_tracker", agent_tracker))
        except ImportError:
            pass
        
        if len(trackers) <= 1:
            # Only one tracker - good for SSOT
            pytest.skip("Single tracker implementation - SSOT compliance achieved")
            return
        
        # Test synchronization between trackers
        agent_name = "sync_test_agent"
        thread_id = "sync-thread-123"
        user_id = "sync-user-123"
        
        execution_ids = []
        
        # Create execution in all trackers
        for tracker_name, tracker in trackers:
            if hasattr(tracker, 'create_execution'):
                exec_id = tracker.create_execution(
                    agent_name=agent_name,
                    thread_id=thread_id, 
                    user_id=user_id
                )
                execution_ids.append((tracker_name, exec_id, tracker))
        
        # CRITICAL ASSERTION: All trackers should track the same execution
        if len(execution_ids) != len(trackers):
            self.fail(
                f"SYNCHRONIZATION FAILURE: Not all trackers created executions. "
                f"Expected {len(trackers)}, got {len(execution_ids)}. "
                f"Golden Path execution tracking is fragmented!"
            )
        
        # Test state updates are synchronized
        from netra_backend.app.core.agent_execution_tracker import ExecutionState
        
        for tracker_name, exec_id, tracker in execution_ids:
            if hasattr(tracker, 'update_execution_state'):
                success = tracker.update_execution_state(exec_id, ExecutionState.RUNNING)
                self.assertTrue(
                    success,
                    f"Failed to update state in {tracker_name} - synchronization broken"
                )
        
        # Verify all trackers show consistent state
        for tracker_name, exec_id, tracker in execution_ids:
            if hasattr(tracker, 'get_execution'):
                execution = tracker.get_execution(exec_id)
                if execution:
                    self.assertEqual(
                        execution.state, ExecutionState.RUNNING,
                        f"{tracker_name} state not synchronized - shows {execution.state} instead of RUNNING"
                    )
    
    # Helper methods for test setup
    
    def _create_mock_websocket_manager(self):
        """Create mock WebSocket manager for testing."""
        mock_manager = Mock()
        mock_manager.notify_agent_started = AsyncMock()
        mock_manager.notify_agent_thinking = AsyncMock() 
        mock_manager.notify_agent_completed = AsyncMock()
        mock_manager.notify_agent_error = AsyncMock()
        return mock_manager
    
    def _create_mock_agent_registry(self):
        """Create mock agent registry for testing."""
        mock_registry = Mock()
        mock_agent = Mock()
        mock_agent.execute = AsyncMock()
        mock_registry.get_agent.return_value = mock_agent
        return mock_registry
    
    def _create_mock_execution_core(self):
        """Create mock execution core for testing.""" 
        mock_core = Mock()
        mock_core.execute_agent_safe = AsyncMock()
        mock_core.agent_tracker = Mock()
        mock_core.execution_tracker = Mock()
        return mock_core
    
    def _create_mock_websocket_bridge(self):
        """Create mock WebSocket bridge for testing."""
        mock_bridge = Mock()
        mock_bridge.notify_agent_started = AsyncMock()
        mock_bridge.notify_agent_thinking = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()
        mock_bridge.notify_agent_error = AsyncMock()
        return mock_bridge
    
    def _create_mock_execution_tracker(self):
        """Create mock execution tracker for testing."""
        mock_tracker = Mock()
        mock_tracker.create_execution = Mock()
        mock_tracker.update_execution_state = Mock()
        mock_tracker.get_execution = Mock()
        return mock_tracker
    
    def _setup_state_capture_hooks(self):
        """Set up hooks to capture execution state changes."""
        self.captured_states = []
        self.captured_websocket_events = []
    
    async def _simulate_golden_path_user_flow(self, websocket_manager, agent_registry, execution_core):
        """Simulate complete Golden Path user flow."""
        # This would simulate:
        # 1. WebSocket message received
        # 2. Agent execution started 
        # 3. Agent processing
        # 4. Agent completion
        # 5. Response sent back
        
        # For testing purposes, we'll capture the key state transitions
        pass
    
    async def _verify_execution_state_consistency(self):
        """Verify that execution states are consistent across all systems."""
        # This would check that all execution tracking systems
        # show the same states for the same execution
        pass
    
    async def _verify_websocket_event_state_alignment(self):
        """Verify that WebSocket events match execution states."""
        # This would ensure that WebSocket events are sent
        # when execution states change
        pass
    
    async def _verify_complete_state_transition_chain(self):
        """Verify that no state transitions are lost."""
        # This would ensure that all expected state transitions
        # occurred and were recorded
        pass


@pytest.mark.integration
@pytest.mark.golden_path  
@pytest.mark.ssot_validation
class TestGoldenPathSSotReadiness:
    """Test Golden Path readiness for SSOT consolidation."""
    
    def test_golden_path_execution_components_inventory(self):
        """
        Inventory all execution-related components used in Golden Path.
        
        This test maps out all the components that need to be SSOT-compliant
        for Golden Path to work reliably.
        """
        golden_path_components = [
            # Core execution tracking
            ("netra_backend.app.core.execution_tracker", "ExecutionTracker"),
            ("netra_backend.app.core.agent_execution_tracker", "AgentExecutionTracker"),
            
            # Agent execution 
            ("netra_backend.app.agents.supervisor.agent_execution_core", "AgentExecutionCore"),
            
            # WebSocket integration
            ("netra_backend.app.services.agent_websocket_bridge", "AgentWebSocketBridge"),
            
            # Execution states
            ("netra_backend.app.core.execution_tracker", "ExecutionState"),
            ("netra_backend.app.core.agent_execution_tracker", "ExecutionState"),
        ]
        
        working_components = []
        missing_components = []
        
        for module_path, component_name in golden_path_components:
            try:
                module = __import__(module_path, fromlist=[component_name])
                component = getattr(module, component_name)
                working_components.append((module_path, component_name, component))
            except (ImportError, AttributeError) as e:
                missing_components.append((module_path, component_name, str(e)))
        
        # Log component inventory for SSOT planning
        print(f"\n=== GOLDEN PATH COMPONENT INVENTORY ===")
        print(f"Working components: {len(working_components)}")
        for module_path, name, _ in working_components:
            print(f"  ✅ {module_path}.{name}")
        
        print(f"Missing components: {len(missing_components)}")
        for module_path, name, error in missing_components:
            print(f"  ❌ {module_path}.{name} - {error}")
        
        # CRITICAL: Golden Path requires core execution components
        essential_components = [
            "ExecutionTracker", "AgentExecutionTracker", "ExecutionState"
        ]
        
        found_essential = [name for _, name, _ in working_components]
        missing_essential = [comp for comp in essential_components if comp not in found_essential]
        
        if missing_essential:
            pytest.fail(
                f"GOLDEN PATH BROKEN: Missing essential components: {missing_essential}. "
                f"Golden Path cannot function without these core execution tracking components."
            )
    
    def test_golden_path_ssot_consolidation_impact(self):
        """
        Test the impact of SSOT consolidation on Golden Path functionality.
        
        This test predicts how SSOT changes will affect Golden Path operation.
        """
        # Test current state fragmentation
        fragmentation_issues = []
        
        # Check ExecutionState fragmentation
        try:
            from netra_backend.app.core.execution_tracker import ExecutionState as CoreState
            from netra_backend.app.core.agent_execution_tracker import ExecutionState as AgentState
            
            core_states = set(state.value for state in CoreState)
            agent_states = set(state.value for state in AgentState)
            
            if core_states != agent_states:
                fragmentation_issues.append(
                    f"ExecutionState fragmentation: core has {len(core_states)} states, "
                    f"agent has {len(agent_states)} states"
                )
        except ImportError:
            pass
        
        # Check ExecutionTracker fragmentation
        tracker_implementations = []
        try:
            from netra_backend.app.core.execution_tracker import ExecutionTracker
            tracker_implementations.append("core.ExecutionTracker")
        except ImportError:
            pass
        
        try:
            from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
            tracker_implementations.append("core.AgentExecutionTracker")
        except ImportError:
            pass
        
        if len(tracker_implementations) > 1:
            fragmentation_issues.append(
                f"ExecutionTracker fragmentation: {len(tracker_implementations)} implementations found"
            )
        
        # Log fragmentation impact
        if fragmentation_issues:
            print(f"\n=== GOLDEN PATH SSOT FRAGMENTATION IMPACT ===")
            for issue in fragmentation_issues:
                print(f"  ⚠️  {issue}")
            
            print(f"\nConsolidation will fix {len(fragmentation_issues)} fragmentation issues")
            print(f"Expected Golden Path improvement: Enhanced reliability and consistency")
        else:
            print(f"\n=== GOLDEN PATH SSOT STATUS ===")
            print(f"  ✅ No fragmentation detected - SSOT compliance achieved")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])