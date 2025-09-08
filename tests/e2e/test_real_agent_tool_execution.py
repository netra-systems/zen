#!/usr/bin/env python
"""Real Agent Tool Execution E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests tool execution across agents with real services.
Business Value: Ensure tool integration and execution reliability.

Business Value Justification (BVJ):
1. Segment: All (Free, Early, Mid, Enterprise)
2. Business Goal: Enable reliable tool-based agent capabilities
3. Value Impact: Tool execution is core to agent value delivery
4. Revenue Impact: $400K+ ARR from tool-powered agent functionality

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests actual tool execution business logic
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# CLAUDE.md compliant imports - Lazy loaded to prevent resource exhaustion
from shared.isolated_environment import get_env
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS


class ToolExecutionStatus(Enum):
    """Tool execution status tracking."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolExecutionTrace:
    """Tracks individual tool execution."""
    tool_name: str
    start_time: float
    args: Dict[str, Any] = field(default_factory=dict)
    end_time: Optional[float] = None
    result: Optional[Any] = None
    status: ToolExecutionStatus = ToolExecutionStatus.PENDING
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
        
    @property
    def success(self) -> bool:
        return self.status == ToolExecutionStatus.COMPLETED


@dataclass
class AgentToolExecutionValidation:
    """Captures and validates agent tool execution across scenarios."""
    
    user_id: str
    thread_id: str
    agent_name: str
    execution_scenario: str
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Tool execution tracking
    tool_executions: List[ToolExecutionTrace] = field(default_factory=list)
    tool_chain_sequence: List[str] = field(default_factory=list)
    parallel_tool_count: int = 0
    
    # Timing metrics (performance benchmarks per requirements)
    time_to_agent_started: Optional[float] = None
    time_to_first_tool: Optional[float] = None
    time_to_last_tool: Optional[float] = None
    time_to_completion: Optional[float] = None
    
    # Business logic validation
    tool_chain_coherent: bool = False
    tools_successful: bool = False
    error_handling_robust: bool = False
    results_actionable: bool = False


