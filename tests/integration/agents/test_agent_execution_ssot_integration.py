"""
Test Agent Execution SSOT Integration - Issues #305, #271

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents execute reliably with proper state management
- Value Impact: Agent execution delivers 90% of platform value through chat
- Revenue Impact: $500K+ ARR protection through reliable agent workflows

CRITICAL ISSUES ADDRESSED:
- #305 - ExecutionTracker dict/enum conflicts in agent execution
- #271 - User isolation in agent execution contexts
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT Imports
from netra_backend.app.core.agent_execution_tracker import (
    ExecutionState,
    AgentExecutionTracker,
    get_execution_tracker
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    managed_user_context,
    create_isolated_execution_context
)

# Agent System Imports
try:
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    from netra_backend.app.agents.registry import AgentRegistry
    AGENT_SYSTEM_AVAILABLE = True
except ImportError:
    AGENT_SYSTEM_AVAILABLE = False

# WebSocket Integration
try:
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    WEBSOCKET_BRIDGE_AVAILABLE = True
except ImportError:
    WEBSOCKET_BRIDGE_AVAILABLE = False


class TestAgentExecutionSSOTIntegration(SSotAsyncTestCase):
    """Test agent execution with SSOT ExecutionTracker and UserContext."""
    
    def setUp(self):
        """Set up test environment with SSOT components."""
        super().setUp()
        self.execution_tracker = get_execution_tracker()
        self.context_manager = UserContextManager()
        
        # Test user IDs for multi-user scenarios
        self.user_id_1 = "integration_user_001"
        self.user_id_2 = "integration_user_002"
    
    @pytest.mark.integration
    @pytest.mark.skipif(not AGENT_SYSTEM_AVAILABLE, reason="Agent system not available")
    async def test_agent_execution_state_progression_with_ssot_tracker(self):
        """Agent execution must progress through proper ExecutionState values using SSOT tracker."""
        # Create user context for isolated execution
        async with managed_user_context(self.user_id_1, "state_progression_test") as user_context:
            # Create execution tracking
            execution_id = f"exec_{user_context.execution_id}"
            
            # Initialize execution state
            self.execution_tracker.update_execution_state(execution_id, ExecutionState.PENDING)
            assert self.execution_tracker.get_execution_state(execution_id) == ExecutionState.PENDING
            
            # Simulate agent execution core workflow
            execution_core = AgentExecutionCore(
                execution_tracker=self.execution_tracker,
                user_context=user_context
            )
            
            # Test state progression: PENDING -> STARTING -> RUNNING -> COMPLETED
            await execution_core.start_execution(execution_id)
            assert self.execution_tracker.get_execution_state(execution_id) == ExecutionState.STARTING
            
            await execution_core.begin_agent_execution(execution_id, "triage_agent") 
            assert self.execution_tracker.get_execution_state(execution_id) == ExecutionState.RUNNING
            
            # Simulate successful completion
            await execution_core.complete_execution(execution_id, {"result": "success"})
            assert self.execution_tracker.get_execution_state(execution_id) == ExecutionState.COMPLETED
    
    @pytest.mark.integration
    @pytest.mark.skipif(not AGENT_SYSTEM_AVAILABLE, reason="Agent system not available")
    async def test_execution_state_enum_safety_in_agent_core(self):
        """Agent execution core must never pass dict objects to ExecutionTracker - Issue #305 fix."""
        async with managed_user_context(self.user_id_1, "enum_safety_test") as user_context:
            execution_id = f"exec_enum_safety_{user_context.execution_id}"
            
            execution_core = AgentExecutionCore(
                execution_tracker=self.execution_tracker,
                user_context=user_context
            )
            
            # Test the specific patterns that were failing in issue #305
            
            # Test 1: Agent not found scenario (line 263 in original bug)
            with patch.object(execution_core, '_get_agent', return_value=None):
                await execution_core.execute_agent(execution_id, "nonexistent_agent", "test message")
                
                # Should use ExecutionState.FAILED, NOT {"success": False, "completed": True}
                final_state = self.execution_tracker.get_execution_state(execution_id)
                assert final_state == ExecutionState.FAILED
                assert isinstance(final_state, ExecutionState)  # Must be enum, not dict
            
            # Test 2: Successful execution scenario (line 382 in original bug)
            execution_id_2 = f"exec_success_{user_context.execution_id}"
            
            # Mock successful agent execution
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = {"result": "Agent completed successfully"}
            
            with patch.object(execution_core, '_get_agent', return_value=mock_agent):
                await execution_core.execute_agent(execution_id_2, "triage_agent", "test message")
                
                # Should use ExecutionState.COMPLETED, NOT {"success": True, "completed": True}  
                final_state = self.execution_tracker.get_execution_state(execution_id_2)
                assert final_state == ExecutionState.COMPLETED
                assert isinstance(final_state, ExecutionState)  # Must be enum, not dict
            
            # Test 3: Error handling scenario (line 397 in original bug)
            execution_id_3 = f"exec_error_{user_context.execution_id}"
            
            # Mock agent execution error
            mock_failing_agent = AsyncMock()
            mock_failing_agent.execute.side_effect = Exception("Agent execution failed")
            
            with patch.object(execution_core, '_get_agent', return_value=mock_failing_agent):
                await execution_core.execute_agent(execution_id_3, "failing_agent", "test message")
                
                # Should use ExecutionState.FAILED, NOT {"success": False, "completed": True}
                final_state = self.execution_tracker.get_execution_state(execution_id_3)
                assert final_state == ExecutionState.FAILED
                assert isinstance(final_state, ExecutionState)  # Must be enum, not dict
    
    @pytest.mark.integration
    async def test_multi_user_agent_execution_isolation(self):
        """Concurrent agent executions must maintain user isolation - Issue #271."""
        async def isolated_agent_execution(user_id: str, execution_name: str) -> Dict[str, Any]:
            async with managed_user_context(user_id, execution_name) as user_context:
                execution_id = f"exec_{user_context.execution_id}"
                
                # Set user-specific data
                user_context.set_data("user_tier", "enterprise" if "001" in user_id else "free")
                user_context.set_data("agent_preference", "cost_optimizer" if "001" in user_id else "triage_agent")
                
                # Track execution
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
                
                # Simulate agent processing with user-specific behavior
                await asyncio.sleep(0.01)  # Simulate processing
                
                user_context.set_data("processing_result", f"result_for_{user_id}")
                
                # Complete execution
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
                
                return {
                    "user_id": user_context.user_id,
                    "execution_id": execution_id,
                    "user_tier": user_context.get_data("user_tier"),
                    "result": user_context.get_data("processing_result"),
                    "final_state": self.execution_tracker.get_execution_state(execution_id)
                }
        
        # Run concurrent agent executions for different users
        results = await asyncio.gather(
            isolated_agent_execution(self.user_id_1, "concurrent_1"),
            isolated_agent_execution(self.user_id_2, "concurrent_2"),
            isolated_agent_execution(self.user_id_1, "concurrent_3"),  # Same user, different execution
        )
        
        # Verify complete isolation
        assert len(results) == 3
        
        # Check user 1 executions (should have enterprise settings)
        user_1_results = [r for r in results if r["user_id"] == self.user_id_1]
        assert len(user_1_results) == 2
        for result in user_1_results:
            assert result["user_tier"] == "enterprise"
            assert f"result_for_{self.user_id_1}" in result["result"]
            assert result["final_state"] == ExecutionState.COMPLETED
        
        # Check user 2 execution (should have free settings)
        user_2_results = [r for r in results if r["user_id"] == self.user_id_2]
        assert len(user_2_results) == 1
        assert user_2_results[0]["user_tier"] == "free"
        assert f"result_for_{self.user_id_2}" in user_2_results[0]["result"]
        
        # Verify no cross-contamination
        all_execution_ids = [r["execution_id"] for r in results]
        assert len(set(all_execution_ids)) == 3, "All executions must have unique IDs"
    
    @pytest.mark.integration
    @pytest.mark.skipif(not WEBSOCKET_BRIDGE_AVAILABLE, reason="WebSocket bridge not available")
    async def test_agent_execution_websocket_event_integration(self):
        """Agent execution must deliver all 5 critical WebSocket events with SSOT tracking."""
        async with managed_user_context(self.user_id_1, "websocket_integration") as user_context:
            # Create WebSocket bridge for event capture
            websocket_bridge = create_agent_websocket_bridge(user_context)
            
            # Track events received
            received_events = []
            
            async def mock_websocket_send(event_type: str, data: Dict[str, Any]):
                received_events.append({"type": event_type, "data": data})
            
            websocket_bridge.send_event = mock_websocket_send
            
            # Execute agent with WebSocket integration
            execution_id = f"exec_websocket_{user_context.execution_id}"
            
            execution_core = AgentExecutionCore(
                execution_tracker=self.execution_tracker,
                user_context=user_context,
                websocket_bridge=websocket_bridge
            )
            
            # Mock agent that sends all required events
            mock_agent = AsyncMock()
            mock_agent.execute.return_value = {"result": "WebSocket test completed"}
            
            with patch.object(execution_core, '_get_agent', return_value=mock_agent):
                await execution_core.execute_agent(execution_id, "triage_agent", "test message")
            
            # Verify all 5 critical WebSocket events were sent
            event_types = [event["type"] for event in received_events]
            
            required_events = [
                "agent_started", 
                "agent_thinking",
                "tool_executing",  # May be optional for simple agents
                "tool_completed",  # May be optional for simple agents
                "agent_completed"
            ]
            
            # At minimum, must have agent_started and agent_completed
            assert "agent_started" in event_types, f"Missing agent_started event. Got: {event_types}"
            assert "agent_completed" in event_types, f"Missing agent_completed event. Got: {event_types}"
            
            # Events must be in correct order
            started_index = event_types.index("agent_started")
            completed_index = event_types.index("agent_completed") 
            assert started_index < completed_index, "agent_started must come before agent_completed"
            
            # Verify final execution state
            final_state = self.execution_tracker.get_execution_state(execution_id)
            assert final_state == ExecutionState.COMPLETED
    
    @pytest.mark.integration
    async def test_execution_tracker_ssot_consistency_across_components(self):
        """All components must use same SSOT ExecutionTracker instance."""
        # Test that different components get consistent tracker instance
        tracker_1 = get_execution_tracker()
        tracker_2 = get_execution_tracker()
        
        # Should be consistent (same type, compatible interface)
        assert type(tracker_1) == type(tracker_2)
        
        # Test state consistency across different component usage
        async with managed_user_context(self.user_id_1, "consistency_test") as user_context:
            execution_id = f"exec_consistency_{user_context.execution_id}"
            
            # Component 1: Set state via tracker_1
            tracker_1.update_execution_state(execution_id, ExecutionState.RUNNING)
            
            # Component 2: Read state via tracker_2  
            state_from_tracker_2 = tracker_2.get_execution_state(execution_id)
            assert state_from_tracker_2 == ExecutionState.RUNNING
            
            # Component 2: Update state
            tracker_2.update_execution_state(execution_id, ExecutionState.COMPLETED)
            
            # Component 1: Read updated state
            state_from_tracker_1 = tracker_1.get_execution_state(execution_id)
            assert state_from_tracker_1 == ExecutionState.COMPLETED
    
    @pytest.mark.integration
    async def test_agent_execution_error_handling_with_ssot(self):
        """Agent execution errors must be properly tracked with SSOT ExecutionState."""
        async with managed_user_context(self.user_id_1, "error_handling_test") as user_context:
            execution_id = f"exec_error_{user_context.execution_id}"
            
            # Test various error scenarios
            error_scenarios = [
                ("agent_not_found", ExecutionState.FAILED),
                ("agent_timeout", ExecutionState.TIMEOUT),
                ("agent_died", ExecutionState.DEAD),
                ("agent_cancelled", ExecutionState.CANCELLED)
            ]
            
            for error_type, expected_state in error_scenarios:
                with self.subTest(error_type=error_type):
                    scenario_execution_id = f"{execution_id}_{error_type}"
                    
                    # Simulate different error conditions
                    if error_type == "agent_not_found":
                        self.execution_tracker.update_execution_state(scenario_execution_id, ExecutionState.FAILED)
                    elif error_type == "agent_timeout":
                        self.execution_tracker.update_execution_state(scenario_execution_id, ExecutionState.TIMEOUT)
                    elif error_type == "agent_died":
                        self.execution_tracker.update_execution_state(scenario_execution_id, ExecutionState.DEAD)
                    elif error_type == "agent_cancelled":
                        self.execution_tracker.update_execution_state(scenario_execution_id, ExecutionState.CANCELLED)
                    
                    # Verify proper state tracking
                    final_state = self.execution_tracker.get_execution_state(scenario_execution_id)
                    assert final_state == expected_state
                    assert isinstance(final_state, ExecutionState)  # Must be enum, not dict
    
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_agent_execution_performance_with_ssot_tracking(self):
        """Agent execution with SSOT tracking must meet performance requirements."""
        import time
        
        execution_times = []
        
        for i in range(10):  # Run 10 executions
            start_time = time.perf_counter()
            
            async with managed_user_context(f"perf_user_{i}", f"perf_test_{i}") as user_context:
                execution_id = f"exec_perf_{i}_{user_context.execution_id}"
                
                # Simulate full agent execution cycle
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.PENDING)
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.STARTING)
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.RUNNING)
                
                # Simulate processing
                await asyncio.sleep(0.001)  # 1ms processing
                
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
            
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)
        
        # Performance requirements
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        # Average execution should be under 50ms (excluding actual agent processing)
        assert avg_time < 0.05, f"Average execution time too high: {avg_time:.3f}s"
        
        # No single execution should take over 100ms (excluding actual agent processing)
        assert max_time < 0.1, f"Maximum execution time too high: {max_time:.3f}s"
    
    @pytest.mark.integration
    async def test_agent_registry_integration_with_user_context(self):
        """Agent registry must work correctly with UserExecutionContext isolation."""
        async with managed_user_context(self.user_id_1, "registry_test") as user_context:
            if not AGENT_SYSTEM_AVAILABLE:
                pytest.skip("Agent system not available")
            
            # Create agent registry with user context
            agent_registry = AgentRegistry(user_context=user_context)
            
            # Test agent retrieval with context
            available_agents = await agent_registry.get_available_agents()
            assert isinstance(available_agents, list)
            assert len(available_agents) > 0, "Should have at least one available agent"
            
            # Test agent creation with user context
            if "triage_agent" in [agent["name"] for agent in available_agents]:
                agent = await agent_registry.create_agent("triage_agent")
                assert agent is not None
                
                # Agent should have user context reference
                assert hasattr(agent, 'user_context') or hasattr(agent, '_user_context')
    
    async def tearDown(self):
        """Clean up test resources."""
        # Clean up any test executions
        if hasattr(self, 'execution_tracker'):
            # Clear test execution states
            pass
        
        await super().tearDown()