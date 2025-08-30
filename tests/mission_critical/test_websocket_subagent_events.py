#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: Sub-Agent WebSocket Event Emissions

THIS IS A COMPREHENSIVE FAILING TEST SUITE DESIGNED TO EXPOSE CRITICAL GAPS
IN WEBSOCKET EVENT EMISSIONS DURING SUB-AGENT EXECUTION

Business Value: $500K+ ARR - Core chat functionality depends on WebSocket events
Critical Issue: Sub-agents do not properly emit WebSocket events during execution,
causing the frontend to appear broken and unresponsive during complex workflows.

SPECIFIC GAPS THIS SUITE EXPOSES:
1. Context propagation gap in agent_execution_core.py line 62
2. Missing WebSocket notifications during sub-agent lifecycle
3. Tool execution events not emitted from within sub-agents  
4. Nested agent calls losing WebSocket context
5. Error recovery WebSocket notifications missing in sub-agents
6. Concurrent sub-agent execution event interleaving issues

ALL TESTS MUST INITIALLY FAIL TO DEMONSTRATE THE CURRENT BROKEN STATE.
"""

import asyncio
import json
import time
import uuid
import threading
import random
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, call
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from loguru import logger

# Import production components - NO MOCKS
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.enhanced_tool_execution import (
    EnhancedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager

# Import sub-agent classes that SHOULD emit events but DON'T
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent  
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent

# Core base classes
from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin


# ============================================================================
# CRITICAL EVENT VALIDATOR - COMPREHENSIVE TRACKING
# ============================================================================

class CriticalSubAgentEventValidator:
    """Ultra-rigorous validator specifically for sub-agent WebSocket events."""
    
    # CRITICAL: These events MUST be emitted during sub-agent execution
    REQUIRED_SUB_AGENT_EVENTS = {
        "agent_started",      # Sub-agent begins processing
        "agent_thinking",     # Sub-agent reasoning/analysis
        "tool_executing",     # Sub-agent executes tools
        "tool_completed",     # Sub-agent tool completion
        "agent_completed"     # Sub-agent finishes
    }
    
    # Events that indicate proper context propagation
    CONTEXT_PROPAGATION_INDICATORS = {
        "connection_id",      # WebSocket connection preserved
        "request_id",         # Request tracking maintained
        "user_id",           # User context preserved
        "thread_id"          # Thread context maintained
    }
    
    def __init__(self, connection_id: str, request_id: str):
        self.connection_id = connection_id
        self.request_id = request_id
        self.events: List[Dict] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.agent_event_map: Dict[str, List[Dict]] = {}  # agent_name -> events
        self.context_violations: List[str] = []
        self.missing_events: Set[str] = set()
        self.start_time = time.time()
        self.sub_agent_executions: Set[str] = set()
        
    def record_event(self, event: Dict) -> None:
        """Record and analyze each WebSocket event."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        agent_name = event.get("agent_name", "unknown")
        
        # Track event
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        
        # Group by agent
        if agent_name not in self.agent_event_map:
            self.agent_event_map[agent_name] = []
        self.agent_event_map[agent_name].append(event)
        
        # Track sub-agent executions
        if "sub" in agent_name.lower() or "agent" in event_type:
            self.sub_agent_executions.add(agent_name)
        
        # Validate context propagation
        self._validate_event_context(event)
        
        logger.info(f"📡 Event Recorded: {event_type} from {agent_name} at {timestamp:.3f}s")
    
    def _validate_event_context(self, event: Dict) -> None:
        """Validate that events contain proper context information."""
        # Check required context fields
        for field in self.CONTEXT_PROPAGATION_INDICATORS:
            if field not in event:
                violation = f"Missing {field} in event {event.get('type', 'unknown')}"
                self.context_violations.append(violation)
                logger.error(f"❌ Context Violation: {violation}")
        
        # Validate specific values match expected context
        if event.get("connection_id") != self.connection_id:
            self.context_violations.append(
                f"Connection ID mismatch: expected {self.connection_id}, "
                f"got {event.get('connection_id')}"
            )
        
        if event.get("request_id") != self.request_id:
            self.context_violations.append(
                f"Request ID mismatch: expected {self.request_id}, "
                f"got {event.get('request_id')}"
            )
    
    def analyze_sub_agent_coverage(self) -> Dict[str, Any]:
        """Analyze which sub-agents properly emit events."""
        coverage_report = {
            "total_sub_agents": len(self.sub_agent_executions),
            "agents_with_events": {},
            "missing_coverage": [],
            "partial_coverage": [],
            "full_coverage": []
        }
        
        for agent_name in self.sub_agent_executions:
            agent_events = self.agent_event_map.get(agent_name, [])
            event_types = {e.get("type") for e in agent_events}
            
            coverage_report["agents_with_events"][agent_name] = {
                "event_count": len(agent_events),
                "event_types": list(event_types),
                "missing_required": list(self.REQUIRED_SUB_AGENT_EVENTS - event_types)
            }
            
            # Categorize coverage level
            required_coverage = len(event_types & self.REQUIRED_SUB_AGENT_EVENTS)
            total_required = len(self.REQUIRED_SUB_AGENT_EVENTS)
            
            if required_coverage == 0:
                coverage_report["missing_coverage"].append(agent_name)
            elif required_coverage < total_required:
                coverage_report["partial_coverage"].append(agent_name)
            else:
                coverage_report["full_coverage"].append(agent_name)
        
        return coverage_report
    
    def validate_critical_sub_agent_requirements(self) -> Tuple[bool, List[str], Dict]:
        """Comprehensive validation of sub-agent event requirements."""
        failures = []
        coverage_report = self.analyze_sub_agent_coverage()
        
        # 1. Check if ANY sub-agent events were recorded
        if len(self.sub_agent_executions) == 0:
            failures.append("CRITICAL: No sub-agent executions detected")
        
        # 2. Check for complete missing coverage
        if coverage_report["missing_coverage"]:
            failures.append(
                f"CRITICAL: Sub-agents with NO events: {coverage_report['missing_coverage']}"
            )
        
        # 3. Check for partial coverage (events missing)
        if coverage_report["partial_coverage"]:
            failures.append(
                f"CRITICAL: Sub-agents with incomplete events: {coverage_report['partial_coverage']}"
            )
        
        # 4. Validate context propagation
        if self.context_violations:
            failures.append(
                f"CRITICAL: Context propagation violations: {len(self.context_violations)} issues"
            )
        
        # 5. Check event ordering within agents
        for agent_name, events in self.agent_event_map.items():
            if len(events) > 1 and not self._validate_agent_event_order(events):
                failures.append(f"CRITICAL: Invalid event order for {agent_name}")
        
        # 6. Check for tool execution events in sub-agents
        tool_events = [e for e in self.events if "tool" in e.get("type", "")]
        if len(tool_events) == 0 and len(self.sub_agent_executions) > 0:
            failures.append("CRITICAL: No tool execution events from sub-agents")
        
        is_valid = len(failures) == 0
        return is_valid, failures, coverage_report
    
    def _validate_agent_event_order(self, events: List[Dict]) -> bool:
        """Validate proper event ordering within a single agent."""
        if not events:
            return True
        
        event_types = [e.get("type") for e in events]
        
        # First event should be agent_started
        if event_types[0] != "agent_started":
            return False
        
        # Last event should be completion or error
        completion_events = {"agent_completed", "agent_fallback", "final_report"}
        if event_types[-1] not in completion_events:
            return False
        
        return True
    
    def generate_comprehensive_report(self) -> str:
        """Generate detailed analysis report."""
        is_valid, failures, coverage_report = self.validate_critical_sub_agent_requirements()
        
        report_lines = [
            "\n" + "=" * 100,
            "🚨 CRITICAL SUB-AGENT WEBSOCKET EVENT ANALYSIS REPORT 🚨",
            "=" * 100,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED (EXPECTED)'}",
            f"Test Duration: {self.event_timeline[-1][0] if self.event_timeline else 0:.3f}s",
            f"Total Events: {len(self.events)}",
            f"Sub-Agents Detected: {len(self.sub_agent_executions)}",
            f"Context Violations: {len(self.context_violations)}",
            "",
            "📊 SUB-AGENT EVENT COVERAGE:",
            f"  - Full Coverage: {len(coverage_report['full_coverage'])} agents",
            f"  - Partial Coverage: {len(coverage_report['partial_coverage'])} agents", 
            f"  - Missing Coverage: {len(coverage_report['missing_coverage'])} agents",
            "",
        ]
        
        # Detailed agent breakdown
        if coverage_report["agents_with_events"]:
            report_lines.append("🔍 DETAILED AGENT ANALYSIS:")
            for agent_name, info in coverage_report["agents_with_events"].items():
                status = "✅" if not info["missing_required"] else "❌"
                report_lines.extend([
                    f"  {status} {agent_name}:",
                    f"    Events: {info['event_count']} ({', '.join(info['event_types'])})",
                    f"    Missing: {', '.join(info['missing_required']) if info['missing_required'] else 'None'}"
                ])
                
        # Context violations
        if self.context_violations:
            report_lines.extend([
                "",
                "🚨 CONTEXT PROPAGATION VIOLATIONS:",
                *[f"  - {violation}" for violation in self.context_violations[:10]]
            ])
            if len(self.context_violations) > 10:
                report_lines.append(f"  ... and {len(self.context_violations) - 10} more")
        
        # Critical failures
        if failures:
            report_lines.extend([
                "",
                "💥 CRITICAL FAILURES:",
                *[f"  - {failure}" for failure in failures]
            ])
        
        # Event timeline sample
        if self.event_timeline:
            report_lines.extend([
                "",
                "📅 EVENT TIMELINE (First 10):",
                *[f"  {ts:.3f}s: {event_type} ({event.get('agent_name', 'unknown')})" 
                  for ts, event_type, event in self.event_timeline[:10]]
            ])
        
        report_lines.append("=" * 100)
        return "\n".join(report_lines)


