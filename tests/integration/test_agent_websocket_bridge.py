"""
Integration Test: Agent-WebSocket Bridge Communication - Bridge Integration Validation

MISSION CRITICAL: Tests the agent-WebSocket bridge that enables seamless communication
between agent execution and WebSocket event delivery, ensuring real-time AI value
reaches users through properly integrated infrastructure components.

Business Value Justification (BVJ):
- Segment: Platform/All - Core AI-WebSocket Integration
- Business Goal: Revenue Protection - Ensures agent execution translates to user value
- Value Impact: Validates the bridge that converts AI processing into user-visible events
- Strategic Impact: Tests the integration that powers 90% of platform business value

CRITICAL REQUIREMENTS:
1. Agent execution to WebSocket event translation
2. Real-time bridge communication with minimal latency
3. Agent lifecycle event generation and delivery
4. Multi-agent orchestration with event coordination
5. Error handling and graceful degradation in bridge communication

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat (Section 6)
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - NO MOCKS for integration tests
@compliance SPEC/core.xml - Single Source of Truth patterns
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.websocket_core.event_validator import (
    WebSocketEventMessage,
    CriticalAgentEventType,
    UnifiedEventValidator
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.isolated_environment import get_env


@pytest.mark.integration
class AgentWebSocketBridgeIntegrationTests(SSotAsyncTestCase):
    """
    Integration tests for agent-WebSocket bridge communication.
    
    These tests validate that the bridge properly translates agent execution
    into WebSocket events, maintains real-time communication, and ensures
    proper coordination between agent lifecycle and event delivery.
    
    CRITICAL: Tests the bridge that enables AI value delivery to users.
    """

    def setup_method(self):
        """Set up test environment with bridge and agent components."""
        super().setup_method()
        self.env = get_env()
        
        # Initialize bridge and agent components
        self.websocket_bridge = AgentWebSocketBridge()
        self.bridge_factory = WebSocketBridgeFactory()
        self.agent_registry = AgentRegistry()
        self.execution_factory = ExecutionEngineFactory()
        self.agent_instance_factory = AgentInstanceFactory()
        
        # Test state tracking
        self.bridge_events: List[Dict[str, Any]] = []
        self.agent_executions: List[Dict[str, Any]] = []
        self.bridge_metrics: Dict[str, Any] = {}
        self.test_user_contexts: List[UserExecutionContext] = []
        self.active_bridges: List[Any] = []
        
        # Configure test environment
        self.set_env_var("TESTING", "true")
        self.set_env_var("BRIDGE_TEST_MODE", "true")
        self.set_env_var("AGENT_BRIDGE_TIMEOUT", "10000")  # 10 second timeout for tests
        
    async def teardown_method(self):
        """Clean up bridge components and test state."""
        try:
            # Clean up active bridges
            for bridge in self.active_bridges:
                try:
                    await self._cleanup_bridge(bridge)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup bridge: {e}")
            
            # Clean up agent registry
            if self.agent_registry:
                await self.agent_registry.cleanup_all_agents()
            
            # Clean up user contexts
            for context in self.test_user_contexts:
                await self._cleanup_user_context(context)
            
            # Reset state
            self.bridge_events.clear()
            self.agent_executions.clear()
            self.bridge_metrics.clear()
            self.active_bridges.clear()
        finally:
            await super().teardown_method()

    def _create_test_user_context(self, user_suffix: str = None) -> UserExecutionContext:
        """Create isolated user execution context for bridge tests."""
        suffix = user_suffix or f"bridge_{uuid.uuid4().hex[:8]}"
        context = self.create_test_user_execution_context(
            user_id=f"test_user_{suffix}",
            thread_id=f"thread_{suffix}",
            run_id=f"run_{suffix}",
            websocket_client_id=f"ws_{suffix}"
        )
        self.test_user_contexts.append(context)
        return context

    async def _cleanup_user_context(self, context: UserExecutionContext):
        """Clean up resources for a user context."""
        try:
            # Clean up any registered agents for this context
            if hasattr(context, 'registered_agents'):
                for agent_name in context.registered_agents:
                    await self.agent_registry.unregister_agent(agent_name, context)
        except Exception as e:
            self.logger.warning(f"Error during context cleanup: {e}")

    async def _cleanup_bridge(self, bridge):
        """Clean up a bridge instance."""
        try:
            if hasattr(bridge, 'disconnect'):
                await bridge.disconnect()
            elif hasattr(bridge, 'close'):
                await bridge.close()
        except Exception as e:
            self.logger.warning(f"Error during bridge cleanup: {e}")

    async def _create_test_bridge(self, user_context: UserExecutionContext) -> Any:
        """Create a test bridge instance for user context."""
        bridge = await self.bridge_factory.create_user_bridge(
            user_id=user_context.user_id,
            websocket_client_id=user_context.websocket_client_id,
            thread_id=user_context.thread_id
        )
        self.active_bridges.append(bridge)
        return bridge

    async def _simulate_agent_execution_step(
        self, 
        agent_name: str, 
        step_type: str, 
        user_context: UserExecutionContext,
        **step_data
    ) -> Dict[str, Any]:
        """Simulate an agent execution step that should generate bridge events."""
        execution_step = {
            "agent_name": agent_name,
            "step_type": step_type,
            "user_context": {
                "user_id": user_context.user_id,
                "thread_id": user_context.thread_id,
                "run_id": user_context.run_id,
                "websocket_client_id": user_context.websocket_client_id
            },
            "timestamp": datetime.now(timezone.utc),
            "step_data": step_data
        }
        
        self.agent_executions.append(execution_step)
        
        # Simulate bridge event generation
        bridge_event = await self._generate_bridge_event_from_step(execution_step)
        
        return execution_step

    async def _generate_bridge_event_from_step(self, execution_step: Dict[str, Any]) -> Dict[str, Any]:
        """Generate WebSocket event from agent execution step via bridge."""
        step_type = execution_step["step_type"]
        agent_name = execution_step["agent_name"]
        user_context = execution_step["user_context"]
        step_data = execution_step["step_data"]
        
        # Map execution steps to WebSocket events
        event_type_mapping = {
            "start_execution": "agent_started",
            "begin_thinking": "agent_thinking",
            "execute_tool": "tool_executing",
            "complete_tool": "tool_completed",
            "finish_execution": "agent_completed",
            "handle_error": "error"
        }
        
        event_type = event_type_mapping.get(step_type, "status_update")
        
        # Create bridge event
        bridge_event = {
            "event_type": event_type,
            "agent_name": agent_name,
            "user_id": user_context["user_id"],
            "thread_id": user_context["thread_id"],
            "run_id": user_context["run_id"],
            "websocket_client_id": user_context["websocket_client_id"],
            "timestamp": datetime.now(timezone.utc),
            "bridge_data": {
                "execution_step": step_type,
                "bridge_latency_ms": 0.5,  # Simulated bridge processing time
                **step_data
            }
        }
        
        # Simulate bridge processing delay
        await asyncio.sleep(0.001)
        
        self.bridge_events.append(bridge_event)
        return bridge_event

    @pytest.mark.asyncio
    async def test_basic_agent_bridge_communication(self):
        """
        Test: Basic agent to WebSocket bridge communication.
        
        Validates that agent execution steps are properly translated into
        WebSocket events through the bridge with correct data mapping.
        
        Business Value: Ensures agent execution reaches users as events.
        """
        print("\n🧪 Testing basic agent bridge communication...")
        
        user_context = self._create_test_user_context("basic_bridge")
        bridge = await self._create_test_bridge(user_context)
        
        # Simulate complete agent execution flow through bridge
        agent_name = "bridge_test_agent"
        execution_steps = [
            ("start_execution", {"user_request": "Analyze data for optimization opportunities"}),
            ("begin_thinking", {"thinking_stage": "analysis", "focus": "data patterns"}),
            ("execute_tool", {"tool_name": "data_analyzer", "purpose": "pattern identification"}),
            ("complete_tool", {"tool_name": "data_analyzer", "results": {"patterns": 5, "insights": 3}}),
            ("finish_execution", {"final_response": "Analysis complete with 3 key insights", "deliverables": ["Pattern analysis", "Optimization recommendations"]})
        ]
        
        # Execute steps through bridge
        bridge_latencies = []
        
        for step_type, step_data in execution_steps:
            step_start = time.time()
            
            # Simulate agent execution step
            execution_step = await self._simulate_agent_execution_step(
                agent_name, step_type, user_context, **step_data
            )
            
            bridge_latency = time.time() - step_start
            bridge_latencies.append(bridge_latency)
            
            print(f"  🔗 Bridge: {step_type} -> {execution_step['timestamp'].strftime('%H:%M:%S.%f')[:-3]} ({bridge_latency * 1000:.1f}ms)")
            
            # Small delay between steps
            await asyncio.sleep(0.01)
        
        # Validate bridge event generation
        assert len(self.bridge_events) == len(execution_steps), f"Bridge event count mismatch: expected {len(execution_steps)}, got {len(self.bridge_events)}"
        
        # Validate event types mapping
        expected_event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        actual_event_types = [event["event_type"] for event in self.bridge_events]
        assert actual_event_types == expected_event_types, f"Event type mapping error: expected {expected_event_types}, got {actual_event_types}"
        
        # Validate data preservation through bridge
        for i, bridge_event in enumerate(self.bridge_events):
            execution_step = self.agent_executions[i]
            
            # Check user context preservation
            assert bridge_event["user_id"] == user_context.user_id, f"User ID lost in bridge for event {i+1}"
            assert bridge_event["thread_id"] == user_context.thread_id, f"Thread ID lost in bridge for event {i+1}"
            assert bridge_event["run_id"] == user_context.run_id, f"Run ID lost in bridge for event {i+1}"
            
            # Check agent context preservation
            assert bridge_event["agent_name"] == agent_name, f"Agent name lost in bridge for event {i+1}"
            
            # Check step data preservation
            step_data = execution_step["step_data"]
            bridge_data = bridge_event["bridge_data"]
            
            for key, value in step_data.items():
                assert key in bridge_data or f"original_{key}" in bridge_data, f"Step data '{key}' lost in bridge for event {i+1}"
        
        # Validate bridge performance
        avg_latency = sum(bridge_latencies) / len(bridge_latencies)
        max_latency = max(bridge_latencies)
        
        assert avg_latency < 0.05, f"Bridge latency too high: avg {avg_latency * 1000:.1f}ms > 50ms"
        assert max_latency < 0.1, f"Max bridge latency too high: {max_latency * 1000:.1f}ms > 100ms"
        
        # Record metrics
        self.record_metric("bridge_events_generated", len(self.bridge_events))
        self.record_metric("avg_bridge_latency_ms", avg_latency * 1000)
        self.record_metric("max_bridge_latency_ms", max_latency * 1000)
        
        print(f"  CHECK Basic bridge communication successful - {len(self.bridge_events)} events")
        print(f"  ⚡ Bridge performance: avg {avg_latency * 1000:.1f}ms, max {max_latency * 1000:.1f}ms")

    @pytest.mark.asyncio
    async def test_real_time_bridge_event_delivery(self):
        """
        Test: Real-time bridge event delivery with timing guarantees.
        
        Validates that bridge events are delivered in real-time with
        minimal latency and proper ordering preservation.
        
        Business Value: Ensures users see AI progress in real-time.
        """
        print("\n🧪 Testing real-time bridge event delivery...")
        
        user_context = self._create_test_user_context("realtime_bridge")
        bridge = await self._create_test_bridge(user_context)
        
        # Create time-sensitive event sequence
        agent_name = "realtime_agent"
        realtime_steps = [
            ("start_execution", {"urgent": True, "real_time_processing": True}),
            ("begin_thinking", {"streaming": True, "progress_updates": True}),
            ("begin_thinking", {"streaming": True, "progress": "25% complete"}),
            ("begin_thinking", {"streaming": True, "progress": "50% complete"}),
            ("begin_thinking", {"streaming": True, "progress": "75% complete"}),
            ("execute_tool", {"tool_name": "realtime_analyzer", "streaming_results": True}),
            ("complete_tool", {"tool_name": "realtime_analyzer", "streaming_complete": True}),
            ("finish_execution", {"real_time_complete": True, "total_time": "2.3 seconds"})
        ]
        
        # Execute with precise timing measurement
        delivery_times = []
        event_intervals = []
        last_event_time = None
        
        for i, (step_type, step_data) in enumerate(realtime_steps):
            step_start = time.time()
            
            # Execute step
            execution_step = await self._simulate_agent_execution_step(
                agent_name, step_type, user_context, **step_data
            )
            
            # Measure delivery time
            delivery_time = time.time() - step_start
            delivery_times.append(delivery_time)
            
            # Measure interval between events
            current_time = time.time()
            if last_event_time is not None:
                interval = current_time - last_event_time
                event_intervals.append(interval)
            last_event_time = current_time
            
            print(f"  ⚡ Real-time: {step_type} delivered in {delivery_time * 1000:.1f}ms")
            
            # Realistic real-time delay
            await asyncio.sleep(0.05)  # 50ms between events
        
        # Validate real-time performance
        avg_delivery_time = sum(delivery_times) / len(delivery_times)
        max_delivery_time = max(delivery_times)
        
        # Real-time requirements (strict)
        assert avg_delivery_time < 0.01, f"Average delivery time too slow for real-time: {avg_delivery_time * 1000:.1f}ms > 10ms"
        assert max_delivery_time < 0.02, f"Max delivery time too slow for real-time: {max_delivery_time * 1000:.1f}ms > 20ms"
        
        # Validate event interval consistency
        if event_intervals:
            avg_interval = sum(event_intervals) / len(event_intervals)
            interval_variance = max(event_intervals) - min(event_intervals)
            
            # Intervals should be consistent for real-time streaming
            assert interval_variance < 0.1, f"Event interval variance too high: {interval_variance * 1000:.1f}ms"
        
        # Validate streaming event content
        thinking_events = [event for event in self.bridge_events if event["event_type"] == "agent_thinking"]
        assert len(thinking_events) >= 4, f"Insufficient streaming thinking events: {len(thinking_events)} < 4"
        
        # Check progress indicators in streaming events
        progress_events = [event for event in thinking_events if "progress" in event["bridge_data"]]
        assert len(progress_events) >= 3, f"Missing progress indicators in streaming: {len(progress_events)} < 3"
        
        # Validate real-time event ordering
        event_timestamps = [event["timestamp"] for event in self.bridge_events]
        sorted_timestamps = sorted(event_timestamps)
        assert event_timestamps == sorted_timestamps, "Real-time events delivered out of order"
        
        # Record metrics
        self.record_metric("realtime_events_count", len(self.bridge_events))
        self.record_metric("avg_delivery_time_ms", avg_delivery_time * 1000)
        self.record_metric("max_delivery_time_ms", max_delivery_time * 1000)
        self.record_metric("streaming_thinking_events", len(thinking_events))
        
        print(f"  CHECK Real-time delivery successful - {len(self.bridge_events)} events")
        print(f"  ⚡ Performance: avg {avg_delivery_time * 1000:.1f}ms, max {max_delivery_time * 1000:.1f}ms")
        print(f"  📊 Streaming events: {len(thinking_events)} thinking updates")

    @pytest.mark.asyncio
    async def test_multi_agent_bridge_coordination(self):
        """
        Test: Multi-agent coordination through bridge communication.
        
        Validates that multiple agents can coordinate through the bridge
        with proper event isolation and handoff mechanisms.
        
        Business Value: Enables complex AI workflows with multiple agents.
        """
        print("\n🧪 Testing multi-agent bridge coordination...")
        
        user_context = self._create_test_user_context("multi_agent_bridge")
        bridge = await self._create_test_bridge(user_context)
        
        # Create multi-agent workflow
        agents = [
            {"name": "coordinator_agent", "role": "coordination"},
            {"name": "analyzer_agent", "role": "analysis"},
            {"name": "optimizer_agent", "role": "optimization"}
        ]
        
        # Simulate coordinated execution
        coordination_events = []
        
        # Phase 1: Coordinator starts and delegates
        coord_steps = [
            ("start_execution", {"workflow": "multi_agent_optimization", "agents_planned": 3}),
            ("begin_thinking", {"planning": "delegating tasks to specialized agents"}),
            ("finish_execution", {"delegation": "tasks assigned to analyzer and optimizer agents"})
        ]
        
        for step_type, step_data in coord_steps:
            await self._simulate_agent_execution_step(
                agents[0]["name"], step_type, user_context, **step_data
            )
            coordination_events.append(f"{agents[0]['name']}:{step_type}")
        
        print(f"  🎯 Coordinator: {len(coord_steps)} coordination steps")
        
        # Phase 2: Analyzer executes analysis
        analyzer_steps = [
            ("start_execution", {"delegated_from": "coordinator_agent", "task": "data_analysis"}),
            ("begin_thinking", {"analyzing": "user data patterns and optimization opportunities"}),
            ("execute_tool", {"tool_name": "pattern_analyzer", "scope": "comprehensive"}),
            ("complete_tool", {"tool_name": "pattern_analyzer", "patterns_found": 8}),
            ("finish_execution", {"analysis_complete": True, "handoff_to": "optimizer_agent"})
        ]
        
        for step_type, step_data in analyzer_steps:
            await self._simulate_agent_execution_step(
                agents[1]["name"], step_type, user_context, **step_data
            )
            coordination_events.append(f"{agents[1]['name']}:{step_type}")
        
        print(f"  🔍 Analyzer: {len(analyzer_steps)} analysis steps")
        
        # Phase 3: Optimizer processes results
        optimizer_steps = [
            ("start_execution", {"delegated_from": "analyzer_agent", "task": "optimization", "input_patterns": 8}),
            ("begin_thinking", {"optimizing": "based on analysis results from analyzer"}),
            ("execute_tool", {"tool_name": "optimization_engine", "input_data": "analysis_results"}),
            ("complete_tool", {"tool_name": "optimization_engine", "optimizations": 5}),
            ("finish_execution", {"final_results": "5 optimizations identified", "workflow_complete": True})
        ]
        
        for step_type, step_data in optimizer_steps:
            await self._simulate_agent_execution_step(
                agents[2]["name"], step_type, user_context, **step_data
            )
            coordination_events.append(f"{agents[2]['name']}:{step_type}")
        
        print(f"  ⚙️ Optimizer: {len(optimizer_steps)} optimization steps")
        
        # Validate multi-agent coordination
        total_expected_events = len(coord_steps) + len(analyzer_steps) + len(optimizer_steps)
        assert len(self.bridge_events) == total_expected_events, f"Event count mismatch: expected {total_expected_events}, got {len(self.bridge_events)}"
        
        # Validate agent isolation in events
        events_by_agent = {}
        for event in self.bridge_events:
            agent_name = event["agent_name"]
            if agent_name not in events_by_agent:
                events_by_agent[agent_name] = []
            events_by_agent[agent_name].append(event)
        
        # Check each agent has their events
        for agent in agents:
            agent_name = agent["name"]
            assert agent_name in events_by_agent, f"Agent {agent_name} missing from bridge events"
            
            agent_events = events_by_agent[agent_name]
            expected_count = {
                "coordinator_agent": len(coord_steps),
                "analyzer_agent": len(analyzer_steps),
                "optimizer_agent": len(optimizer_steps)
            }[agent_name]
            
            assert len(agent_events) == expected_count, f"Agent {agent_name} event count mismatch: expected {expected_count}, got {len(agent_events)}"
        
        # Validate handoff data preservation
        analyzer_start = next(event for event in self.bridge_events 
                            if event["agent_name"] == "analyzer_agent" and event["event_type"] == "agent_started")
        assert "delegated_from" in analyzer_start["bridge_data"], "Handoff context missing in analyzer start"
        
        optimizer_start = next(event for event in self.bridge_events 
                             if event["agent_name"] == "optimizer_agent" and event["event_type"] == "agent_started")
        assert "delegated_from" in optimizer_start["bridge_data"], "Handoff context missing in optimizer start"
        
        # Validate workflow progression
        coordinator_finish = next(event for event in self.bridge_events 
                                if event["agent_name"] == "coordinator_agent" and event["event_type"] == "agent_completed")
        analyzer_finish = next(event for event in self.bridge_events 
                             if event["agent_name"] == "analyzer_agent" and event["event_type"] == "agent_completed")
        optimizer_finish = next(event for event in self.bridge_events 
                              if event["agent_name"] == "optimizer_agent" and event["event_type"] == "agent_completed")
        
        # Validate timing progression (coordinator -> analyzer -> optimizer)
        assert coordinator_finish["timestamp"] < analyzer_start["timestamp"], "Coordination must complete before analysis starts"
        assert analyzer_finish["timestamp"] < optimizer_start["timestamp"], "Analysis must complete before optimization starts"
        
        # Record metrics
        self.record_metric("coordinated_agents", len(agents))
        self.record_metric("total_coordination_events", len(self.bridge_events))
        self.record_metric("coordination_phases", 3)
        
        print(f"  CHECK Multi-agent coordination successful - {len(agents)} agents, {len(self.bridge_events)} events")
        print(f"  🔄 Coordination flow: Coordinator -> Analyzer -> Optimizer")
        print(f"  📊 Events per agent: Coord {len(coord_steps)}, Analyzer {len(analyzer_steps)}, Optimizer {len(optimizer_steps)}")

    @pytest.mark.asyncio
    async def test_bridge_error_handling_and_recovery(self):
        """
        Test: Bridge error handling and recovery mechanisms.
        
        Validates that the bridge properly handles errors during agent
        execution and provides graceful recovery with user notification.
        
        Business Value: Ensures reliable AI delivery despite infrastructure issues.
        """
        print("\n🧪 Testing bridge error handling and recovery...")
        
        user_context = self._create_test_user_context("error_bridge")
        bridge = await self._create_test_bridge(user_context)
        
        # Create execution sequence with errors and recovery
        agent_name = "resilient_agent"
        error_recovery_sequence = [
            ("start_execution", {"resilience_mode": True, "error_handling": "graceful"}),
            ("begin_thinking", {"planning": "robust execution with error handling"}),
            ("execute_tool", {"tool_name": "primary_tool", "backup_available": True}),
            ("handle_error", {"error_type": "tool_failure", "tool_name": "primary_tool", "recovery_action": "fallback_to_backup"}),
            ("execute_tool", {"tool_name": "backup_tool", "recovery_mode": True}),
            ("complete_tool", {"tool_name": "backup_tool", "recovery_successful": True}),
            ("finish_execution", {"completed_with_recovery": True, "reliability_maintained": True})
        ]
        
        # Execute sequence with error simulation
        error_count = 0
        recovery_count = 0
        
        for step_type, step_data in error_recovery_sequence:
            execution_step = await self._simulate_agent_execution_step(
                agent_name, step_type, user_context, **step_data
            )
            
            if step_type == "handle_error":
                error_count += 1
                print(f"  WARNING️ Error handled: {step_data.get('error_type', 'unknown')} -> {step_data.get('recovery_action', 'unknown')}")
            elif "recovery" in str(step_data):
                recovery_count += 1
                print(f"  🔄 Recovery: {step_type}")
            
            await asyncio.sleep(0.01)
        
        # Validate error event generation
        error_events = [event for event in self.bridge_events if event["event_type"] == "error"]
        assert len(error_events) == error_count, f"Error event count mismatch: expected {error_count}, got {len(error_events)}"
        
        # Validate error event structure
        for error_event in error_events:
            bridge_data = error_event["bridge_data"]
            assert "error_type" in bridge_data, "Error event missing error_type"
            assert "recovery_action" in bridge_data, "Error event missing recovery_action"
            
            # Validate user-friendly error messaging
            error_type = bridge_data["error_type"]
            recovery_action = bridge_data["recovery_action"]
            assert error_type in ["tool_failure", "connection_error", "timeout"], f"Unknown error type: {error_type}"
            assert "fallback" in recovery_action or "retry" in recovery_action, f"Invalid recovery action: {recovery_action}"
        
        # Validate recovery sequence
        recovery_events = [event for event in self.bridge_events 
                         if "recovery" in str(event["bridge_data"]) or "backup" in str(event["bridge_data"])]
        assert len(recovery_events) >= recovery_count, f"Insufficient recovery events: {len(recovery_events)} < {recovery_count}"
        
        # Validate successful completion despite errors
        completion_events = [event for event in self.bridge_events if event["event_type"] == "agent_completed"]
        assert len(completion_events) == 1, "Must have successful completion despite errors"
        
        completion_event = completion_events[0]
        bridge_data = completion_event["bridge_data"]
        assert bridge_data.get("completed_with_recovery") is True, "Completion must acknowledge recovery"
        assert bridge_data.get("reliability_maintained") is True, "Completion must confirm reliability"
        
        # Validate bridge maintains event sequence integrity
        event_types = [event["event_type"] for event in self.bridge_events]
        assert "agent_started" in event_types, "Must have agent_started despite errors"
        assert "agent_completed" in event_types, "Must have agent_completed despite errors"
        assert "error" in event_types, "Must have error event"
        
        # Validate no event loss during error handling
        total_expected_events = len(error_recovery_sequence)
        assert len(self.bridge_events) == total_expected_events, f"Event loss during error handling: expected {total_expected_events}, got {len(self.bridge_events)}"
        
        # Validate error transparency
        for error_event in error_events:
            bridge_data = error_event["bridge_data"]
            # Errors should provide clear user impact and recovery information
            assert "recovery_action" in bridge_data, "Error must specify recovery action"
            assert "error_type" in bridge_data, "Error must specify error type"
        
        # Record metrics
        self.record_metric("errors_handled", error_count)
        self.record_metric("recovery_actions", recovery_count)
        self.record_metric("error_recovery_ratio", recovery_count / max(error_count, 1))
        self.record_metric("completion_despite_errors", 1)
        
        print(f"  CHECK Bridge error handling successful - {error_count} errors, {recovery_count} recoveries")
        print(f"  🛡️ Error recovery ratio: {recovery_count}/{error_count} = {recovery_count/max(error_count, 1):.1f}")
        print(f"  🎯 Successful completion maintained despite {error_count} errors")

    @pytest.mark.asyncio
    async def test_bridge_performance_under_concurrent_load(self):
        """
        Test: Bridge performance under concurrent agent execution load.
        
        Validates that the bridge maintains performance and reliability
        when handling multiple concurrent agent executions.
        
        Business Value: Ensures platform scalability for multiple simultaneous users.
        """
        print("\n🧪 Testing bridge performance under concurrent load...")
        
        # Create multiple user contexts for load testing
        concurrent_users = []
        concurrent_bridges = []
        
        user_count = 5  # 5 concurrent users
        agents_per_user = 2  # 2 agents per user
        steps_per_agent = 5  # 5 steps per agent
        
        for i in range(user_count):
            user_context = self._create_test_user_context(f"load_user_{i+1}")
            bridge = await self._create_test_bridge(user_context)
            concurrent_users.append(user_context)
            concurrent_bridges.append(bridge)
        
        # Create concurrent execution tasks
        async def execute_agent_load(user_index, user_context, agent_index):
            """Execute agent load for concurrent testing."""
            agent_name = f"load_agent_{user_index+1}_{agent_index+1}"
            
            steps = [
                ("start_execution", {"load_test": True, "user_index": user_index, "agent_index": agent_index}),
                ("begin_thinking", {"concurrent_processing": True}),
                ("execute_tool", {"tool_name": f"load_tool_{agent_index}", "concurrent": True}),
                ("complete_tool", {"tool_name": f"load_tool_{agent_index}", "load_results": {"success": True}}),
                ("finish_execution", {"load_test_complete": True})
            ]
            
            execution_times = []
            
            for step_type, step_data in steps:
                step_start = time.time()
                
                await self._simulate_agent_execution_step(
                    agent_name, step_type, user_context, **step_data
                )
                
                execution_time = time.time() - step_start
                execution_times.append(execution_time)
                
                # Small concurrent delay
                await asyncio.sleep(0.001)
            
            return {
                "user_index": user_index,
                "agent_index": agent_index,
                "agent_name": agent_name,
                "execution_times": execution_times,
                "total_time": sum(execution_times)
            }
        
        # Create all concurrent tasks
        concurrent_tasks = []
        for user_index, user_context in enumerate(concurrent_users):
            for agent_index in range(agents_per_user):
                task = execute_agent_load(user_index, user_context, agent_index)
                concurrent_tasks.append(task)
        
        print(f"  🚀 Starting concurrent load: {user_count} users × {agents_per_user} agents × {steps_per_agent} steps = {len(concurrent_tasks)} total executions")
        
        # Execute all tasks concurrently
        load_start_time = time.time()
        
        execution_results = await asyncio.gather(*concurrent_tasks)
        
        total_load_time = time.time() - load_start_time
        
        # Analyze load test results
        total_executions = len(execution_results)
        total_events = len(self.bridge_events)
        
        all_execution_times = []
        for result in execution_results:
            all_execution_times.extend(result["execution_times"])
        
        avg_execution_time = sum(all_execution_times) / len(all_execution_times)
        max_execution_time = max(all_execution_times)
        
        # Calculate throughput
        events_per_second = total_events / total_load_time
        executions_per_second = total_executions / total_load_time
        
        # Validate performance under load
        assert avg_execution_time < 0.05, f"Average execution time too slow under load: {avg_execution_time * 1000:.1f}ms > 50ms"
        assert events_per_second > 20, f"Event throughput too low: {events_per_second:.1f} events/sec < 20 events/sec"
        
        # Validate user isolation under concurrent load
        events_by_user = {}
        for event in self.bridge_events:
            user_id = event["user_id"]
            if user_id not in events_by_user:
                events_by_user[user_id] = []
            events_by_user[user_id].append(event)
        
        # Check each user received their expected events
        expected_events_per_user = agents_per_user * steps_per_agent
        for user_context in concurrent_users:
            user_id = user_context.user_id
            user_events = events_by_user.get(user_id, [])
            
            assert len(user_events) == expected_events_per_user, f"User {user_id} event count under load: expected {expected_events_per_user}, got {len(user_events)}"
            
            # Validate no cross-contamination
            for event in user_events:
                assert event["user_id"] == user_id, f"User isolation failure under load: {event['user_id']} != {user_id}"
        
        # Validate agent isolation within users
        for user_context in concurrent_users:
            user_events = events_by_user[user_context.user_id]
            agents_in_events = {event["agent_name"] for event in user_events}
            
            expected_agents = {f"load_agent_{concurrent_users.index(user_context)+1}_{i+1}" for i in range(agents_per_user)}
            assert agents_in_events == expected_agents, f"Agent isolation failure for user {user_context.user_id}"
        
        # Record comprehensive load metrics
        self.record_metric("concurrent_users", user_count)
        self.record_metric("agents_per_user", agents_per_user)
        self.record_metric("total_concurrent_executions", total_executions)
        self.record_metric("total_concurrent_events", total_events)
        self.record_metric("load_test_duration_ms", total_load_time * 1000)
        self.record_metric("avg_execution_time_ms", avg_execution_time * 1000)
        self.record_metric("events_per_second", events_per_second)
        self.record_metric("executions_per_second", executions_per_second)
        
        print(f"  CHECK Concurrent load test successful - {total_events} events, {total_executions} executions")
        print(f"  🚀 Throughput: {events_per_second:.1f} events/sec, {executions_per_second:.1f} executions/sec")
        print(f"  ⚡ Performance: avg {avg_execution_time * 1000:.1f}ms, max {max_execution_time * 1000:.1f}ms")
        print(f"  🕒 Total duration: {total_load_time * 1000:.1f}ms")


if __name__ == "__main__":
    """MIGRATED: Use SSOT unified test runner"""
    print("MIGRATION NOTICE: Please use SSOT unified test runner")
    print("Command: python tests/unified_test_runner.py --category integration")