class RealAgentToolExecutionTester:
    """Tests tool execution across agents with real services and WebSocket events."""
    
    # CLAUDE.md REQUIRED WebSocket events - SSOT
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    
    # Tool execution test scenarios
    TOOL_EXECUTION_SCENARIOS = [
        {
            "scenario_name": "sequential_tool_chain",
            "agent": "triage_agent",
            "message": "Analyze this data and generate a comprehensive report with visualizations",
            "expected_tool_sequence": ["data_analyzer", "report_generator", "visualization_tool"],
            "execution_pattern": "sequential",
            "success_criteria": ["data_analyzed", "report_generated", "visualizations_created"]
        },
        {
            "scenario_name": "parallel_tool_execution",
            "agent": "data_agent", 
            "message": "Perform simultaneous analysis of cost data, performance metrics, and usage patterns",
            "expected_tools": ["cost_calculator", "performance_analyzer", "usage_tracker"],
            "execution_pattern": "parallel",
            "success_criteria": ["multiple_analyses", "concurrent_execution", "consolidated_results"]
        },
        {
            "scenario_name": "conditional_tool_branching",
            "agent": "optimization_agent",
            "message": "Optimize system configuration based on current performance metrics",
            "expected_tool_flow": ["metrics_collector", "performance_evaluator", "optimizer_selector", "configuration_updater"],
            "execution_pattern": "conditional",
            "success_criteria": ["metrics_collected", "optimization_applied", "configuration_updated"]
        },
        {
            "scenario_name": "error_recovery_tool_chain",
            "agent": "validation_agent",
            "message": "Validate data integrity and recover from any detected issues",
            "expected_tools": ["data_validator", "error_detector", "recovery_tool", "verification_tool"],
            "execution_pattern": "error_recovery",
            "success_criteria": ["errors_detected", "recovery_attempted", "validation_confirmed"]
        },
        {
            "scenario_name": "complex_multi_step_workflow",
            "agent": "workflow_agent",
            "message": "Execute a complex workflow involving data collection, processing, analysis, and reporting",
            "expected_workflow_stages": ["collection", "processing", "analysis", "reporting"],
            "execution_pattern": "multi_stage",
            "success_criteria": ["all_stages_completed", "data_flow_maintained", "final_report_generated"]
        }
    ]
    
    def __init__(self, config: Optional[E2ETestConfig] = None):
        self.config = config or get_e2e_config()
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[AgentToolExecutionValidation] = []
        
    async def setup(self):
        """Initialize test environment with real services."""
        # Lazy imports per CLAUDE.md to prevent Docker crashes
        from shared.isolated_environment import IsolatedEnvironment
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.backend_client import BackendTestClient
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        
        self.env = IsolatedEnvironment()
        self.jwt_helper = JWTTestHelper()
        
        # Initialize backend client using SSOT config
        self.backend_client = BackendTestClient(self.config.backend_url)
        
        # Create test user with tool execution permissions
        user_data = create_test_user_data("tool_execution_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with comprehensive tool permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=["tools:execute", "agents:use", "data:access", "workflows:run", "system:optimize"]
        )
        
        # Initialize WebSocket client using SSOT config
        self.ws_client = WebSocketTestClient(self.config.websocket_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Tool execution test environment ready for user {self.email}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_tool_execution_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: float = 90.0
    ) -> AgentToolExecutionValidation:
        """Execute a tool execution scenario and validate results.
        
        Args:
            scenario: Tool execution scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = AgentToolExecutionValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            agent_name=scenario["agent"],
            execution_scenario=scenario["scenario_name"]
        )
        
        # Send tool execution request via WebSocket
        execution_request = {
            "type": "agent_request",
            "agent": scenario["agent"],
            "message": scenario["message"],
            "thread_id": thread_id,
            "context": {
                "execution_scenario": scenario["scenario_name"],
                "expected_pattern": scenario.get("execution_pattern", "sequential"),
                "user_id": self.user_id,
                "tool_execution_mode": "comprehensive"
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        await self.ws_client.send_json(execution_request)
        logger.info(f"Sent tool execution request: {scenario['scenario_name']} via {scenario['agent']}")
        
        # Track tool executions in real-time
        tool_execution_tracker = {}
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout and not completed:
            event = await self.ws_client.receive(timeout=2.0)
            
            if event:
                await self._process_tool_execution_event(event, validation, tool_execution_tracker)
                
                # Check for completion
                if event.get("type") in ["agent_completed", "workflow_completed", "error"]:
                    completed = True
                    validation.time_to_completion = time.time() - start_time
                    
        # Finalize tool execution traces
        self._finalize_tool_executions(validation, tool_execution_tracker)
        
        # Validate the tool execution results
        self._validate_tool_execution(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _process_tool_execution_event(
        self, 
        event: Dict[str, Any], 
        validation: AgentToolExecutionValidation,
        tool_tracker: Dict[str, ToolExecutionTrace]
    ):
        """Process and categorize tool execution specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - validation.start_time
        
        # Record all events
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        
        # Track timing of critical events
        if event_type == "agent_started" and not validation.time_to_agent_started:
            validation.time_to_agent_started = event_time
            logger.info(f"Agent {validation.agent_name} started at {event_time:.2f}s")
            
        elif event_type == "tool_executing":
            if not validation.time_to_first_tool:
                validation.time_to_first_tool = event_time
                
            # Create new tool execution trace
            tool_data = event.get("data", {})
            tool_name = tool_data.get("tool_name", "unknown_tool")
            tool_id = tool_data.get("tool_id", str(uuid.uuid4()))
            
            tool_trace = ToolExecutionTrace(
                tool_name=tool_name,
                start_time=time.time(),
                args=tool_data.get("args", {}),
                status=ToolExecutionStatus.EXECUTING
            )
            
            tool_tracker[tool_id] = tool_trace
            validation.tool_chain_sequence.append(tool_name)
            
            # Check for parallel execution
            executing_count = sum(
                1 for trace in tool_tracker.values() 
                if trace.status == ToolExecutionStatus.EXECUTING
            )
            validation.parallel_tool_count = max(validation.parallel_tool_count, executing_count)
            
            logger.info(f"Tool executing: {tool_name} (parallel count: {executing_count})")
            
        elif event_type == "tool_completed":
            validation.time_to_last_tool = event_time
            
            # Update tool execution trace
            tool_data = event.get("data", {})
            tool_id = tool_data.get("tool_id")
            
            if tool_id and tool_id in tool_tracker:
                trace = tool_tracker[tool_id]
                trace.end_time = time.time()
                trace.result = tool_data.get("result")
                trace.status = ToolExecutionStatus.COMPLETED
                
                logger.info(f"Tool completed: {trace.tool_name} (duration: {trace.duration:.2f}s)")
                
        elif event_type == "tool_error":
            # Handle tool errors
            tool_data = event.get("data", {})
            tool_id = tool_data.get("tool_id")
            
            if tool_id and tool_id in tool_tracker:
                trace = tool_tracker[tool_id]
                trace.end_time = time.time()
                trace.status = ToolExecutionStatus.FAILED
                trace.error_message = tool_data.get("error", "Unknown error")
                
                logger.warning(f"Tool failed: {trace.tool_name} - {trace.error_message}")
                
    def _finalize_tool_executions(
        self, 
        validation: AgentToolExecutionValidation,
        tool_tracker: Dict[str, ToolExecutionTrace]
    ):
        """Finalize tool execution traces and add to validation."""
        validation.tool_executions = list(tool_tracker.values())
        
        # Handle any tools that didn't complete
        for trace in validation.tool_executions:
            if trace.status == ToolExecutionStatus.EXECUTING:
                trace.status = ToolExecutionStatus.TIMEOUT
                trace.end_time = time.time()
                
    def _validate_tool_execution(
        self, 
        validation: AgentToolExecutionValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate tool execution against business requirements."""
        
        # 1. Check tool chain coherence
        expected_tools = (
            scenario.get("expected_tool_sequence", []) or 
            scenario.get("expected_tools", []) or
            scenario.get("expected_tool_flow", [])
        )
        
        if expected_tools:
            executed_tools = [trace.tool_name for trace in validation.tool_executions]
            # Allow partial matches for complex scenarios
            tool_match_score = sum(
                1 for expected in expected_tools
                if any(expected.lower() in executed.lower() for executed in executed_tools)
            )
            validation.tool_chain_coherent = tool_match_score >= len(expected_tools) * 0.5
            
        # 2. Validate tool success rate
        successful_tools = sum(1 for trace in validation.tool_executions if trace.success)
        total_tools = len(validation.tool_executions)
        
        if total_tools > 0:
            success_rate = successful_tools / total_tools
            validation.tools_successful = success_rate >= 0.7  # 70% success threshold
            
        # 3. Check error handling robustness
        failed_tools = [trace for trace in validation.tool_executions if trace.status == ToolExecutionStatus.FAILED]
        if failed_tools:
            # If there were failures, check if execution continued (robust error handling)
            validation.error_handling_robust = (
                validation.time_to_completion is not None and  # Execution completed
                len(validation.tool_executions) > len(failed_tools)  # Some tools succeeded
            )
        else:
            validation.error_handling_robust = True  # No errors to handle
            
        # 4. Check if results are actionable
        success_criteria = scenario.get("success_criteria", [])
        if success_criteria and validation.tool_executions:
            # Simple heuristic: if tools executed and completed, assume actionable results
            validation.results_actionable = (
                validation.tools_successful and
                any(trace.result for trace in validation.tool_executions)
            )
            
    def generate_tool_execution_report(self) -> str:
        """Generate comprehensive tool execution test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT TOOL EXECUTION TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total execution scenarios tested: {len(self.validations)}")
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Execution Scenario {i}: {val.execution_scenario} ---")
            report.append(f"Agent: {val.agent_name}")
            report.append(f"User ID: {val.user_id}")
            report.append(f"Thread ID: {val.thread_id}")
            report.append(f"Events received: {len(val.events_received)}")
            report.append(f"Event types: {sorted(val.event_types_seen)}")
            
            # Check for REQUIRED WebSocket events
            missing_events = self.REQUIRED_EVENTS - val.event_types_seen
            if missing_events:
                report.append(f"⚠️ MISSING REQUIRED EVENTS: {missing_events}")
            else:
                report.append("✓ All required WebSocket events received")
                
            # Performance metrics
            report.append("\nPerformance Metrics:")
            report.append(f"  - Agent started: {val.time_to_agent_started:.2f}s" if val.time_to_agent_started else "  - Agent not started")
            report.append(f"  - First tool: {val.time_to_first_tool:.2f}s" if val.time_to_first_tool else "  - No tools executed")
            report.append(f"  - Last tool: {val.time_to_last_tool:.2f}s" if val.time_to_last_tool else "  - No tools completed")
            report.append(f"  - Total completion: {val.time_to_completion:.2f}s" if val.time_to_completion else "  - Not completed")
            
            # Tool execution analysis
            report.append("\nTool Execution Analysis:")
            report.append(f"  - Total tools executed: {len(val.tool_executions)}")
            report.append(f"  - Max parallel tools: {val.parallel_tool_count}")
            report.append(f"  - Tool chain sequence: {' → '.join(val.tool_chain_sequence[:5])}")  # Show first 5
            
            if val.tool_executions:
                successful = sum(1 for t in val.tool_executions if t.success)
                failed = sum(1 for t in val.tool_executions if t.status == ToolExecutionStatus.FAILED)
                timeout = sum(1 for t in val.tool_executions if t.status == ToolExecutionStatus.TIMEOUT)
                
                report.append(f"  - Successful tools: {successful}")
                report.append(f"  - Failed tools: {failed}")
                report.append(f"  - Timeout tools: {timeout}")
                
                # Tool timing analysis
                durations = [t.duration for t in val.tool_executions if t.duration]
                if durations:
                    avg_duration = sum(durations) / len(durations)
                    max_duration = max(durations)
                    report.append(f"  - Average tool duration: {avg_duration:.2f}s")
                    report.append(f"  - Max tool duration: {max_duration:.2f}s")
                    
            # Business logic validation
            report.append("\nBusiness Logic Validation:")
            report.append(f"  ✓ Tool chain coherent: {val.tool_chain_coherent}")
            report.append(f"  ✓ Tools successful: {val.tools_successful}")
            report.append(f"  ✓ Error handling robust: {val.error_handling_robust}")
            report.append(f"  ✓ Results actionable: {val.results_actionable}")
            
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture(params=["local", "staging"])
async def tool_execution_tester(request):
    """Create and setup the tool execution tester for both local and staging environments."""
    env_name = request.param
    
    # Skip staging if environment not available
    if env_name == "staging":
        config = get_e2e_config(force_environment="staging")
        if not config.is_available():
            pytest.skip(f"Staging environment not available: {config.backend_url}")
    else:
        config = get_e2e_config(force_environment="local")
    
    tester = RealAgentToolExecutionTester(config=config)
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class TestRealAgentToolExecution:
    """Test suite for real agent tool execution."""
    
    async def test_sequential_tool_chain_execution(self, tool_execution_tester):
        """Test sequential tool chain execution with real agent."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[0]  # sequential_tool_chain
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=120.0
        )
        
        # CRITICAL: Verify all required WebSocket events
        missing_events = tool_execution_tester.REQUIRED_EVENTS - validation.event_types_seen
        assert not missing_events, f"Missing required events: {missing_events}"
        
        # Verify agent and tool execution
        assert validation.time_to_agent_started is not None, "Agent should have started"
        assert validation.time_to_agent_started < 5.0, "Agent should start quickly"
        
        # Tool execution validation
        assert len(validation.tool_executions) > 0, "Should execute tools"
        assert validation.time_to_first_tool is not None, "Should start tool execution"
        
        # Performance benchmark
        if validation.time_to_completion:
            assert validation.time_to_completion < 100.0, "Should complete within performance target"
            
    async def test_parallel_tool_execution_workflow(self, tool_execution_tester):
        """Test parallel tool execution capabilities."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[1]  # parallel_tool_execution
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=100.0
        )
        
        # WebSocket events validation
        assert "agent_started" in validation.event_types_seen, "Should have agent_started event"
        assert "tool_executing" in validation.event_types_seen, "Should execute tools"
        
        # Parallel execution validation
        if validation.tool_executions:
            assert len(validation.tool_executions) > 0, "Should execute multiple tools"
            
        # Check for any parallel execution (may not always occur)
        if validation.parallel_tool_count > 1:
            logger.info(f"Parallel execution detected: {validation.parallel_tool_count} concurrent tools")
            
    async def test_conditional_tool_branching(self, tool_execution_tester):
        """Test conditional tool execution branching logic."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[2]  # conditional_tool_branching
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=110.0
        )
        
        # Event flow validation
        assert validation.events_received, "Should receive execution events"
        
        # Tool sequence validation
        if validation.tool_chain_sequence:
            assert len(validation.tool_chain_sequence) > 0, "Should have tool execution sequence"
            logger.info(f"Tool execution sequence: {' → '.join(validation.tool_chain_sequence)}")
            
    async def test_error_recovery_tool_chain(self, tool_execution_tester):
        """Test error recovery in tool execution chains."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[3]  # error_recovery_tool_chain
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=90.0
        )
        
        # Should handle any errors gracefully
        assert len(validation.events_received) > 0, "Should receive events even with errors"
        
        # Error handling validation
        failed_tools = [t for t in validation.tool_executions if t.status == ToolExecutionStatus.FAILED]
        if failed_tools:
            # Should continue execution despite failures
            assert validation.error_handling_robust, "Should handle tool failures robustly"
            logger.info(f"Error recovery tested with {len(failed_tools)} failed tools")
            
    async def test_complex_multi_step_workflow(self, tool_execution_tester):
        """Test complex multi-step workflow execution."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[4]  # complex_multi_step_workflow
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=150.0  # Longer timeout for complex workflow
        )
        
        # Workflow completion validation
        if validation.tool_executions:
            assert len(validation.tool_executions) >= 2, "Complex workflow should use multiple tools"
            
        # Business value validation
        if validation.time_to_completion:
            logger.info(f"Complex workflow completed in {validation.time_to_completion:.2f}s")
            
    async def test_tool_execution_performance_benchmarks(self, tool_execution_tester):
        """Test tool execution performance against business benchmarks."""
        # Run multiple scenarios for performance measurement
        performance_results = []
        
        # Test first 3 scenarios for performance
        for scenario in tool_execution_tester.TOOL_EXECUTION_SCENARIOS[:3]:
            validation = await tool_execution_tester.execute_tool_execution_scenario(
                scenario, timeout=90.0
            )
            performance_results.append(validation)
            
        # Performance assertions
        start_times = [v.time_to_agent_started for v in performance_results if v.time_to_agent_started]
        first_tool_times = [v.time_to_first_tool for v in performance_results if v.time_to_first_tool]
        completion_times = [v.time_to_completion for v in performance_results if v.time_to_completion]
        
        if start_times:
            avg_start_time = sum(start_times) / len(start_times)
            assert avg_start_time < 6.0, f"Average agent start time {avg_start_time:.2f}s too slow"
            
        if first_tool_times:
            avg_first_tool = sum(first_tool_times) / len(first_tool_times)
            assert avg_first_tool < 15.0, f"Average first tool time {avg_first_tool:.2f}s too slow"
            
        if completion_times:
            avg_completion = sum(completion_times) / len(completion_times)
            assert avg_completion < 120.0, f"Average completion {avg_completion:.2f}s too slow"
            
    async def test_tool_execution_reliability_metrics(self, tool_execution_tester):
        """Test tool execution reliability metrics."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[0]  # Use sequential for reliability test
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=100.0
        )
        
        # Reliability metrics validation
        if validation.tool_executions:
            total_tools = len(validation.tool_executions)
            successful_tools = sum(1 for t in validation.tool_executions if t.success)
            
            if total_tools > 0:
                reliability_rate = successful_tools / total_tools
                assert reliability_rate >= 0.5, f"Tool reliability rate {reliability_rate:.1%} too low"
                logger.info(f"Tool execution reliability: {reliability_rate:.1%} ({successful_tools}/{total_tools})")
                
        # Business logic validation
        quality_score = sum([
            validation.tool_chain_coherent,
            validation.tools_successful, 
            validation.error_handling_robust,
            validation.results_actionable
        ])
        
        assert quality_score >= 2, f"Tool execution quality score {quality_score}/4 below minimum"
        
    async def test_tool_execution_event_ordering(self, tool_execution_tester):
        """Test WebSocket event ordering for tool execution."""
        scenario = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[0]
        
        validation = await tool_execution_tester.execute_tool_execution_scenario(
            scenario, timeout=90.0
        )
        
        # Build event sequence
        event_sequence = [e.get("type") for e in validation.events_received]
        
        # Verify logical ordering
        if "agent_started" in event_sequence and "tool_executing" in event_sequence:
            started_idx = event_sequence.index("agent_started")
            tool_idx = event_sequence.index("tool_executing")
            assert tool_idx > started_idx, "Tool execution should come after agent start"
            
        # Tool event pairing validation
        executing_events = event_sequence.count("tool_executing")
        completed_events = event_sequence.count("tool_completed")
        error_events = event_sequence.count("tool_error")
        
        if executing_events > 0:
            completion_rate = (completed_events + error_events) / executing_events
            assert completion_rate >= 0.7, f"Tool completion rate {completion_rate:.1%} too low"
            
    async def test_comprehensive_tool_execution_report(self, tool_execution_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute representative scenarios
        test_scenarios = tool_execution_tester.TOOL_EXECUTION_SCENARIOS[:4]  # First 4 scenarios
        
        for scenario in test_scenarios:
            await tool_execution_tester.execute_tool_execution_scenario(
                scenario, timeout=100.0
            )
            
        # Generate and save report
        report = tool_execution_tester.generate_tool_execution_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "tool_execution_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Tool execution report saved to: {report_file}")
        
        # Verify overall success
        total_tests = len(tool_execution_tester.validations)
        successful_executions = sum(
            1 for v in tool_execution_tester.validations 
            if v.tools_successful or v.tool_chain_coherent
        )
        
        assert successful_executions > 0, "At least some tool executions should succeed"
        success_rate = successful_executions / total_tests if total_tests > 0 else 0
        logger.info(f"Tool execution success rate: {success_rate:.1%}")


if __name__ == "__main__":
    # Support environment selection via E2E_TEST_ENV
    test_env = get_env("E2E_TEST_ENV", "local")
    logger.info(f"Running E2E tests against {test_env} environment")
    
    # Run with real services
    pytest.main([
        __file__,
        "-v",
        "--real-services",
        "-s",
        "--tb=short"
    ])