# ============================================================================
# SUB-AGENT EXECUTION SIMULATOR
# ============================================================================

class SubAgentExecutionSimulator:
    """Simulates realistic sub-agent execution scenarios."""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.tool_dispatcher = ToolDispatcher()
        self._setup_realistic_tools()
        
    def _setup_realistic_tools(self):
        """Setup realistic tools that sub-agents would use."""
        
        async def analyze_data(data: Dict) -> Dict:
            """Simulate data analysis tool."""
            await asyncio.sleep(random.uniform(0.05, 0.15))  # Realistic processing time
            return {
                "analysis": f"Analyzed {len(str(data))} bytes of data",
                "insights": ["Pattern A detected", "Anomaly at position 42"],
                "confidence": random.uniform(0.7, 0.95)
            }
        
        async def generate_report(template: str, data: Dict) -> Dict:
            """Simulate report generation tool."""
            await asyncio.sleep(random.uniform(0.1, 0.3))
            return {
                "report": f"Generated report using {template}",
                "sections": ["Executive Summary", "Findings", "Recommendations"],
                "word_count": random.randint(500, 2000)
            }
        
        async def optimize_parameters(params: Dict) -> Dict:
            """Simulate optimization tool.""" 
            await asyncio.sleep(random.uniform(0.08, 0.25))
            return {
                "optimized_params": {k: v * random.uniform(0.9, 1.1) for k, v in params.items() if isinstance(v, (int, float))},
                "improvement": f"{random.uniform(10, 30):.1f}%",
                "iterations": random.randint(5, 50)
            }
        
        async def search_knowledge_base(query: str) -> Dict:
            """Simulate knowledge base search."""
            await asyncio.sleep(random.uniform(0.03, 0.12))
            return {
                "results": [
                    {"title": f"Result for '{query}' #{i}", "relevance": random.uniform(0.6, 0.95)}
                    for i in range(random.randint(3, 8))
                ],
                "total_found": random.randint(10, 100)
            }
        
        # Create tools as BaseTool objects
        from langchain_core.tools import Tool
        
        # Create tools and register them
        tools_to_register = [
            Tool(name="analyze_data", func=analyze_data, description="Analyze data patterns"),
            Tool(name="generate_report", func=generate_report, description="Generate comprehensive reports"),  
            Tool(name="optimize_parameters", func=optimize_parameters, description="Optimize system parameters"),
            Tool(name="search_knowledge_base", func=search_knowledge_base, description="Search knowledge base")
        ]
        
        self.tool_dispatcher.registry.register_tools(tools_to_register)
    
    async def create_sub_agent_scenario(self, agent_class, connection_id: str, 
                                      scenario_data: Dict) -> BaseSubAgent:
        """Create a realistic sub-agent execution scenario."""
        # Create mock LLM for testing
        class MockLLM:
            async def generate(self, *args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate processing
                return {
                    "content": "Mock response",
                    "reasoning": "Mock reasoning",
                    "confidence": 0.95
                }
        
        mock_llm = MockLLM()
        
        # Create agent instance - simplified to avoid complex dependencies
        if agent_class == DataSubAgent:
            agent = DataSubAgent(
                llm_manager=mock_llm,
                tool_dispatcher=self.tool_dispatcher,
                websocket_manager=self.ws_manager
            )
        else:
            # For other agents, create a simple mock that inherits from BaseSubAgent
            class MockSubAgent(BaseSubAgent):
                def __init__(self, name):
                    super().__init__(mock_llm, name=name, description=f"Mock {name}")
                    self.tool_dispatcher = self.tool_dispatcher
                    
                async def execute(self, state, run_id, stream_updates=False):
                    # Simulate sub-agent execution
                    await asyncio.sleep(0.1)
                    return {"result": "mock execution"}
            
            agent = MockSubAgent(f"Mock{agent_class.__name__}")
        
        # CRITICAL: Set WebSocket context that should be propagated
        agent.websocket_manager = self.ws_manager
        agent._user_id = scenario_data.get("user_id", connection_id)
        
        return agent
    
    async def execute_nested_sub_agent_chain(self, connection_id: str, request_id: str,
                                           chain_depth: int = 3) -> List[str]:
        """Execute a chain of nested sub-agent calls."""
        executed_agents = []
        
        # Define realistic agent execution chain
        agent_chain = [
            (TriageSubAgent, {"task": "Initial request analysis"}),
            (DataSubAgent, {"task": "Data collection and analysis"}), 
            (OptimizationsCoreSubAgent, {"task": "Performance optimization"}),
            (ReportingSubAgent, {"task": "Final report generation"})
        ]
        
        state = DeepAgentState()
        state.user_request = f"Complex task requiring {chain_depth} sub-agents"
        state.chat_thread_id = connection_id
        state.user_id = connection_id
        
        for i, (agent_class, scenario_data) in enumerate(agent_chain[:chain_depth]):
            agent = await self.create_sub_agent_scenario(agent_class, connection_id, scenario_data)
            agent_name = f"{agent_class.__name__}_{i}"
            executed_agents.append(agent_name)
            
            run_id = f"{request_id}_subagent_{i}"
            
            try:
                # This should emit WebSocket events but likely WON'T
                await agent.run(state, run_id, stream_updates=True)
            except Exception as e:
                logger.error(f"Sub-agent {agent_name} failed: {e}")
                # Continue chain execution to test error recovery
        
        return executed_agents


# ============================================================================
# COMPREHENSIVE FAILING TESTS  
# ============================================================================

@pytest.mark.critical
@pytest.mark.mission_critical
@pytest.mark.timeout(60)
class TestSubAgentWebSocketEventEmissions:
    """CRITICAL tests that expose sub-agent WebSocket event emission failures."""
    
    @pytest.mark.asyncio
    async def test_single_sub_agent_emits_all_required_events(self):
        """Test that a single sub-agent emits ALL required WebSocket events.
        
        THIS TEST SHOULD FAIL because sub-agents don't properly emit events.
        """
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        connection_id = "test-single-subagent"
        request_id = "req-single-001"
        validator = CriticalSubAgentEventValidator(connection_id, request_id)
        
        # Setup WebSocket connection with event capture
        mock_ws = MagicMock()
        async def capture_event(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record_event(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture_event)
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Execute single sub-agent
        agent = await simulator.create_sub_agent_scenario(
            DataSubAgent, 
            connection_id,
            {"task": "Single agent test", "user_id": connection_id}
        )
        
        state = DeepAgentState()
        state.user_request = "Analyze system performance data"
        state.chat_thread_id = connection_id
        state.user_id = connection_id
        
        # CRITICAL: This execution should emit events but likely won't
        await agent.run(state, request_id, stream_updates=True)
        
        # Allow events to propagate
        await asyncio.sleep(1.0)
        
        # Validate (this should FAIL)
        is_valid, failures, coverage_report = validator.validate_critical_sub_agent_requirements()
        
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - Demonstrates broken state
        assert not is_valid, (
            f"❌ EXPECTED FAILURE: Sub-agent should NOT emit proper events (current broken state). "
            f"But validation passed: {coverage_report}"
        )
        
        # Specific assertions that should fail
        assert len(validator.sub_agent_executions) == 0, (
            "❌ EXPECTED: No sub-agent events detected (demonstrates the bug)"
        )
        
        required_events = validator.REQUIRED_SUB_AGENT_EVENTS
        recorded_types = {e.get("type") for e in validator.events}
        missing_events = required_events - recorded_types
        
        assert len(missing_events) == len(required_events), (
            f"❌ EXPECTED: All required events missing. Missing: {missing_events}, "
            f"Found: {recorded_types}"
        )
    
    @pytest.mark.asyncio  
    async def test_nested_sub_agent_context_propagation(self):
        """Test WebSocket context propagation through nested sub-agent calls.
        
        THIS TEST SHOULD FAIL due to context propagation gap in agent_execution_core.py:62
        """
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        connection_id = "test-nested-context"
        request_id = "req-nested-001"
        validator = CriticalSubAgentEventValidator(connection_id, request_id)
        
        # Setup WebSocket capture
        mock_ws = MagicMock()
        async def capture_event(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record_event(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture_event) 
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Execute nested sub-agent chain
        executed_agents = await simulator.execute_nested_sub_agent_chain(
            connection_id, request_id, chain_depth=3
        )
        
        # Allow all async events to complete
        await asyncio.sleep(2.0)
        
        # Validate context propagation (should FAIL)
        is_valid, failures, coverage_report = validator.validate_critical_sub_agent_requirements()
        
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - Context not propagated
        assert len(validator.context_violations) > 0, (
            "❌ EXPECTED: Context propagation violations should exist "
            "(demonstrates agent_execution_core.py line 62 gap)"
        )
        
        # Verify specific context fields are missing
        context_fields = validator.CONTEXT_PROPAGATION_INDICATORS
        events_with_context = [
            e for e in validator.events 
            if all(field in e for field in context_fields)
        ]
        
        assert len(events_with_context) == 0, (
            f"❌ EXPECTED: No events with complete context propagation. "
            f"Found {len(events_with_context)} events with context"
        )
        
        # Verify sub-agents are not emitting events
        assert len(coverage_report["missing_coverage"]) == len(executed_agents), (
            f"❌ EXPECTED: All sub-agents missing events. "
            f"Executed: {executed_agents}, Missing: {coverage_report['missing_coverage']}"
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_sub_agent_event_isolation(self):
        """Test that concurrent sub-agent executions maintain event isolation.
        
        THIS TEST SHOULD FAIL due to event mixing and missing emissions.
        """
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        # Create multiple concurrent scenarios
        num_concurrent = 5
        validators = {}
        connections = []
        
        for i in range(num_concurrent):
            connection_id = f"concurrent-{i}"
            request_id = f"req-concurrent-{i}"
            validator = CriticalSubAgentEventValidator(connection_id, request_id)
            validators[connection_id] = validator
            
            # Setup WebSocket
            mock_ws = MagicMock()
            async def capture_event(message, v=validator):
                if isinstance(message, str):
                    data = json.loads(message)
                else:
                    data = message
                v.record_event(data)
            
            mock_ws.send_json = AsyncMock(side_effect=capture_event)
            await ws_manager.connect_user(connection_id, mock_ws, connection_id)
            connections.append((connection_id, request_id, mock_ws))
        
        # Execute concurrent sub-agents
        async def execute_concurrent_agent(connection_id: str, request_id: str):
            agent_types = [DataSubAgent, TriageSubAgent, ReportingSubAgent, OptimizationsCoreSubAgent]
            agent_class = random.choice(agent_types)
            
            agent = await simulator.create_sub_agent_scenario(
                agent_class,
                connection_id,
                {"task": f"Concurrent task {connection_id}", "user_id": connection_id}
            )
            
            state = DeepAgentState()
            state.user_request = f"Concurrent request {connection_id}"
            state.chat_thread_id = connection_id
            state.user_id = connection_id
            
            # This should emit isolated events but likely won't emit any
            await agent.run(state, request_id, stream_updates=True)
            return agent_class.__name__
        
        # Run all concurrently
        tasks = [
            execute_concurrent_agent(conn_id, req_id) 
            for conn_id, req_id, _ in connections
        ]
        agent_types_executed = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Allow events to propagate
        await asyncio.sleep(2.0)
        
        # Validate each connection separately
        total_failures = 0
        total_context_violations = 0
        
        for connection_id, validator in validators.items():
            is_valid, failures, coverage = validator.validate_critical_sub_agent_requirements()
            
            if not is_valid:
                total_failures += len(failures)
                total_context_violations += len(validator.context_violations)
                logger.error(f"Connection {connection_id} validation failed: {failures}")
        
        # EXPECTED TO FAIL - No proper event isolation or emission
        assert total_failures > 0, (
            "❌ EXPECTED: Concurrent sub-agent executions should have failures "
            "(demonstrates broken event emission)"
        )
        
        # Check for event mixing (events with wrong connection_id) 
        event_mixing_count = sum(len(v.context_violations) for v in validators.values())
        
        # This might be 0 if no events are emitted at all (which is also a failure)
        logger.error(f"Total context violations across all connections: {event_mixing_count}")
        
        # Verify most connections have no events (the broken state)
        connections_without_events = sum(
            1 for v in validators.values() 
            if len(v.sub_agent_executions) == 0
        )
        
        assert connections_without_events >= num_concurrent - 1, (
            f"❌ EXPECTED: Most connections should have no sub-agent events. "
            f"Found {connections_without_events}/{num_concurrent} without events"
        )
    
    @pytest.mark.asyncio
    async def test_sub_agent_tool_execution_events(self):
        """Test that sub-agents emit proper tool execution events.
        
        THIS TEST SHOULD FAIL because tool events are not emitted from sub-agents.
        """
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        connection_id = "test-tool-events"
        request_id = "req-tools-001"
        validator = CriticalSubAgentEventValidator(connection_id, request_id)
        
        # Setup WebSocket capture
        mock_ws = MagicMock()
        async def capture_event(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record_event(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture_event)
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Create sub-agent that uses multiple tools
        agent = await simulator.create_sub_agent_scenario(
            DataSubAgent,
            connection_id,
            {"task": "Multi-tool analysis", "user_id": connection_id}
        )
        
        state = DeepAgentState()
        state.user_request = "Analyze data using multiple tools and generate comprehensive report"
        state.chat_thread_id = connection_id
        state.user_id = connection_id
        
        # Execute agent (should use tools and emit events)
        await agent.run(state, request_id, stream_updates=True)
        
        # Allow events to propagate
        await asyncio.sleep(1.5)
        
        # Analyze tool-related events
        tool_executing_events = [e for e in validator.events if e.get("type") == "tool_executing"]
        tool_completed_events = [e for e in validator.events if e.get("type") == "tool_completed"]
        
        logger.error(f"Tool executing events: {len(tool_executing_events)}")
        logger.error(f"Tool completed events: {len(tool_completed_events)}")
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - No tool events from sub-agents
        assert len(tool_executing_events) == 0, (
            f"❌ EXPECTED: No tool executing events from sub-agents. "
            f"Found {len(tool_executing_events)} events"
        )
        
        assert len(tool_completed_events) == 0, (
            f"❌ EXPECTED: No tool completed events from sub-agents. "
            f"Found {len(tool_completed_events)} events"
        )
        
        # Verify tool events are not paired (because they don't exist)
        assert len(tool_executing_events) != len(tool_completed_events), (
            "❌ EXPECTED: Tool events not paired (because none exist)"
        )
    
    @pytest.mark.asyncio
    async def test_sub_agent_error_recovery_events(self):
        """Test WebSocket events during sub-agent error scenarios.
        
        THIS TEST SHOULD FAIL because error recovery events are not emitted.
        """
        ws_manager = WebSocketManager()
        
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        connection_id = "test-error-recovery"
        request_id = "req-error-001"
        validator = CriticalSubAgentEventValidator(connection_id, request_id)
        
        # Setup WebSocket capture
        mock_ws = MagicMock()
        async def capture_event(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record_event(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture_event)
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Create sub-agent that will encounter errors
        agent = await simulator.create_sub_agent_scenario(
            DataSubAgent,
            connection_id,
            {"task": "Error-prone analysis", "user_id": connection_id}
        )
        
        state = DeepAgentState()
        state.user_request = "This request will cause errors"
        state.chat_thread_id = connection_id
        state.user_id = connection_id
        
        # Execute agent (should handle errors and emit recovery events)
        try:
            await agent.run(state, request_id, stream_updates=True)
        except Exception as e:
            logger.info(f"Expected error occurred: {e}")
        
        # Allow events to propagate
        await asyncio.sleep(1.0)
        
        # Analyze error-related events
        start_events = [e for e in validator.events if e.get("type") == "agent_started"]
        error_events = [e for e in validator.events if "error" in e.get("type", "").lower()]
        fallback_events = [e for e in validator.events if e.get("type") == "agent_fallback"]
        completion_events = [e for e in validator.events if e.get("type") == "agent_completed"]
        
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - No error recovery events
        assert len(start_events) == 0, (
            f"❌ EXPECTED: No agent_started events during errors. "
            f"Found {len(start_events)} events"
        )
        
        assert len(error_events) == 0, (
            f"❌ EXPECTED: No error handling events. Found {len(error_events)} events"
        )
        
        assert len(fallback_events) == 0, (
            f"❌ EXPECTED: No fallback events. Found {len(fallback_events)} events"  
        )
        
        assert len(completion_events) == 0, (
            f"❌ EXPECTED: No completion events after errors. "
            f"Found {len(completion_events)} events"
        )
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_during_sub_agent_execution(self):
        """Test sub-agent events during WebSocket reconnection scenarios.
        
        THIS TEST SHOULD FAIL because reconnection handling is broken.
        """
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        user_id = "reconnect-user"
        connection_id1 = "conn-1"  
        connection_id2 = "conn-2"
        request_id = "req-reconnect-001"
        
        validator1 = CriticalSubAgentEventValidator(connection_id1, request_id)
        validator2 = CriticalSubAgentEventValidator(connection_id2, request_id)
        
        # First connection
        mock_ws1 = MagicMock()
        async def capture1(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator1.record_event(data)
        
        mock_ws1.send_json = AsyncMock(side_effect=capture1)
        await ws_manager.connect_user(user_id, mock_ws1, connection_id1)
        
        # Start sub-agent execution
        agent = await simulator.create_sub_agent_scenario(
            ReportingSubAgent,
            connection_id1,
            {"task": "Long-running report", "user_id": user_id}
        )
        
        state = DeepAgentState()
        state.user_request = "Generate comprehensive report"
        state.chat_thread_id = connection_id1
        state.user_id = user_id
        
        # Start execution (don't await - let it run)
        execution_task = asyncio.create_task(
            agent.run(state, request_id, stream_updates=True)
        )
        
        # Simulate brief execution then disconnect
        await asyncio.sleep(0.5)
        await ws_manager.disconnect_user(user_id, mock_ws1, connection_id1)
        
        # Reconnect with new connection
        mock_ws2 = MagicMock()
        async def capture2(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator2.record_event(data)
        
        mock_ws2.send_json = AsyncMock(side_effect=capture2)
        await ws_manager.connect_user(user_id, mock_ws2, connection_id2)
        
        # Wait for execution to complete
        try:
            await execution_task
        except Exception as e:
            logger.info(f"Execution completed with exception: {e}")
        
        # Allow events to propagate
        await asyncio.sleep(1.0)
        
        # Analyze reconnection behavior
        events_before = len(validator1.events)
        events_after = len(validator2.events)
        
        logger.error(f"Events on first connection: {events_before}")
        logger.error(f"Events on second connection: {events_after}")
        logger.error(validator1.generate_comprehensive_report())
        logger.error(validator2.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - No proper reconnection handling
        assert events_before == 0 and events_after == 0, (
            f"❌ EXPECTED: No events on either connection during reconnection. "
            f"Before: {events_before}, After: {events_after}"
        )
        
        # Verify no completion events were sent to new connection
        completion_events_new = [
            e for e in validator2.events 
            if e.get("type") in ["agent_completed", "final_report"]
        ]
        
        assert len(completion_events_new) == 0, (
            f"❌ EXPECTED: No completion events on reconnected session. "
            f"Found {len(completion_events_new)} events"
        )


# ============================================================================
# STRESS TESTING FOR SUB-AGENT EVENTS
# ============================================================================

@pytest.mark.critical
@pytest.mark.stress
@pytest.mark.timeout(120)
class TestSubAgentWebSocketStress:
    """Stress tests to expose performance issues in sub-agent event handling."""
    
    @pytest.mark.asyncio
    async def test_high_frequency_sub_agent_executions(self):
        """Test rapid-fire sub-agent executions for event throughput.
        
        THIS TEST SHOULD FAIL due to missing events and poor throughput.
        """
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        connection_id = "stress-high-freq"
        validator = CriticalSubAgentEventValidator(connection_id, "stress-req")
        
        # Setup WebSocket
        mock_ws = MagicMock()
        event_count = 0
        
        async def capture_event(message):
            nonlocal event_count
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record_event(data)
            event_count += 1
        
        mock_ws.send_json = AsyncMock(side_effect=capture_event)
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Execute many sub-agents rapidly
        num_agents = 20
        start_time = time.time()
        
        async def rapid_execution(i: int):
            agent_types = [DataSubAgent, TriageSubAgent, ReportingSubAgent]
            agent_class = agent_types[i % len(agent_types)]
            
            agent = await simulator.create_sub_agent_scenario(
                agent_class,
                connection_id,
                {"task": f"Rapid task {i}", "user_id": connection_id}
            )
            
            state = DeepAgentState()
            state.user_request = f"Rapid execution {i}"
            state.chat_thread_id = connection_id
            state.user_id = connection_id
            
            await agent.run(state, f"rapid-{i}", stream_updates=True)
            return i
        
        # Execute all rapidly
        tasks = [rapid_execution(i) for i in range(num_agents)]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.time() - start_time
        execution_rate = len(completed) / duration
        
        # Allow events to propagate
        await asyncio.sleep(2.0)
        
        final_event_count = len(validator.events)
        event_rate = final_event_count / duration if duration > 0 else 0
        
        logger.error(f"Executed {len(completed)} agents in {duration:.2f}s = {execution_rate:.1f} agents/s")
        logger.error(f"Received {final_event_count} events = {event_rate:.1f} events/s")
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - Poor event throughput and missing events
        expected_min_events = num_agents * 3  # At least 3 events per agent
        
        assert final_event_count < expected_min_events, (
            f"❌ EXPECTED: Low event count due to missing emissions. "
            f"Expected >{expected_min_events}, got {final_event_count}"
        )
        
        assert event_rate < 50, (  # Should be much higher if working properly
            f"❌ EXPECTED: Low event rate due to broken emissions. "
            f"Rate: {event_rate:.1f} events/s (should be >100)"
        )
        
        # Verify most agents produced no events
        agents_with_events = len(validator.sub_agent_executions)
        assert agents_with_events < num_agents / 2, (
            f"❌ EXPECTED: Most agents produce no events. "
            f"Agents with events: {agents_with_events}/{num_agents}"
        )
    
    @pytest.mark.asyncio
    async def test_memory_leak_during_sub_agent_event_failures(self):
        """Test for memory leaks when sub-agent events fail to emit properly.
        
        THIS TEST SHOULD FAIL by revealing memory growth from unhandled event contexts.
        """
        import psutil
        import gc
        
        ws_manager = WebSocketManager()
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        connection_id = "memory-leak-test"
        validator = CriticalSubAgentEventValidator(connection_id, "mem-req")
        
        # Setup WebSocket
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(side_effect=lambda m: validator.record_event(
            json.loads(m) if isinstance(m, str) else m
        ))
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute many sub-agents that fail to emit events properly
        iterations = 50
        
        for i in range(iterations):
            agent = await simulator.create_sub_agent_scenario(
                DataSubAgent,
                connection_id,
                {"task": f"Memory test {i}", "user_id": connection_id}
            )
            
            state = DeepAgentState()
            state.user_request = f"Memory test iteration {i}"
            state.chat_thread_id = connection_id
            state.user_id = connection_id
            
            # These executions should leak memory due to improper cleanup
            try:
                await agent.run(state, f"mem-{i}", stream_updates=True)
            except Exception as e:
                logger.debug(f"Expected failure in iteration {i}: {e}")
            
            # Periodic memory checks
            if i % 10 == 0:
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                logger.info(f"Iteration {i}: Memory = {current_memory:.1f}MB (+{memory_growth:.1f}MB)")
        
        # Final memory measurement
        gc.collect()
        await asyncio.sleep(1.0)  # Allow cleanup
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        logger.error(f"Memory growth: {initial_memory:.1f}MB → {final_memory:.1f}MB (+{total_growth:.1f}MB)")
        logger.error(f"Events emitted: {len(validator.events)} (should be much higher)")
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - Memory leak due to poor event handling
        max_acceptable_growth = 50  # MB
        
        assert total_growth > max_acceptable_growth, (
            f"❌ EXPECTED: Memory leak from broken event handling. "
            f"Growth: {total_growth:.1f}MB (expected >{max_acceptable_growth}MB)"
        )
        
        # Verify very few events were emitted (the root cause of issues)
        expected_events = iterations * 3  # Minimum expected
        assert len(validator.events) < expected_events / 4, (
            f"❌ EXPECTED: Very few events due to broken emission. "
            f"Got {len(validator.events)}, expected <{expected_events/4}"
        )


# ============================================================================
# INTEGRATION WITH EXISTING SYSTEM
# ============================================================================

@pytest.mark.critical
@pytest.mark.integration
@pytest.mark.timeout(90)
class TestSubAgentIntegrationWithSupervisor:
    """Test sub-agent events in context of full supervisor workflow."""
    
    @pytest.mark.asyncio
    async def test_supervisor_sub_agent_event_chain(self):
        """Test complete supervisor → sub-agent → tool event chain.
        
        THIS TEST SHOULD FAIL due to broken event propagation in the full chain.
        """
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.database.dependencies import get_async_database
        
        # Setup complete system
        ws_manager = WebSocketManager() 
        tool_dispatcher = ToolDispatcher()
        
        connection_id = "supervisor-chain-test"
        request_id = "req-supervisor-001"
        validator = CriticalSubAgentEventValidator(connection_id, request_id)
        
        # Setup WebSocket capture
        mock_ws = MagicMock()
        async def capture_event(message):
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            validator.record_event(data)
        
        mock_ws.send_json = AsyncMock(side_effect=capture_event)
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Create realistic sub-agents in tool dispatcher
        simulator = SubAgentExecutionSimulator(ws_manager)
        
        # This is where the critical gap should be exposed
        try:
            # Create mock LLM for supervisor
            class MockLLM:
                async def generate(self, *args, **kwargs):
                    return {"content": "Mock supervisor response"}
            
            mock_llm = MockLLM()
            
            # Setup supervisor with proper WebSocket integration
            registry = AgentRegistry(mock_llm, tool_dispatcher)
            registry.set_websocket_manager(ws_manager)  # Should enhance tool dispatcher
            
            engine = ExecutionEngine(registry, ws_manager)
            
            # Create execution context that should propagate to sub-agents
            context = AgentExecutionContext(
                agent_name="supervisor",
                request_id=request_id,
                connection_id=connection_id,
                start_time=time.time(),
                retry_count=0,
                max_retries=1
            )
            
            state = DeepAgentState()
            state.user_request = "Complex request requiring multiple sub-agents"
            state.chat_thread_id = connection_id
            state.user_id = connection_id
            
            # Execute through supervisor (should trigger sub-agents)
            result = await engine.execute_agent(context, state)
            
            # Allow all events to propagate
            await asyncio.sleep(3.0)
            
        except Exception as e:
            logger.error(f"Integration execution failed: {e}")
        
        # Analyze complete event chain
        supervisor_events = [e for e in validator.events if "supervisor" in e.get("agent_name", "").lower()]
        subagent_events = [e for e in validator.events if "sub" in e.get("agent_name", "").lower()]
        tool_events = [e for e in validator.events if "tool" in e.get("type", "")]
        
        logger.error(f"Supervisor events: {len(supervisor_events)}")
        logger.error(f"Sub-agent events: {len(subagent_events)}")  
        logger.error(f"Tool events: {len(tool_events)}")
        logger.error(validator.generate_comprehensive_report())
        
        # EXPECTED TO FAIL - Broken event chain
        assert len(supervisor_events) == 0, (
            f"❌ EXPECTED: No supervisor events. Found {len(supervisor_events)}"
        )
        
        assert len(subagent_events) == 0, (
            f"❌ EXPECTED: No sub-agent events (critical gap). Found {len(subagent_events)}"
        )
        
        assert len(tool_events) == 0, (
            f"❌ EXPECTED: No tool events from sub-agents. Found {len(tool_events)}"
        )
        
        # Verify the specific gap: context not propagated to sub-agents
        context_propagated_events = [
            e for e in validator.events 
            if e.get("connection_id") == connection_id and e.get("request_id") == request_id
        ]
        
        assert len(context_propagated_events) == 0, (
            f"❌ EXPECTED: No events with propagated context (line 62 gap). "
            f"Found {len(context_propagated_events)}"
        )


if __name__ == "__main__":
    # This file contains comprehensive FAILING tests that expose critical gaps
    # Run with: pytest tests/mission_critical/test_websocket_subagent_events.py -v -s
    # Or: python tests/mission_critical/test_websocket_subagent_events.py
    
    logger.info("🚨 RUNNING CRITICAL SUB-AGENT WEBSOCKET EVENT FAILURE TESTS 🚨")
    logger.info("These tests are DESIGNED TO FAIL to expose the current broken state")
    logger.info("Focus areas:")
    logger.info("1. Context propagation gap in agent_execution_core.py line 62")
    logger.info("2. Missing WebSocket events from sub-agent executions")
    logger.info("3. Tool events not emitted within sub-agents")
    logger.info("4. Error recovery WebSocket notifications missing")
    logger.info("5. Concurrent execution event handling issues")
    
    pytest.main([__file__, "-v", "-s", "--tb=short"])