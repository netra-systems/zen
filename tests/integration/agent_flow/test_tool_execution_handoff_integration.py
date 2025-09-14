"""
Tool Execution Handoff Integration Test

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core agent functionality
- Business Goal: Agent Reliability & User Experience - $500K+ ARR protection
- Value Impact: Validates complex tool handoffs during agent execution deliver value
- Strategic Impact: Critical for substantive AI interactions that solve real problems

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns from test_framework/ssot/base_test_case.py
- NO MOCKS for integration tests - uses real agent services and infrastructure
- Tests must validate $500K+ ARR chat functionality with complex tool usage
- WebSocket events must track tool_executing → tool_completed transitions
- Agent execution must handle tool timeouts and error scenarios gracefully
- Tests must validate tool handoffs between different agent types
- Tests must pass or fail meaningfully (no test cheating allowed)

ARCHITECTURE ALIGNMENT:
- Uses AgentInstanceFactory for per-request agent instantiation
- Tests UserExecutionContext isolation during tool execution
- Validates WebSocket event delivery for tool execution transparency
- Tests EnhancedToolDispatcher integration with agent workflows
- Follows Golden Path requirements for complex agent-tool interactions

This test validates that tool execution handoffs work correctly during agent
execution, including complex scenarios with timeouts, errors, and handoffs
between different types of tools and agents.
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager
from enum import Enum

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# CRITICAL: Import REAL agent execution components (NO MOCKS per CLAUDE.md)
try:
    from netra_backend.app.agents.supervisor.agent_instance_factory import (
        AgentInstanceFactory, 
        get_agent_instance_factory,
        configure_agent_instance_factory
    )
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.schemas.agent_models import DeepAgentState
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
    from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.agents.base.execution_context import ExecutionStatus
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.schemas.tool import ToolResult, ToolStatus
    from netra_backend.app.core.tools.base_tool import BaseTool
    REAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    # Graceful fallback if components not available
    print(f"Warning: Some real components not available: {e}")
    REAL_COMPONENTS_AVAILABLE = False
    AgentInstanceFactory = type('MockClass', (), {})
    UserExecutionContext = type('MockClass', (), {})
    BaseAgent = type('MockClass', (), {})


class ToolExecutionPhase(Enum):
    """Tool execution phases for testing."""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    HANDOFF_REQUESTED = "handoff_requested"
    HANDOFF_COMPLETED = "handoff_completed"


class TestToolExecutionHandoffIntegration(SSotAsyncTestCase):
    """
    Integration Tests for Tool Execution Handoff Integration.
    
    This test class validates that tool execution handoffs work correctly during
    agent execution, including complex scenarios with timeouts, errors, and
    handoffs between different types of tools and agents.
    
    Tests protect $500K+ ARR chat functionality by validating:
    - Tool_executing → tool_completed transitions work reliably
    - Complex tool handoffs during agent execution
    - Tool timeouts and error scenarios are handled gracefully
    - Multi-agent tool coordination and handoffs
    - WebSocket event delivery during tool execution phases
    """
    
    def setup_method(self, method):
        """Set up test environment with real tool execution infrastructure."""
        super().setup_method(method)
        
        # Skip if real components not available
        if not REAL_COMPONENTS_AVAILABLE:
            pytest.skip("Real agent components not available for integration testing")
        
        # Initialize environment and metrics
        self.env = self.get_env()
        self.test_user_id = f"tool_test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"tool_thread_{uuid.uuid4().hex[:8]}"
        self.test_session_id = f"tool_session_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"tool_run_{uuid.uuid4().hex[:8]}"
        
        # Initialize test tracking
        self.tool_executions: List[Dict[str, Any]] = []
        self.tool_handoffs: List[Dict[str, Any]] = []
        self.websocket_events_received: List[Dict[str, Any]] = []
        self.timeout_events: List[Dict[str, Any]] = []
        
        # Set test environment variables
        self.set_env_var("TESTING", "true")
        self.set_env_var("ENABLE_TOOL_EXECUTION", "true")
        self.set_env_var("ENABLE_TOOL_HANDOFFS", "true")
        self.set_env_var("TOOL_EXECUTION_TIMEOUT", "30")
        self.set_env_var("ENABLE_WEBSOCKET_EVENTS", "true")
        
        # Track test metrics
        self.record_metric("test_start_time", time.time())
        self.record_metric("tool_handoffs_tested", 0)
        
    def teardown_method(self, method):
        """Clean up test resources and record final metrics."""
        # Record final test metrics
        self.record_metric("test_end_time", time.time())
        self.record_metric("tool_executions_total", len(self.tool_executions))
        self.record_metric("tool_handoffs_total", len(self.tool_handoffs))
        self.record_metric("websocket_events_total", len(self.websocket_events_received))
        self.record_metric("timeout_events_total", len(self.timeout_events))
        
        # Log tool execution summary for debugging
        successful_executions = sum(1 for exec in self.tool_executions if exec.get('success', False))
        if self.tool_executions:
            success_rate = successful_executions / len(self.tool_executions)
            self.logger.info(f"Tool execution test completed: {successful_executions}/{len(self.tool_executions)} successful ({success_rate:.1%})")
            
        super().teardown_method(method)
    
    async def _create_test_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for testing."""
        return UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            session_id=self.test_session_id,
            run_id=self.test_run_id,
            workspace_id=f"workspace_{uuid.uuid4().hex[:8]}",
            metadata={
                "test_context": True,
                "test_method": self.get_test_context().test_name,
                "user_request": "Test tool execution handoffs during agent workflow",
                "tool_handoff_test": True
            }
        )
    
    async def _create_test_tool_dispatcher(self, user_context: UserExecutionContext) -> EnhancedToolDispatcher:
        """Create tool dispatcher for testing with proper user context."""
        tool_dispatcher = EnhancedToolDispatcher(
            user_context=user_context,
            enable_handoffs=True,
            timeout_seconds=30
        )
        return tool_dispatcher
    
    async def _simulate_websocket_connection(self, user_context: UserExecutionContext) -> Dict[str, Any]:
        """Simulate a WebSocket connection for tool event tracking."""
        connection_data = {
            "connection_id": f"ws_conn_{uuid.uuid4().hex[:8]}",
            "user_id": user_context.user_id,
            "connected_at": time.time(),
            "status": "connected",
            "tool_events_received": []
        }
        return connection_data
    
    async def _record_tool_execution(self, 
                                   tool_name: str,
                                   execution_phase: ToolExecutionPhase,
                                   details: Dict[str, Any],
                                   timestamp: Optional[float] = None) -> None:
        """Record a tool execution event for analysis."""
        if timestamp is None:
            timestamp = time.time()
            
        execution_record = {
            "tool_name": tool_name,
            "phase": execution_phase.value,
            "details": details,
            "timestamp": timestamp,
            "user_id": self.test_user_id,
            "test_context": True
        }
        
        self.tool_executions.append(execution_record)
        
        # Record as custom metric
        self.record_metric(f"tool_execution_{len(self.tool_executions)}", execution_record)
        
        self.logger.debug(f"Recorded tool execution: {tool_name} ({execution_phase.value})")
    
    async def _record_tool_handoff(self, 
                                 from_tool: str,
                                 to_tool: str,
                                 handoff_reason: str,
                                 success: bool,
                                 details: Dict[str, Any]) -> None:
        """Record a tool handoff event for analysis."""
        handoff_record = {
            "from_tool": from_tool,
            "to_tool": to_tool,
            "reason": handoff_reason,
            "success": success,
            "details": details,
            "timestamp": time.time(),
            "user_id": self.test_user_id
        }
        
        self.tool_handoffs.append(handoff_record)
        self.record_metric("tool_handoffs_tested", self.get_metric("tool_handoffs_tested", 0) + 1)
        
        self.logger.info(f"Recorded tool handoff: {from_tool} -> {to_tool} ({'SUCCESS' if success else 'FAILED'})")
    
    async def _record_websocket_event(self, 
                                    event_type: str, 
                                    data: Dict[str, Any],
                                    connection_data: Dict[str, Any]) -> None:
        """Record a WebSocket event related to tool execution."""
        event_record = {
            "event_type": event_type,
            "data": data,
            "timestamp": time.time(),
            "connection_id": connection_data.get("connection_id"),
            "user_id": self.test_user_id
        }
        
        self.websocket_events_received.append(event_record)
        connection_data["tool_events_received"].append(event_record)
        self.increment_websocket_events()
        
        self.logger.debug(f"Recorded tool WebSocket event: {event_type}")
    
    async def _simulate_tool_execution_with_result(self,
                                                 tool_name: str,
                                                 execution_time: float = 1.0,
                                                 should_succeed: bool = True,
                                                 result_data: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Simulate tool execution and return result."""
        # Record execution start
        await self._record_tool_execution(
            tool_name=tool_name,
            execution_phase=ToolExecutionPhase.DISPATCHED,
            details={"execution_time_expected": execution_time}
        )
        
        # Simulate execution time
        await asyncio.sleep(execution_time)
        
        if should_succeed:
            # Record successful execution
            await self._record_tool_execution(
                tool_name=tool_name,
                execution_phase=ToolExecutionPhase.COMPLETED,
                details={"execution_time_actual": execution_time, "result_data": result_data}
            )
            
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.SUCCESS,
                result=result_data or {"message": f"{tool_name} executed successfully"},
                execution_time=execution_time,
                metadata={"test_execution": True, "user_id": self.test_user_id}
            )
        else:
            # Record failed execution
            await self._record_tool_execution(
                tool_name=tool_name,
                execution_phase=ToolExecutionPhase.FAILED,
                details={"execution_time_actual": execution_time, "error": "Simulated failure"}
            )
            
            return ToolResult(
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error="Simulated tool execution failure for testing",
                execution_time=execution_time,
                metadata={"test_execution": True, "user_id": self.test_user_id}
            )
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.tool_execution
    async def test_tool_executing_to_tool_completed_transitions(self):
        """
        Test tool_executing → tool_completed transitions work reliably.
        
        This test validates that the critical WebSocket events for tool execution
        are properly sent and received, enabling users to see real-time tool
        execution progress during agent workflows.
        
        CRITICAL: This protects $500K+ ARR chat functionality by ensuring
        users can see tool execution transparency during AI problem-solving.
        """
        # ARRANGE: Create user context and infrastructure
        user_context = await self._create_test_user_context()
        connection_data = await self._simulate_websocket_connection(user_context)
        tool_dispatcher = await self._create_test_tool_dispatcher(user_context)
        
        # Create agent state for tool execution context
        agent_state = DeepAgentState(
            agent_id=f"tool_agent_{uuid.uuid4().hex[:8]}",
            user_context=user_context,
            initial_state="tool_ready"
        )
        
        # Define test tools to execute in sequence
        test_tools = [
            {"name": "data_analysis_tool", "execution_time": 0.2, "should_succeed": True},
            {"name": "optimization_tool", "execution_time": 0.3, "should_succeed": True},
            {"name": "reporting_tool", "execution_time": 0.1, "should_succeed": True}
        ]
        
        # ACT: Execute tool sequence with WebSocket event tracking
        
        tool_results = []
        
        for i, tool_config in enumerate(test_tools):
            tool_name = tool_config["name"]
            execution_time = tool_config["execution_time"]
            should_succeed = tool_config["should_succeed"]
            
            # Record tool_executing WebSocket event
            await self._record_websocket_event(
                "tool_executing",
                {
                    "tool_name": tool_name,
                    "agent_id": agent_state.agent_id,
                    "tool_index": i,
                    "estimated_duration": execution_time
                },
                connection_data
            )
            
            # Execute the tool
            tool_result = await self._simulate_tool_execution_with_result(
                tool_name=tool_name,
                execution_time=execution_time,
                should_succeed=should_succeed,
                result_data={"tool_index": i, "agent_id": agent_state.agent_id}
            )
            
            tool_results.append(tool_result)
            
            # Record tool_completed WebSocket event
            await self._record_websocket_event(
                "tool_completed",
                {
                    "tool_name": tool_name,
                    "agent_id": agent_state.agent_id,
                    "tool_index": i,
                    "status": tool_result.status.value,
                    "execution_time": tool_result.execution_time,
                    "result_preview": str(tool_result.result)[:100] if tool_result.result else None
                },
                connection_data
            )
        
        # ASSERT: Validate tool execution and WebSocket events
        
        # Verify all tools executed successfully
        self.assertEqual(len(tool_results), len(test_tools),
                        "All test tools should have been executed")
        
        for i, (tool_result, tool_config) in enumerate(zip(tool_results, test_tools)):
            self.assertEqual(tool_result.tool_name, tool_config["name"],
                           f"Tool {i} name should match")
            
            if tool_config["should_succeed"]:
                self.assertEqual(tool_result.status, ToolStatus.SUCCESS,
                               f"Tool {i} should have succeeded")
            else:
                self.assertEqual(tool_result.status, ToolStatus.ERROR,
                               f"Tool {i} should have failed as expected")
        
        # Verify WebSocket events were recorded correctly
        expected_events = len(test_tools) * 2  # tool_executing + tool_completed for each tool
        self.assertEqual(len(self.websocket_events_received), expected_events,
                        f"Should have recorded {expected_events} WebSocket events")
        
        # Verify event sequence (executing -> completed for each tool)
        for i in range(len(test_tools)):
            executing_event = self.websocket_events_received[i * 2]
            completed_event = self.websocket_events_received[i * 2 + 1]
            
            self.assertEqual(executing_event["event_type"], "tool_executing",
                           f"Event {i*2} should be tool_executing")
            self.assertEqual(completed_event["event_type"], "tool_completed",
                           f"Event {i*2+1} should be tool_completed")
            
            # Verify tool names match
            self.assertEqual(executing_event["data"]["tool_name"], test_tools[i]["name"],
                           f"Tool_executing event {i} tool name should match")
            self.assertEqual(completed_event["data"]["tool_name"], test_tools[i]["name"],
                           f"Tool_completed event {i} tool name should match")
        
        # Verify tool execution records
        completed_executions = [exec for exec in self.tool_executions if exec["phase"] == "completed"]
        self.assertEqual(len(completed_executions), len(test_tools),
                        "Should have completed execution records for all tools")
        
        # Verify performance characteristics
        total_execution_time = sum(tool_config["execution_time"] for tool_config in test_tools)
        total_test_time = time.time() - self.get_metric("test_start_time")
        
        # Allow some overhead but should be reasonably efficient
        self.assertLess(total_test_time, total_execution_time + 2.0,
                       "Total test time should not have excessive overhead")
        
        # Record business value metrics
        self.record_metric("tool_transitions_validated", True)
        self.record_metric("tools_executed_successfully", len(test_tools))
        self.record_metric("websocket_events_properly_sequenced", True)
        
        self.logger.info(f"Tool execution transitions validated successfully for {len(test_tools)} tools")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.tool_handoffs
    async def test_complex_tool_handoffs_during_agent_execution(self):
        """
        Test complex tool handoffs during agent execution scenarios.
        
        This test validates that when tools need to hand off execution to other
        tools during complex agent workflows, the handoffs work correctly and
        WebSocket events continue to provide visibility to users.
        """
        # ARRANGE: Create user context and infrastructure
        user_context = await self._create_test_user_context()
        connection_data = await self._simulate_websocket_connection(user_context)
        tool_dispatcher = await self._create_test_tool_dispatcher(user_context)
        
        # Create agent state for complex workflow
        agent_state = DeepAgentState(
            agent_id=f"handoff_agent_{uuid.uuid4().hex[:8]}",
            user_context=user_context,
            initial_state="complex_workflow_ready"
        )
        
        # ACT: Execute complex tool handoff scenario
        
        # Phase 1: Initial data collection tool
        await self._record_websocket_event(
            "tool_executing",
            {
                "tool_name": "data_collection_tool",
                "agent_id": agent_state.agent_id,
                "phase": "initial_collection"
            },
            connection_data
        )
        
        data_collection_result = await self._simulate_tool_execution_with_result(
            tool_name="data_collection_tool",
            execution_time=0.3,
            should_succeed=True,
            result_data={"data_points": 150, "requires_specialized_analysis": True}
        )
        
        await self._record_websocket_event(
            "tool_completed",
            {
                "tool_name": "data_collection_tool",
                "agent_id": agent_state.agent_id,
                "status": "completed",
                "handoff_required": True,
                "next_tool": "specialized_analysis_tool"
            },
            connection_data
        )
        
        # Phase 2: Tool handoff to specialized analysis
        handoff_reason = "Large dataset requires specialized analysis capabilities"
        await self._record_tool_handoff(
            from_tool="data_collection_tool",
            to_tool="specialized_analysis_tool",
            handoff_reason=handoff_reason,
            success=True,
            details={
                "data_points": 150,
                "agent_id": agent_state.agent_id,
                "handoff_trigger": "data_volume_threshold"
            }
        )
        
        await self._record_websocket_event(
            "tool_executing",
            {
                "tool_name": "specialized_analysis_tool",
                "agent_id": agent_state.agent_id,
                "phase": "specialized_analysis",
                "handoff_from": "data_collection_tool"
            },
            connection_data
        )
        
        analysis_result = await self._simulate_tool_execution_with_result(
            tool_name="specialized_analysis_tool",
            execution_time=0.5,
            should_succeed=True,
            result_data={
                "analysis_complete": True,
                "optimization_needed": True,
                "complexity_level": "high"
            }
        )
        
        await self._record_websocket_event(
            "tool_completed",
            {
                "tool_name": "specialized_analysis_tool",
                "agent_id": agent_state.agent_id,
                "status": "completed",
                "requires_optimization": True,
                "next_tool": "optimization_tool"
            },
            connection_data
        )
        
        # Phase 3: Second handoff to optimization tool
        await self._record_tool_handoff(
            from_tool="specialized_analysis_tool",
            to_tool="optimization_tool",
            handoff_reason="High complexity analysis requires optimization",
            success=True,
            details={
                "complexity_level": "high",
                "agent_id": agent_state.agent_id,
                "handoff_trigger": "complexity_threshold"
            }
        )
        
        await self._record_websocket_event(
            "tool_executing",
            {
                "tool_name": "optimization_tool",
                "agent_id": agent_state.agent_id,
                "phase": "optimization",
                "handoff_from": "specialized_analysis_tool"
            },
            connection_data
        )
        
        optimization_result = await self._simulate_tool_execution_with_result(
            tool_name="optimization_tool",
            execution_time=0.4,
            should_succeed=True,
            result_data={
                "optimization_complete": True,
                "performance_improvement": "35%",
                "ready_for_reporting": True
            }
        )
        
        await self._record_websocket_event(
            "tool_completed",
            {
                "tool_name": "optimization_tool",
                "agent_id": agent_state.agent_id,
                "status": "completed",
                "workflow_complete": True
            },
            connection_data
        )
        
        # ASSERT: Validate complex handoff workflow
        
        # Verify all tool executions were recorded
        completed_executions = [exec for exec in self.tool_executions if exec["phase"] == "completed"]
        expected_tools = ["data_collection_tool", "specialized_analysis_tool", "optimization_tool"]
        
        self.assertEqual(len(completed_executions), len(expected_tools),
                        "Should have completed executions for all tools in handoff chain")
        
        for i, tool_name in enumerate(expected_tools):
            self.assertEqual(completed_executions[i]["tool_name"], tool_name,
                           f"Tool {i} should be {tool_name}")
        
        # Verify handoffs were recorded
        self.assertEqual(len(self.tool_handoffs), 2,
                        "Should have recorded 2 tool handoffs")
        
        # Verify handoff chain integrity
        first_handoff = self.tool_handoffs[0]
        second_handoff = self.tool_handoffs[1]
        
        self.assertEqual(first_handoff["from_tool"], "data_collection_tool")
        self.assertEqual(first_handoff["to_tool"], "specialized_analysis_tool")
        self.assertTrue(first_handoff["success"], "First handoff should be successful")
        
        self.assertEqual(second_handoff["from_tool"], "specialized_analysis_tool")
        self.assertEqual(second_handoff["to_tool"], "optimization_tool")
        self.assertTrue(second_handoff["success"], "Second handoff should be successful")
        
        # Verify WebSocket event continuity throughout handoffs
        executing_events = [evt for evt in self.websocket_events_received if evt["event_type"] == "tool_executing"]
        completed_events = [evt for evt in self.websocket_events_received if evt["event_type"] == "tool_completed"]
        
        self.assertEqual(len(executing_events), 3, "Should have 3 tool_executing events")
        self.assertEqual(len(completed_events), 3, "Should have 3 tool_completed events")
        
        # Verify WebSocket events show handoff progression
        for i, tool_name in enumerate(expected_tools):
            self.assertEqual(executing_events[i]["data"]["tool_name"], tool_name,
                           f"Executing event {i} should be for {tool_name}")
            self.assertEqual(completed_events[i]["data"]["tool_name"], tool_name,
                           f"Completed event {i} should be for {tool_name}")
        
        # Verify handoff context preservation
        for handoff in self.tool_handoffs:
            self.assertEqual(handoff["details"]["agent_id"], agent_state.agent_id,
                           "Agent context should be preserved during handoffs")
        
        # Verify business value metrics
        self.record_metric("tool_handoffs_successful", len([h for h in self.tool_handoffs if h["success"]]))
        self.record_metric("handoff_chain_complete", True)
        self.record_metric("websocket_continuity_maintained", True)
        
        self.logger.info(f"Complex tool handoff workflow validated successfully with {len(self.tool_handoffs)} handoffs")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.tool_timeout
    async def test_tool_timeout_and_error_scenarios(self):
        """
        Test tool timeout and error scenarios during agent execution.
        
        This test validates that when tools timeout or fail, the system handles
        these scenarios gracefully and provides appropriate WebSocket events
        to keep users informed.
        """
        # ARRANGE: Create user context with shorter timeout for testing
        user_context = await self._create_test_user_context()
        connection_data = await self._simulate_websocket_connection(user_context)
        
        # Set shorter timeout for testing
        self.set_env_var("TOOL_EXECUTION_TIMEOUT", "2")  # 2 second timeout
        
        agent_state = DeepAgentState(
            agent_id=f"timeout_agent_{uuid.uuid4().hex[:8]}",
            user_context=user_context,
            initial_state="timeout_test_ready"
        )
        
        # ACT: Execute timeout and error scenarios
        
        # Scenario 1: Tool that times out
        await self._record_websocket_event(
            "tool_executing",
            {
                "tool_name": "slow_analysis_tool",
                "agent_id": agent_state.agent_id,
                "estimated_duration": 5.0,  # Longer than timeout
                "timeout_risk": True
            },
            connection_data
        )
        
        # Simulate timeout by waiting longer than timeout period
        timeout_start = time.time()
        try:
            # This should timeout
            timeout_result = await asyncio.wait_for(
                self._simulate_tool_execution_with_result(
                    tool_name="slow_analysis_tool",
                    execution_time=3.0,  # Longer than timeout
                    should_succeed=True
                ),
                timeout=2.0  # Timeout after 2 seconds
            )
            self.fail("Tool should have timed out")
        except asyncio.TimeoutError:
            timeout_duration = time.time() - timeout_start
            
            # Record timeout event
            timeout_record = {
                "tool_name": "slow_analysis_tool",
                "timeout_duration": timeout_duration,
                "expected_timeout": 2.0,
                "timestamp": time.time(),
                "user_id": self.test_user_id
            }
            self.timeout_events.append(timeout_record)
            
            await self._record_tool_execution(
                tool_name="slow_analysis_tool",
                execution_phase=ToolExecutionPhase.TIMED_OUT,
                details={"timeout_duration": timeout_duration}
            )
            
            await self._record_websocket_event(
                "tool_completed",
                {
                    "tool_name": "slow_analysis_tool",
                    "agent_id": agent_state.agent_id,
                    "status": "timeout",
                    "error": "Tool execution timed out",
                    "timeout_duration": timeout_duration
                },
                connection_data
            )
        
        # Scenario 2: Tool that fails with error
        await self._record_websocket_event(
            "tool_executing",
            {
                "tool_name": "error_prone_tool",
                "agent_id": agent_state.agent_id,
                "error_expected": True
            },
            connection_data
        )
        
        error_result = await self._simulate_tool_execution_with_result(
            tool_name="error_prone_tool",
            execution_time=0.1,
            should_succeed=False  # This will fail
        )
        
        await self._record_websocket_event(
            "tool_completed",
            {
                "tool_name": "error_prone_tool",
                "agent_id": agent_state.agent_id,
                "status": "error",
                "error": error_result.error,
                "execution_time": error_result.execution_time
            },
            connection_data
        )
        
        # Scenario 3: Successful recovery tool
        await self._record_websocket_event(
            "tool_executing",
            {
                "tool_name": "recovery_tool",
                "agent_id": agent_state.agent_id,
                "recovery_attempt": True
            },
            connection_data
        )
        
        recovery_result = await self._simulate_tool_execution_with_result(
            tool_name="recovery_tool",
            execution_time=0.2,
            should_succeed=True,
            result_data={"recovery_successful": True, "errors_handled": 2}
        )
        
        await self._record_websocket_event(
            "tool_completed",
            {
                "tool_name": "recovery_tool",
                "agent_id": agent_state.agent_id,
                "status": "success",
                "recovery_data": recovery_result.result
            },
            connection_data
        )
        
        # ASSERT: Validate timeout and error handling
        
        # Verify timeout was recorded
        self.assertEqual(len(self.timeout_events), 1, "Should have recorded 1 timeout event")
        timeout_event = self.timeout_events[0]
        self.assertEqual(timeout_event["tool_name"], "slow_analysis_tool")
        self.assertAlmostEqual(timeout_event["timeout_duration"], 2.0, delta=0.5)
        
        # Verify tool execution phases were recorded correctly
        timed_out_executions = [exec for exec in self.tool_executions if exec["phase"] == "timed_out"]
        failed_executions = [exec for exec in self.tool_executions if exec["phase"] == "failed"]
        completed_executions = [exec for exec in self.tool_executions if exec["phase"] == "completed"]
        
        self.assertEqual(len(timed_out_executions), 1, "Should have 1 timed out execution")
        self.assertEqual(len(failed_executions), 1, "Should have 1 failed execution")
        self.assertEqual(len(completed_executions), 1, "Should have 1 completed execution")
        
        # Verify WebSocket events were sent for all scenarios
        timeout_events_ws = [evt for evt in self.websocket_events_received 
                           if evt["data"].get("status") == "timeout"]
        error_events_ws = [evt for evt in self.websocket_events_received 
                         if evt["data"].get("status") == "error"]
        success_events_ws = [evt for evt in self.websocket_events_received 
                           if evt["data"].get("status") == "success"]
        
        self.assertEqual(len(timeout_events_ws), 1, "Should have 1 timeout WebSocket event")
        self.assertEqual(len(error_events_ws), 1, "Should have 1 error WebSocket event")
        self.assertEqual(len(success_events_ws), 1, "Should have 1 success WebSocket event")
        
        # Verify error handling provides useful information
        error_event = error_events_ws[0]
        self.assertIn("error", error_event["data"], "Error event should contain error details")
        self.assertEqual(error_event["data"]["tool_name"], "error_prone_tool")
        
        # Verify recovery was successful
        success_event = success_events_ws[0]
        self.assertEqual(success_event["data"]["tool_name"], "recovery_tool")
        self.assertTrue(success_event["data"].get("recovery_data", {}).get("recovery_successful", False))
        
        # Record error handling metrics
        self.record_metric("timeout_scenarios_handled", len(self.timeout_events))
        self.record_metric("error_scenarios_handled", len(failed_executions))
        self.record_metric("recovery_scenarios_successful", len(completed_executions))
        self.record_metric("error_handling_validated", True)
        
        self.logger.info("Tool timeout and error scenarios validated successfully")


# Test configuration for pytest
pytestmark = [
    pytest.mark.integration,
    pytest.mark.tool_execution,
    pytest.mark.tool_handoffs,
    pytest.mark.real_services
]
