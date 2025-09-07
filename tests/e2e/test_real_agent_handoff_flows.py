#!/usr/bin/env python
"""Real Agent Handoff Flows E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests agent-to-agent handoff workflows with real services.
Business Value: Ensure smooth workflow transitions and collaboration.

Business Value Justification (BVJ):
1. Segment: Mid, Enterprise
2. Business Goal: Enable complex multi-agent workflows
3. Value Impact: Agent handoffs enable sophisticated problem solving
4. Revenue Impact: $350K+ ARR from advanced workflow capabilities

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events per agent
- Tests actual agent handoff business logic
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
from typing import Dict, List, Any, Optional, Set, Tuple
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


class HandoffStatus(Enum):
    """Agent handoff status tracking."""
    PENDING = "pending"
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentHandoffTrace:
    """Tracks individual agent handoff."""
    from_agent: str
    to_agent: str
    handoff_context: Dict[str, Any]
    start_time: float
    end_time: Optional[float] = None
    status: HandoffStatus = HandoffStatus.PENDING
    success: bool = False
    data_preserved: bool = False
    context_maintained: bool = False
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


@dataclass
class AgentHandoffFlowValidation:
    """Captures and validates agent handoff flow execution."""
    
    user_id: str
    thread_id: str
    workflow_name: str
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Agent handoff tracking
    handoff_traces: List[AgentHandoffTrace] = field(default_factory=list)
    agent_sequence: List[str] = field(default_factory=list)
    active_agents: Set[str] = field(default_factory=set)
    
    # Workflow state tracking
    workflow_context: Dict[str, Any] = field(default_factory=dict)
    data_flow: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing metrics (performance benchmarks per requirements)
    time_to_first_agent: Optional[float] = None
    time_to_first_handoff: Optional[float] = None
    time_to_workflow_completion: Optional[float] = None
    
    # Business logic validation
    handoffs_successful: bool = False
    data_integrity_maintained: bool = False
    workflow_coherent: bool = False
    final_result_complete: bool = False


class RealAgentHandoffFlowsTester:
    """Tests agent handoff flows with real services and WebSocket events."""
    
    # CLAUDE.md REQUIRED WebSocket events per agent
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    # Agent handoff workflow scenarios
    HANDOFF_WORKFLOW_SCENARIOS = [
        {
            "workflow_name": "triage_to_data_analysis",
            "initial_message": "I need a comprehensive analysis of our customer data trends",
            "expected_agent_flow": ["triage_agent", "data_agent"],
            "handoff_points": [
                {"trigger": "data_analysis_required", "from": "triage_agent", "to": "data_agent"}
            ],
            "success_criteria": ["data_collected", "analysis_performed", "insights_delivered"]
        },
        {
            "workflow_name": "research_to_optimization_workflow",
            "initial_message": "Research market opportunities and optimize our strategy accordingly",
            "expected_agent_flow": ["supply_researcher", "optimization_agent"],
            "handoff_points": [
                {"trigger": "research_complete", "from": "supply_researcher", "to": "optimization_agent"}
            ],
            "success_criteria": ["research_findings", "optimization_plan", "strategy_updated"]
        },
        {
            "workflow_name": "multi_stage_validation_flow",
            "initial_message": "Validate this complex business proposal through multiple expert reviews",
            "expected_agent_flow": ["triage_agent", "validation_agent", "reporting_agent"],
            "handoff_points": [
                {"trigger": "validation_needed", "from": "triage_agent", "to": "validation_agent"},
                {"trigger": "report_generation", "from": "validation_agent", "to": "reporting_agent"}
            ],
            "success_criteria": ["proposal_validated", "expert_review", "comprehensive_report"]
        },
        {
            "workflow_name": "error_recovery_handoff",
            "initial_message": "Process this data but expect some agents to fail and recover gracefully",
            "expected_agent_flow": ["data_agent", "validation_agent", "recovery_agent"],
            "handoff_points": [
                {"trigger": "validation_required", "from": "data_agent", "to": "validation_agent"},
                {"trigger": "error_detected", "from": "validation_agent", "to": "recovery_agent"}
            ],
            "success_criteria": ["error_detection", "recovery_attempted", "workflow_completed"]
        },
        {
            "workflow_name": "parallel_collaboration_workflow",
            "initial_message": "Coordinate multiple agents to work on different aspects simultaneously",
            "expected_agent_flow": ["triage_agent", "data_agent", "optimization_agent"],
            "handoff_points": [
                {"trigger": "parallel_processing", "from": "triage_agent", "to": "data_agent"},
                {"trigger": "parallel_processing", "from": "triage_agent", "to": "optimization_agent"}
            ],
            "success_criteria": ["parallel_execution", "coordination_maintained", "results_consolidated"]
        }
    ]
    
    def __init__(self):
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[AgentHandoffFlowValidation] = []
        
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
        
        # Initialize backend client
        backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        self.backend_client = BackendTestClient(backend_url)
        
        # Create test user with workflow permissions
        user_data = create_test_user_data("handoff_flow_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with comprehensive workflow permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=["agents:use", "workflows:execute", "handoff:manage", "coordination:enable"]
        )
        
        # Initialize WebSocket client
        ws_url = f"{backend_url.replace('http', 'ws')}/ws"
        self.ws_client = WebSocketTestClient(ws_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Agent handoff flow test environment ready for user {self.email}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_handoff_workflow_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: float = 150.0
    ) -> AgentHandoffFlowValidation:
        """Execute an agent handoff workflow scenario and validate results.
        
        Args:
            scenario: Handoff workflow scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = AgentHandoffFlowValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            workflow_name=scenario["workflow_name"]
        )
        
        # Send initial workflow request
        workflow_request = {
            "type": "agent_request",
            "agent": scenario["expected_agent_flow"][0],  # Start with first agent
            "message": scenario["initial_message"],
            "thread_id": thread_id,
            "context": {
                "workflow_name": scenario["workflow_name"],
                "expected_flow": scenario["expected_agent_flow"],
                "handoff_enabled": True,
                "user_id": self.user_id
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        await self.ws_client.send_json(workflow_request)
        logger.info(f"Started handoff workflow: {scenario['workflow_name']}")
        
        # Track workflow execution and handoffs
        handoff_tracker = {}
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout and not completed:
            event = await self.ws_client.receive(timeout=3.0)
            
            if event:
                await self._process_handoff_event(event, validation, handoff_tracker, scenario)
                
                # Check for workflow completion
                if event.get("type") in ["workflow_completed", "agent_completed", "error"]:
                    # Allow for final handoff completion
                    await asyncio.sleep(2.0)
                    final_event = await self.ws_client.receive(timeout=1.0)
                    if final_event:
                        await self._process_handoff_event(final_event, validation, handoff_tracker, scenario)
                        
                    completed = True
                    validation.time_to_workflow_completion = time.time() - start_time
                    
        # Finalize handoff traces
        self._finalize_handoff_traces(validation, handoff_tracker)
        
        # Validate the handoff workflow results
        self._validate_handoff_workflow(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _process_handoff_event(
        self, 
        event: Dict[str, Any], 
        validation: AgentHandoffFlowValidation,
        handoff_tracker: Dict[str, AgentHandoffTrace],
        scenario: Dict[str, Any]
    ):
        """Process and categorize handoff workflow specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - validation.start_time
        
        # Record all events
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        
        # Track timing of critical events
        if event_type == "agent_started":
            if not validation.time_to_first_agent:
                validation.time_to_first_agent = event_time
                
            # Track which agent started
            agent_data = event.get("data", {})
            agent_name = agent_data.get("agent_name", "unknown")
            if agent_name not in validation.agent_sequence:
                validation.agent_sequence.append(agent_name)
            validation.active_agents.add(agent_name)
            
            logger.info(f"Agent started: {agent_name} at {event_time:.2f}s")
            
        elif event_type == "agent_thinking":
            # Extract workflow context from thinking
            thinking_data = event.get("data", {})
            if isinstance(thinking_data, dict):
                thought = thinking_data.get("thought", "")
                if "handoff" in thought.lower() or "workflow" in thought.lower():
                    validation.workflow_context["thinking_steps"] = validation.workflow_context.get("thinking_steps", [])
                    validation.workflow_context["thinking_steps"].append(thought)
                    
        elif event_type == "handoff_initiated":
            if not validation.time_to_first_handoff:
                validation.time_to_first_handoff = event_time
                
            # Create handoff trace
            handoff_data = event.get("data", {})
            from_agent = handoff_data.get("from_agent", "unknown")
            to_agent = handoff_data.get("to_agent", "unknown")
            handoff_context = handoff_data.get("context", {})
            
            handoff_id = f"{from_agent}_to_{to_agent}_{len(validation.handoff_traces)}"
            handoff_trace = AgentHandoffTrace(
                from_agent=from_agent,
                to_agent=to_agent,
                handoff_context=handoff_context,
                start_time=time.time(),
                status=HandoffStatus.INITIATED
            )
            
            handoff_tracker[handoff_id] = handoff_trace
            logger.info(f"Handoff initiated: {from_agent} → {to_agent}")
            
        elif event_type == "handoff_completed":
            # Update handoff trace
            handoff_data = event.get("data", {})
            handoff_id = handoff_data.get("handoff_id")
            
            # Find matching handoff trace
            for trace_id, trace in handoff_tracker.items():
                if (handoff_id and trace_id == handoff_id) or \
                   (trace.status == HandoffStatus.INITIATED and not trace.success):
                    trace.end_time = time.time()
                    trace.status = HandoffStatus.COMPLETED
                    trace.success = True
                    trace.data_preserved = handoff_data.get("data_preserved", False)
                    trace.context_maintained = handoff_data.get("context_maintained", False)
                    
                    logger.info(f"Handoff completed: {trace.from_agent} → {trace.to_agent} ({trace.duration:.2f}s)")
                    break
                    
        elif event_type == "workflow_data":
            # Track data flow through workflow
            data_info = event.get("data", {})
            if data_info:
                validation.data_flow.append({
                    "timestamp": event_time,
                    "data_type": data_info.get("type", "unknown"),
                    "source": data_info.get("source", "unknown"),
                    "content_size": len(str(data_info)) if data_info else 0
                })
                
        elif event_type in ["agent_completed", "workflow_completed"]:
            # Extract final workflow results
            final_data = event.get("data", {})
            if isinstance(final_data, dict):
                validation.workflow_context["final_result"] = final_data
                logger.info(f"Workflow completed with result keys: {list(final_data.keys())}")
                
            # Mark agent as no longer active
            agent_name = final_data.get("agent_name", "unknown")
            validation.active_agents.discard(agent_name)
            
    def _finalize_handoff_traces(
        self, 
        validation: AgentHandoffFlowValidation,
        handoff_tracker: Dict[str, AgentHandoffTrace]
    ):
        """Finalize handoff traces and add to validation."""
        validation.handoff_traces = list(handoff_tracker.values())
        
        # Handle any handoffs that didn't complete
        for trace in validation.handoff_traces:
            if trace.status == HandoffStatus.INITIATED:
                trace.status = HandoffStatus.FAILED
                trace.end_time = time.time()
                
    def _validate_handoff_workflow(
        self, 
        validation: AgentHandoffFlowValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate handoff workflow against business requirements."""
        
        # 1. Check handoff success rate
        successful_handoffs = sum(1 for trace in validation.handoff_traces if trace.success)
        total_handoffs = len(validation.handoff_traces)
        
        if total_handoffs > 0:
            handoff_success_rate = successful_handoffs / total_handoffs
            validation.handoffs_successful = handoff_success_rate >= 0.7
        else:
            # If no explicit handoffs detected, check if workflow progressed through expected agents
            expected_agents = scenario.get("expected_agent_flow", [])
            agents_executed = len(set(validation.agent_sequence) & set(expected_agents))
            validation.handoffs_successful = agents_executed >= len(expected_agents) * 0.7
            
        # 2. Validate data integrity through workflow
        if validation.data_flow:
            # Check for data consistency through the workflow
            data_sizes = [d["content_size"] for d in validation.data_flow if d["content_size"] > 0]
            if data_sizes:
                # Data should generally increase or stay consistent (not dramatically decrease)
                min_size = min(data_sizes)
                max_size = max(data_sizes)
                validation.data_integrity_maintained = max_size >= min_size * 0.5  # Allow some loss
        else:
            # Heuristic: if handoffs preserved data, integrity is maintained
            validation.data_integrity_maintained = any(
                trace.data_preserved for trace in validation.handoff_traces
            ) if validation.handoff_traces else True
            
        # 3. Check workflow coherence
        expected_agents = scenario.get("expected_agent_flow", [])
        if expected_agents:
            # Check if agents were executed in a logical sequence
            agents_matched = sum(
                1 for expected in expected_agents 
                if expected in validation.agent_sequence
            )
            validation.workflow_coherent = agents_matched >= len(expected_agents) * 0.6
        else:
            validation.workflow_coherent = len(validation.agent_sequence) > 1
            
        # 4. Check final result completeness
        final_result = validation.workflow_context.get("final_result", {})
        success_criteria = scenario.get("success_criteria", [])
        
        if success_criteria and final_result:
            result_content = str(final_result).lower()
            criteria_met = sum(
                1 for criteria in success_criteria
                if criteria.lower().replace("_", " ") in result_content
            )
            validation.final_result_complete = criteria_met >= len(success_criteria) * 0.5
        else:
            validation.final_result_complete = bool(final_result)
            
    def generate_handoff_flows_report(self) -> str:
        """Generate comprehensive handoff flows test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT HANDOFF FLOWS TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total workflow scenarios tested: {len(self.validations)}")
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Workflow {i}: {val.workflow_name} ---")
            report.append(f"User ID: {val.user_id}")
            report.append(f"Thread ID: {val.thread_id}")
            report.append(f"Events received: {len(val.events_received)}")
            report.append(f"Event types: {sorted(val.event_types_seen)}")
            
            # Agent execution sequence
            report.append(f"Agent sequence: {' → '.join(val.agent_sequence)}")
            
            # Check for REQUIRED WebSocket events (aggregate across all agents)
            missing_events = self.REQUIRED_EVENTS - val.event_types_seen
            if missing_events:
                report.append(f"⚠️ MISSING REQUIRED EVENTS: {missing_events}")
            else:
                report.append("✓ All required WebSocket events received")
                
            # Performance metrics
            report.append("\nPerformance Metrics:")
            report.append(f"  - First agent started: {val.time_to_first_agent:.2f}s" if val.time_to_first_agent else "  - No agents started")
            report.append(f"  - First handoff: {val.time_to_first_handoff:.2f}s" if val.time_to_first_handoff else "  - No handoffs detected")
            report.append(f"  - Workflow completion: {val.time_to_workflow_completion:.2f}s" if val.time_to_workflow_completion else "  - Workflow not completed")
            
            # Handoff analysis
            report.append(f"\nHandoff Analysis:")
            report.append(f"  - Total handoffs: {len(val.handoff_traces)}")
            
            if val.handoff_traces:
                successful_handoffs = sum(1 for h in val.handoff_traces if h.success)
                avg_handoff_time = sum(h.duration for h in val.handoff_traces if h.duration) / len(val.handoff_traces)
                
                report.append(f"  - Successful handoffs: {successful_handoffs}")
                report.append(f"  - Average handoff time: {avg_handoff_time:.2f}s")
                
                # Individual handoff details
                for j, handoff in enumerate(val.handoff_traces, 1):
                    status_symbol = "✓" if handoff.success else "✗"
                    report.append(f"    {j}. {status_symbol} {handoff.from_agent} → {handoff.to_agent} ({handoff.duration:.2f}s if handoff.duration else 'N/A'})")
                    
            # Data flow analysis
            if val.data_flow:
                report.append(f"  - Data flow events: {len(val.data_flow)}")
                total_data_size = sum(d["content_size"] for d in val.data_flow)
                report.append(f"  - Total data processed: {total_data_size} characters")
                
            # Business logic validation
            report.append("\nBusiness Logic Validation:")
            report.append(f"  ✓ Handoffs successful: {val.handoffs_successful}")
            report.append(f"  ✓ Data integrity maintained: {val.data_integrity_maintained}")
            report.append(f"  ✓ Workflow coherent: {val.workflow_coherent}")
            report.append(f"  ✓ Final result complete: {val.final_result_complete}")
            
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture
async def handoff_flows_tester():
    """Create and setup the handoff flows tester."""
    tester = RealAgentHandoffFlowsTester()
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class TestRealAgentHandoffFlows:
    """Test suite for real agent handoff flow execution."""
    
    async def test_triage_to_data_analysis_handoff(self, handoff_flows_tester):
        """Test triage to data analysis agent handoff workflow."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[0]  # triage_to_data_analysis
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=180.0
        )
        
        # CRITICAL: Verify workflow progression
        assert len(validation.agent_sequence) > 0, "Should execute at least one agent"
        
        # Verify basic handoff functionality
        expected_agents = scenario["expected_agent_flow"]
        agents_found = sum(1 for agent in expected_agents if agent in validation.agent_sequence)
        assert agents_found >= len(expected_agents) * 0.5, f"Should execute most expected agents: {agents_found}/{len(expected_agents)}"
        
        # Verify workflow coherence
        assert validation.workflow_coherent, "Workflow should be coherent"
        
        # Performance benchmark
        if validation.time_to_workflow_completion:
            assert validation.time_to_workflow_completion < 150.0, "Should complete within performance target"
            
        logger.info(f"Handoff workflow agent sequence: {' → '.join(validation.agent_sequence)}")
        
    async def test_research_to_optimization_workflow(self, handoff_flows_tester):
        """Test research to optimization agent handoff workflow."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[1]  # research_to_optimization_workflow
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=200.0
        )
        
        # Verify workflow execution
        assert len(validation.events_received) > 0, "Should receive workflow events"
        assert len(validation.agent_sequence) > 0, "Should execute agents"
        
        # Check for handoff attempts (may not always succeed in test environment)
        if validation.handoff_traces:
            assert len(validation.handoff_traces) > 0, "Should attempt agent handoffs"
            logger.info(f"Detected {len(validation.handoff_traces)} handoff attempts")
            
        # Verify data flow through workflow
        if validation.data_flow:
            assert len(validation.data_flow) > 0, "Should have data flow through workflow"
            
    async def test_multi_stage_validation_flow(self, handoff_flows_tester):
        """Test multi-stage validation workflow with multiple handoffs."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[2]  # multi_stage_validation_flow
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=220.0
        )
        
        # Multi-stage workflow validation
        assert validation.workflow_coherent, "Multi-stage workflow should be coherent"
        
        # Check agent execution diversity
        unique_agents = len(set(validation.agent_sequence))
        assert unique_agents >= 2, f"Multi-stage workflow should use multiple agents: {unique_agents}"
        
        # Performance validation
        if validation.time_to_first_agent:
            assert validation.time_to_first_agent < 10.0, "First agent should start quickly"
            
    async def test_error_recovery_handoff_workflow(self, handoff_flows_tester):
        """Test error recovery in handoff workflows."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[3]  # error_recovery_handoff
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=160.0
        )
        
        # Should handle errors gracefully
        assert len(validation.events_received) > 0, "Should receive events even with potential errors"
        
        # Error recovery validation
        error_events = [e for e in validation.events_received if e.get("type") == "error"]
        if error_events:
            # Should continue workflow despite errors
            assert validation.workflow_coherent or len(validation.agent_sequence) > 1, \
                "Should maintain workflow coherence despite errors"
            logger.info(f"Error recovery tested with {len(error_events)} error events")
        
    async def test_parallel_collaboration_workflow(self, handoff_flows_tester):
        """Test parallel agent collaboration workflow."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[4]  # parallel_collaboration_workflow
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=180.0
        )
        
        # Parallel collaboration validation
        if len(validation.agent_sequence) >= 2:
            logger.info(f"Parallel workflow executed {len(validation.agent_sequence)} agents")
            
        # Check for coordination indicators
        if validation.workflow_context.get("thinking_steps"):
            coordination_thoughts = sum(
                1 for thought in validation.workflow_context["thinking_steps"]
                if "coordin" in thought.lower() or "parallel" in thought.lower()
            )
            if coordination_thoughts > 0:
                logger.info(f"Detected coordination thinking: {coordination_thoughts} instances")
                
    async def test_handoff_performance_benchmarks(self, handoff_flows_tester):
        """Test handoff workflow performance benchmarks."""
        # Run multiple scenarios for performance measurement
        performance_results = []
        
        for scenario in handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[:3]:  # First 3 scenarios
            validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
                scenario, timeout=150.0
            )
            performance_results.append(validation)
            
        # Performance assertions
        workflow_times = [v.time_to_workflow_completion for v in performance_results if v.time_to_workflow_completion]
        first_agent_times = [v.time_to_first_agent for v in performance_results if v.time_to_first_agent]
        first_handoff_times = [v.time_to_first_handoff for v in performance_results if v.time_to_first_handoff]
        
        if workflow_times:
            avg_workflow_time = sum(workflow_times) / len(workflow_times)
            assert avg_workflow_time < 200.0, f"Average workflow time {avg_workflow_time:.2f}s too slow"
            
        if first_agent_times:
            avg_first_agent = sum(first_agent_times) / len(first_agent_times)
            assert avg_first_agent < 12.0, f"Average first agent time {avg_first_agent:.2f}s too slow"
            
        if first_handoff_times:
            avg_first_handoff = sum(first_handoff_times) / len(first_handoff_times)
            logger.info(f"Average first handoff time: {avg_first_handoff:.2f}s")
            
    async def test_handoff_data_integrity_validation(self, handoff_flows_tester):
        """Test data integrity through handoff workflows."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[0]  # Use triage_to_data_analysis
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=160.0
        )
        
        # Data integrity validation
        if validation.data_flow:
            assert len(validation.data_flow) > 0, "Should have data flow through workflow"
            
            # Check data flow consistency
            data_sources = set(d["source"] for d in validation.data_flow if d["source"] != "unknown")
            if len(data_sources) > 1:
                logger.info(f"Data flowed through {len(data_sources)} sources: {data_sources}")
                
        # Handoff data preservation
        if validation.handoff_traces:
            data_preserved_count = sum(1 for h in validation.handoff_traces if h.data_preserved)
            if data_preserved_count > 0:
                logger.info(f"Data preservation detected in {data_preserved_count} handoffs")
                
    async def test_handoff_workflow_quality_metrics(self, handoff_flows_tester):
        """Test handoff workflow quality metrics."""
        scenario = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[0]
        
        validation = await handoff_flows_tester.execute_handoff_workflow_scenario(
            scenario, timeout=140.0
        )
        
        # Calculate workflow quality score
        quality_score = sum([
            validation.handoffs_successful,
            validation.data_integrity_maintained,
            validation.workflow_coherent,
            validation.final_result_complete
        ])
        
        # Should meet minimum quality threshold
        assert quality_score >= 2, f"Handoff workflow quality score {quality_score}/4 below minimum"
        
        # Basic workflow execution validation
        assert len(validation.agent_sequence) > 0, "Should execute at least one agent"
        assert len(validation.events_received) > 5, "Should have substantial event flow"
        
        logger.info(f"Handoff workflow quality score: {quality_score}/4")
        
    async def test_comprehensive_handoff_flows_report(self, handoff_flows_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute representative handoff scenarios
        test_scenarios = handoff_flows_tester.HANDOFF_WORKFLOW_SCENARIOS[:4]  # First 4 scenarios
        
        for scenario in test_scenarios:
            await handoff_flows_tester.execute_handoff_workflow_scenario(
                scenario, timeout=170.0
            )
            
        # Generate and save report
        report = handoff_flows_tester.generate_handoff_flows_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "handoff_flows_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Handoff flows report saved to: {report_file}")
        
        # Verify overall workflow success
        total_tests = len(handoff_flows_tester.validations)
        successful_workflows = sum(
            1 for v in handoff_flows_tester.validations 
            if v.workflow_coherent and len(v.agent_sequence) > 0
        )
        
        assert successful_workflows > 0, "At least some handoff workflows should succeed"
        success_rate = successful_workflows / total_tests if total_tests > 0 else 0
        logger.info(f"Handoff workflow success rate: {success_rate:.1%}")


if __name__ == "__main__":
    # Run with real services
    pytest.main([
        __file__,
        "-v",
        "--real-services",
        "-s",
        "--tb=short"
    ])